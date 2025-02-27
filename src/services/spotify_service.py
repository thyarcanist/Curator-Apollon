import spotipy
from spotipy.oauth2 import SpotifyOAuth
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
        self.sp = None
        self.auth_manager = None
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

    def ensure_authenticated(self):
        if self.sp is None:
            try:
                port, auth_queue = self._start_auth_server()
                
                # Define scopes as a single space-separated string
                SCOPES = "playlist-read-private playlist-read-collaborative playlist-read-public user-library-read user-read-private user-read-email"
                
                self.auth_manager = SpotifyOAuth(
                    client_id="55c875d209d94fdf963a31243f5d6fdb",
                    client_secret="cf4f384ddf3c46c49e8ca8d15d3b71ba",
                    redirect_uri="https://apollon.occybyte.com/callback",
                    scope=SCOPES,  # Use the single string instead of join
                    cache_path=str(self.cache_path),
                    open_browser=True
                )
                
                auth_url = self.auth_manager.get_authorize_url()
                webbrowser.open(auth_url)
                
                try:
                    # Show instructions to user
                    messagebox.showinfo(
                        message="After authorizing in your browser:\n\n"
                               "1. Copy the FULL URL from your browser\n"
                               "2. Paste it in the next dialog",
                        title="Spotify Authentication"
                    )
                    
                    # Get the full URL from user
                    response = simpledialog.askstring(
                        "Spotify Authentication",
                        "Please paste the FULL URL from your browser:",
                        initialvalue="https://apollon.occybyte.com/callback?code="
                    )
                    
                    if response:
                        # Extract code from URL
                        code = self.auth_manager.parse_response_code(response)
                        # Get token with code
                        self.auth_manager.get_access_token(code)
                        # Create Spotify client
                        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
                        # Test connection
                        self.sp.current_user()
                    else:
                        raise Exception("Authentication cancelled")
                    
                finally:
                    self._stop_auth_server()
                
            except Exception as e:
                if self.cache_path.exists():
                    self.cache_path.unlink()
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
                raise ValueError("Invalid Spotify playlist URL format")
            
            # Get playlist details with more fields
            try:
                playlist = self.sp.playlist(playlist_id, 
                    fields="name,tracks.total,owner.display_name,public")
                if not playlist:
                    raise ValueError("Could not find playlist")
                    
                print(f"Playlist details: {playlist}")  # Debug info
                
            except Exception as e:
                raise ValueError(f"Could not access playlist: {str(e)}")
            
            messagebox.showinfo("Import Status", 
                              f"Found playlist: {playlist['name']}\n"
                              f"Owner: {playlist['owner']['display_name']}\n"
                              f"Public: {playlist.get('public', False)}\n"
                              f"Total tracks: {playlist['tracks']['total']}")
            
            tracks = []
            offset = 0
            limit = 50  # Increased batch size
            
            while True:
                try:
                    results = self.sp.playlist_tracks(
                        playlist_id,
                        offset=offset,
                        limit=limit,
                        fields="items(track(id,name,artists,is_local)),next,total"
                    )
                    
                    if not results or not results['items']:
                        break
                    
                    batch_ids = []
                    batch_tracks = []
                    
                    # Collect all valid tracks from this batch
                    for item in results['items']:
                        if (item['track'] and 
                            not item['track'].get('is_local', False) and 
                            item['track'].get('id')):
                            batch_ids.append(item['track']['id'])
                            batch_tracks.append(item['track'])
                    
                    if batch_ids:
                        # Get audio features for the entire batch
                        features = self.sp.audio_features(batch_ids)
                        
                        # Process each track with its features
                        for track, feature in zip(batch_tracks, features):
                            if feature:
                                tracks.append(Track(
                                    id=track['id'],
                                    title=track['name'],
                                    artist=track['artists'][0]['name'],
                                    bpm=feature['tempo'],
                                    key=self._convert_key(feature['key'], feature['mode']),
                                    camelot_position=self._get_camelot_position(
                                        feature['key'], feature['mode']
                                    ),
                                    energy_level=feature['energy'],
                                    spotify_url=f"https://open.spotify.com/track/{track['id']}"
                                ))
                                print(f"Successfully imported: {track['name']}")
                    
                    offset += limit
                    
                    # Show progress
                    messagebox.showinfo("Import Progress", 
                                      f"Processed {len(tracks)} tracks so far...")
                    
                except Exception as e:
                    print(f"Error in batch processing: {str(e)}")
                    continue
            
            if not tracks:
                raise Exception(
                    "No tracks could be imported. This could be because:\n"
                    "1. The playlist is private\n"
                    "2. You don't have access to the playlist\n"
                    "3. The tracks are not available in your region\n"
                    "Please check the playlist URL and permissions."
                )
            
            return tracks
            
        except Exception as e:
            raise Exception(f"Playlist import failed: {str(e)}")
    
    def _extract_spotify_id(self, url: str) -> str:
        """Extract Spotify ID from various URL formats"""
        # Handle different Spotify URL formats
        patterns = [
            r'spotify:(?:track|playlist):([a-zA-Z0-9]+)',  # Spotify URI
            r'open\.spotify\.com/(?:track|playlist)/([a-zA-Z0-9]+)',  # Web URL
            r'/([a-zA-Z0-9]+)(?:\?|$)'  # Simple ID or ID with query params
        ]
        
        for pattern in patterns:
            if match := re.search(pattern, url):
                return match.group(1)
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