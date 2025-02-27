import spotipy
from spotipy.oauth2 import SpotifyOAuth
from models.library import Track
import re
import os
from pathlib import Path
from tkinter import messagebox, simpledialog
import webbrowser

class CustomSpotifyOAuth(SpotifyOAuth):
    def get_auth_response(self):
        auth_url = self.get_authorize_url()
        webbrowser.open(auth_url)
        # Use tkinter dialog instead of input()
        response = simpledialog.askstring(
            "Spotify Authentication",
            "Please paste the URL you were redirected to:",
            initialvalue="https://apollon.occybyte.com/callback?code="
        )
        return response

class SpotifyService:
    def __init__(self):
        self.sp = None
        self.auth_manager = None
        self._setup_cache()
        
    def _setup_cache(self):
        """Setup cache directory for Spotify tokens"""
        self.cache_dir = Path.home() / '.cache' / 'apollon'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / 'spotify_token.cache'
    
    def ensure_authenticated(self):
        """Ensure Spotify client is authenticated"""
        if self.sp is None:
            try:
                self.auth_manager = CustomSpotifyOAuth(
                    client_id="55c875d209d94fdf963a31243f5d6fdb",
                    client_secret="cf4f384ddf3c46c49e8ca8d15d3b71ba",
                    redirect_uri="https://apollon.occybyte.com/callback",
                    scope="user-library-read playlist-read-private",
                    cache_path=str(self.cache_path),
                    open_browser=False  # We'll handle browser opening ourselves
                )
                self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
                # Test the connection
                self.sp.current_user()
            except Exception as e:
                if self.cache_path.exists():
                    self.cache_path.unlink()
                raise Exception(f"Failed to authenticate with Spotify: {str(e)}\nPlease try again.")
    
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
            # Extract playlist ID from various Spotify URL formats
            playlist_id = self._extract_spotify_id(playlist_url)
            if not playlist_id:
                raise ValueError("Invalid Spotify playlist URL format")
            
            tracks = []
            results = self.sp.playlist_tracks(playlist_id)
            
            while results:
                for item in results['items']:
                    try:
                        if not item['track']:  # Skip any None tracks or local files
                            continue
                            
                        track = item['track']
                        audio_features = self.sp.audio_features(track['id'])
                        
                        if not audio_features or not audio_features[0]:  # Skip tracks without audio features
                            continue
                        
                        audio_feature = audio_features[0]
                        
                        tracks.append(Track(
                            id=track['id'],
                            title=track['name'],
                            artist=track['artists'][0]['name'],
                            bpm=audio_feature['tempo'],
                            key=self._convert_key(audio_feature['key'], audio_feature['mode']),
                            camelot_position=self._get_camelot_position(audio_feature['key'], 
                                                                      audio_feature['mode']),
                            energy_level=audio_feature['energy'],
                            spotify_url=f"https://open.spotify.com/track/{track['id']}"
                        ))
                    except Exception as e:
                        print(f"Error processing track: {str(e)}")
                        continue
                
                # Get next page of results if available
                if results['next']:
                    results = self.sp.next(results)
                else:
                    results = None
                    
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