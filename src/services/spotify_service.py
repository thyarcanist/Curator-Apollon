import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from models.library import Track
import re
import os
from pathlib import Path
from tkinter import messagebox, simpledialog
import webbrowser
import http.server
import socketserver
import threading
from urllib.parse import urlparse, parse_qs
from queue import Queue
import requests
import base64

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, auth_queue=None, **kwargs):
        self.auth_queue = auth_queue
        super().__init__(*args, **kwargs)

    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        
        # Send styled response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        if 'code' in query_components:
            self.auth_queue.put(query_components['code'][0])
            response_html = """
            <html>
            <head>
                <style>
                    body {
                        background-color: #1E1E1E;
                        color: #E0E0E0;
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        text-align: center;
                        padding: 2rem;
                        background-color: #2D2D2D;
                        border-radius: 8px;
                    }
                    h1 { color: #9D86E9; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Curator Apollon</h1>
                    <p>Authentication successful! You can close this window.</p>
                </div>
            </body>
            </html>
            """
        else:
            response_html = """
            <html>
            <head>
                <style>
                    body {
                        background-color: #1E1E1E;
                        color: #E0E0E0;
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        text-align: center;
                        padding: 2rem;
                        background-color: #2D2D2D;
                        border-radius: 8px;
                    }
                    h1 { color: #9D86E9; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Curator Apollon</h1>
                    <p>Authentication failed. Please try again.</p>
                </div>
            </body>
            </html>
            """
        
        self.wfile.write(response_html.encode())

class SpotifyService:
    def __init__(self):
        self.client_id = "55c875d209d94fdf963a31243f5d6fdb"
        self.client_secret = "cf4f384ddf3c46c49e8ca8d15d3b71ba"
        self.token = None
        self.sp = None
        self._setup_cache()
        self.server = None
        self.server_thread = None
    
    def _setup_cache(self):
        self.cache_dir = Path.home() / '.cache' / 'apollon'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / 'spotify_token.cache'
    
    def _start_auth_server(self):
        auth_queue = Queue()
        handler = lambda *args, **kwargs: CallbackHandler(*args, auth_queue=auth_queue, **kwargs)
        
        # Find an available port
        for port in range(8000, 8100):
            try:
                self.server = socketserver.TCPServer(("", port), handler)
                break
            except:
                continue
        
        if not self.server:
            raise Exception("Could not start authentication server")
        
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        return port, auth_queue
    
    def _stop_auth_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.server_thread = None

    def _get_token(self):
        """Get access token using client credentials flow"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = str(base64.b64encode(auth_bytes), 'utf-8')
        
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        try:
            result = requests.post(url, headers=headers, data=data)
            result.raise_for_status()
            json_result = result.json()
            self.token = json_result["access_token"]
            return self.token
        except Exception as e:
            raise Exception(f"Failed to get access token: {str(e)}")

    def ensure_authenticated(self):
        if self.sp is None:
            try:
                # Define minimal required scopes for playlist access
                SCOPES = "playlist-read-private playlist-read-collaborative"  # Only what we need
                
                self.auth_manager = SpotifyOAuth(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    redirect_uri="https://apollon.occybyte.com/callback",
                    scope=SCOPES,
                    cache_path=str(self.cache_path),
                    open_browser=True,
                    show_dialog=True
                )
                
                try:
                    token_info = self.auth_manager.get_cached_token()
                    if not token_info or self.auth_manager.is_token_expired(token_info):
                        print("Getting new token...")
                        auth_url = self.auth_manager.get_authorize_url()
                        webbrowser.open(auth_url)
                        
                        # Show instructions to user
                        messagebox.showinfo(
                            "Spotify Authentication",
                            "After authorizing in your browser:\n\n"
                            "1. Copy the FULL URL from your browser\n"
                            "2. Paste it in the next dialog"
                        )
                        
                        response = simpledialog.askstring(
                            "Spotify Authentication",
                            "Please paste the FULL URL from your browser:",
                            initialvalue="https://apollon.occybyte.com/callback?code="
                        )
                        
                        if response:
                            code = self.auth_manager.parse_response_code(response)
                            token_info = self.auth_manager.get_access_token(code)
                        else:
                            raise Exception("Authentication cancelled")
                    
                    self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
                    
                except Exception as e:
                    print(f"Authentication error: {str(e)}")
                    if self.cache_path.exists():
                        self.cache_path.unlink()
                    raise
                    
            except Exception as e:
                raise Exception(f"Authentication failed: {str(e)}")
    
    def get_track_info(self, spotify_url: str) -> Track:
        """Get track info from Spotify URL"""
        self.ensure_authenticated()
        # Extract track ID from various Spotify URL formats
        track_id = self._extract_spotify_id(spotify_url)
        if not track_id:
            raise ValueError("Invalid Spotify URL format")
            
        # Get track info from Spotify
        track_info = self.sp.track(track_id)
        audio_features = self.sp.audio_features(track_id)[0]
        
        if not audio_features:
            raise ValueError("Could not fetch audio features for this track")
        
        return Track(
            id=track_id,
            title=track_info['name'],
            artist=track_info['artists'][0]['name'],
            bpm=audio_features['tempo'],
            key=self._convert_key(audio_features['key'], audio_features['mode']),
            camelot_position=self._get_camelot_position(audio_features['key'], 
                                                      audio_features['mode']),
            energy_level=audio_features['energy'],
            spotify_url=f"https://open.spotify.com/track/{track_id}"
        )
    
    def import_playlist(self, playlist_url: str) -> list[Track]:
        """Import tracks from a Spotify playlist URL"""
        self.ensure_authenticated()
        try:
            playlist_id = self._extract_spotify_id(playlist_url)
            if not playlist_id:
                raise ValueError(
                    "Invalid Spotify playlist URL format. Please use one of these formats:\n"
                    "- https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M\n"
                    "- spotify:playlist:37i9dQZF1DXcBWIGoYBM5M\n"
                    "- Just the ID: 37i9dQZF1DXcBWIGoYBM5M"
                )
            
            print(f"Attempting to import playlist: {playlist_id}")
            
            try:
                # First try to get basic playlist info
                playlist = self.sp.playlist(
                    playlist_id,
                    fields="name,tracks.total",
                    market="US"  # Add market parameter
                )
                
                if not playlist:
                    raise ValueError("Could not find playlist")
                    
                print(f"Found playlist: {playlist['name']} with {playlist['tracks']['total']} tracks")
                
                # Get tracks with market parameter
                results = self.sp.playlist_tracks(
                    playlist_id,
                    fields="items(track(id,name,artists,is_local))",
                    market="US"
                )
                
                if not results or not results['items']:
                    raise Exception("No tracks found in playlist")
                
                tracks = []
                for item in results['items']:
                    if item['track'] and not item['track'].get('is_local', False):
                        tracks.append(Track(
                            id=item['track']['id'],
                            title=item['track']['name'],
                            artist=item['track']['artists'][0]['name'],
                            bpm=item['track']['tempo'],
                            key=self._convert_key(item['track']['key'], item['track']['mode']),
                            camelot_position=self._get_camelot_position(item['track']['key'], 
                                                                      item['track']['mode']),
                            energy_level=item['track']['energy']
                        ))
                        print(f"Imported: {item['track']['name']}")
                
                if not tracks:
                    raise Exception("No valid tracks could be imported")
                
                return tracks
                
            except Exception as e:
                print(f"Error during playlist import: {str(e)}")
                raise
                
        except Exception as e:
            raise Exception(f"Playlist import failed: {str(e)}")
    
    def _extract_spotify_id(self, url: str) -> str:
        """Extract Spotify ID from various URL formats"""
        print(f"Extracting ID from URL: {url}")  # Debug print
        
        # Clean the URL first
        url = url.strip()
        
        # Handle different Spotify URL formats
        patterns = [
            r'spotify:playlist:([a-zA-Z0-9]{22})',  # Spotify URI
            r'open\.spotify\.com/playlist/([a-zA-Z0-9]{22})',  # Web URL
            r'spotify\.com/playlist/([a-zA-Z0-9]{22})',  # Shortened URL
            r'playlist/([a-zA-Z0-9]{22})',  # Path only
            r'^([a-zA-Z0-9]{22})$'  # Just the ID
        ]
        
        for pattern in patterns:
            if match := re.search(pattern, url):
                playlist_id = match.group(1)
                print(f"Found playlist ID: {playlist_id}")  # Debug print
                return playlist_id
            
        print("No valid playlist ID found")  # Debug print
        return None
    
    def _convert_key(self, key: int, mode: int) -> str:
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        modes = ['minor', 'major']
        return f"{keys[key]} {modes[mode]}"
    
    def _get_camelot_position(self, key: int, mode: int) -> str:
        """
        Convert Spotify key/mode to Camelot position
        key: 0-11 (C-B)
        mode: 0=minor, 1=major
        """
        camelot_wheel = {
            # Major keys (B notation)
            (0, 1): '8B',   # C major
            (1, 1): '3B',   # C#/Db major
            (2, 1): '10B',  # D major
            (3, 1): '5B',   # D#/Eb major
            (4, 1): '12B',  # E major
            (5, 1): '7B',   # F major
            (6, 1): '2B',   # F#/Gb major
            (7, 1): '9B',   # G major
            (8, 1): '4B',   # G#/Ab major
            (9, 1): '11B',  # A major
            (10, 1): '6B',  # A#/Bb major
            (11, 1): '1B',  # B major
            
            # Minor keys (A notation)
            (0, 0): '5A',   # C minor
            (1, 0): '12A',  # C#/Db minor
            (2, 0): '7A',   # D minor
            (3, 0): '2A',   # D#/Eb minor
            (4, 0): '9A',   # E minor
            (5, 0): '4A',   # F minor
            (6, 0): '11A',  # F#/Gb minor
            (7, 0): '6A',   # G minor
            (8, 0): '1A',   # G#/Ab minor
            (9, 0): '8A',   # A minor
            (10, 0): '3A',  # A#/Bb minor
            (11, 0): '10A', # B minor
        }
        return camelot_wheel.get((key, mode), 'Unknown') 

    def test_playlist_access(self, playlist_url: str) -> bool:
        """Test if we can access a playlist"""
        try:
            playlist_id = self._extract_spotify_id(playlist_url)
            if not playlist_id:
                print("Could not extract playlist ID")
                return False
            
            # Try to get just the playlist name
            result = self.sp.playlist(
                playlist_id,
                fields="name",
                market="US"
            )
            
            print(f"Successfully accessed playlist: {result['name']}")
            return True
        
        except Exception as e:
            print(f"Error accessing playlist: {str(e)}")
            return False 