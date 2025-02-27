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
from ttkbootstrap.dialogs import Messagebox  # Update import

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
        print("Initializing SpotifyService...")
        self.client_id = "55c875d209d94fdf963a31243f5d6fdb"
        self.client_secret = "cf4f384ddf3c46c49e8ca8d15d3b71ba"
        self.token = None
        self.sp = None
        self._setup_cache()
        
        # Initialize auth manager during construction
        print("Setting up OAuth manager...")
        self.auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri="https://apollon.occybyte.com/callback",
            scope=" ".join([
                "playlist-read-private",
                "playlist-read-collaborative",
                "playlist-modify-public",
                "playlist-modify-private",
                "user-library-read"
            ]),
            cache_path=str(self.cache_path),
            open_browser=False,
            show_dialog=True
        )
        
        # Try to get cached token
        try:
            print("Checking for cached token...")
            token_info = self.auth_manager.get_cached_token()
            if token_info and not self.auth_manager.is_token_expired(token_info):
                print("Found valid cached token")
                self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
                print("Spotify client initialized from cache")
        except Exception as e:
            print(f"Cache initialization error (non-fatal): {str(e)}")
    
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
        
        response = requests.post(url, headers=headers, data=data)
        json_result = response.json()
        
        if response.status_code == 200:
            self.token = json_result["access_token"]
            return self.token
        else:
            print(f"Token Error: {json_result}")
            raise Exception(f"Failed to get token: {response.status_code}")

    def ensure_authenticated(self):
        """Ensure we have a valid OAuth token"""
        if self.sp is None:
            print("No Spotify client exists, initializing...")
            try:
                print("Checking for cached token...")
                token_info = self.auth_manager.get_cached_token()
                
                if not token_info or self.auth_manager.is_token_expired(token_info):
                    print("No valid cached token, starting new authentication...")
                    auth_url = self.auth_manager.get_authorize_url()
                    print(f"Opening auth URL: {auth_url}")
                    webbrowser.open(auth_url)
                    
                    # Show instructions
                    Messagebox.show_info(
                        message="After authorizing in your browser:\n\n"
                               "1. Copy the FULL URL from your browser\n"
                               "2. Paste it in the next dialog",
                        title="Spotify Authentication"
                    )
                    
                    response = simpledialog.askstring(
                        "Spotify Authentication",
                        "Please paste the FULL URL from your browser:",
                        initialvalue="https://apollon.occybyte.com/callback?code="
                    )
                    
                    if response:
                        print("Got response URL, extracting code...")
                        code = self.auth_manager.parse_response_code(response)
                        print("Getting access token...")
                        token_info = self.auth_manager.get_access_token(code)
                    else:
                        raise Exception("Authentication cancelled by user")
                else:
                    print("Using cached token")
                
                print("Initializing Spotify client...")
                self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
                print("Spotify client initialized successfully")
                
            except Exception as e:
                print(f"Error during authentication: {str(e)}")
                if self.cache_path.exists():
                    print("Removing invalid cache file...")
                    self.cache_path.unlink()
                raise Exception(f"Failed to initialize Spotify client: {str(e)}")
    
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
                raise ValueError("Invalid playlist URL")
            
            print(f"Attempting to access playlist with ID: {playlist_id}")
            
            try:
                playlist = self.sp.playlist(playlist_id)
                print(f"Found playlist: {playlist['name']}")
                
                tracks = []
                items = playlist['tracks']['items']
                
                for item in items:
                    if not item['track'] or item['track'].get('is_local', False):
                        continue
                    
                    track = item['track']
                    print(f"Processing: {track['name']} by {track['artists'][0]['name']}")
                    
                    try:
                        # Try to get audio features one at a time
                        features = self.sp.audio_features(track['id'])[0]
                        if features:
                            tracks.append(Track(
                                id=track['id'],
                                title=track['name'],
                                artist=track['artists'][0]['name'],
                                bpm=features['tempo'],
                                key=self._convert_key(features['key'], features['mode']),
                                camelot_position=self._get_camelot_position(
                                    features['key'], features['mode']
                                ),
                                energy_level=features['energy'],
                                spotify_url=f"https://open.spotify.com/track/{track['id']}",
                                album=track['album']['name']
                            ))
                            print(f"✓ Imported with audio features")
                        else:
                            # Fallback to basic track info if no features available
                            tracks.append(Track(
                                id=track['id'],
                                title=track['name'],
                                artist=track['artists'][0]['name'],
                                bpm=0,
                                key="Unknown",
                                camelot_position=0,
                                energy_level=0,
                                spotify_url=f"https://open.spotify.com/track/{track['id']}",
                                album=track['album']['name']
                            ))
                            print("! Imported without audio features")
                    except Exception as e:
                        print(f"! Error getting audio features: {str(e)}")
                        # Still add the track without audio features
                        tracks.append(Track(
                            id=track['id'],
                            title=track['name'],
                            artist=track['artists'][0]['name'],
                            bpm=0,
                            key="Unknown",
                            camelot_position=0,
                            energy_level=0,
                            spotify_url=f"https://open.spotify.com/track/{track['id']}",
                            album=track['album']['name']
                        ))
                
                if not tracks:
                    raise Exception("No tracks could be imported")
                
                print(f"\nImport Summary:")
                print(f"Total tracks: {len(tracks)}")
                return tracks
                
            except Exception as e:
                print(f"Error accessing playlist: {str(e)}")
                raise
                
        except Exception as e:
            print(f"Import error: {str(e)}")
            raise
    
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

    def test_api_access(self):
        """Test Spotify API access"""
        try:
            token = self._get_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Test with a known public playlist
            test_id = "37i9dQZF1DXcBWIGoYBM5M"  # Today's Top Hits
            url = f"https://api.spotify.com/v1/playlists/{test_id}"
            
            print(f"Testing API access with URL: {url}")
            response = requests.get(
                url,
                headers=headers,
                params={"fields": "name", "market": "US"}
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"API test error: {str(e)}")
            return False 

    def debug_auth(self):
        """Debug authentication status"""
        try:
            print("\n=== Starting Authentication Debug ===")
            
            if self.sp:
                print("Spotify client already initialized, testing connection...")
            else:
                print("No Spotify client, starting authentication...")
                self.ensure_authenticated()
            
            if not self.sp:
                print("Failed to initialize Spotify client")
                return False
            
            print("Testing API access...")
            try:
                # Test 1: Get current user profile
                me = self.sp.me()
                print(f"✓ Successfully authenticated as: {me['display_name']} ({me['id']})")
                
                # Test 2: Get user's playlists
                playlists = self.sp.current_user_playlists(limit=1)
                if playlists and playlists['items']:
                    test_playlist = playlists['items'][0]
                    print(f"✓ Successfully accessed user playlist: {test_playlist['name']}")
                else:
                    print("✓ API connection working but no playlists found")
                
                # Test 3: Try to get audio features for a known track
                test_track_id = "11dFghVXANMlKmJXsNCbNl"  # This is a Spotify test track ID
                features = self.sp.audio_features([test_track_id])
                if features and features[0]:
                    print("✓ Successfully accessed audio features API")
                else:
                    print("✗ Could not access audio features API")
                
                print("=== Authentication Debug Complete ===\n")
                return True
                
            except Exception as e:
                print(f"✗ API test failed: {str(e)}")
                return False
            
        except Exception as e:
            print(f"✗ Debug error: {str(e)}")
            print("=== Authentication Debug Failed ===\n")
            return False 

    def get_playlist_tracks(self, playlist_id):
        """
        Get all tracks from a playlist
        Args:
            playlist_id: The Spotify playlist ID
        Returns:
            List of track objects
        """
        try:
            results = self.sp.playlist_tracks(playlist_id)
            tracks = results['items']
            while results['next']:
                results = self.sp.next(results)
                tracks.extend(results['items'])
            return tracks
        except Exception as e:
            print(f"Error getting playlist tracks: {e}")
            return [] 

    def export_playlist_to_txt(self, playlist_url: str, output_path: str) -> bool:
        """Export playlist tracks to a text file"""
        try:
            tracks = self.import_playlist(playlist_url)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("Curator Apollon - Playlist Export\n")
                f.write("================================\n\n")
                
                for i, track in enumerate(tracks, 1):
                    album_name = track.album if hasattr(track, 'album') else "Unknown Album"
                    f.write(f"{i}. {track.title} - {track.artist} [{album_name}]\n")
            
            print(f"Successfully exported {len(tracks)} tracks to {output_path}")
            return True
            
        except Exception as e:
            print(f"Export error: {str(e)}")
            return False 