import spotipy
from spotipy.oauth2 import SpotifyOAuth
from models.library import Track

class SpotifyService:
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id="55c875d209d94fdf963a31243f5d6fdb",
            client_secret="cf4f384ddf3c46c49e8ca8d15d3b71ba",
            redirect_uri="https://apollon.occybyte.com/",
            scope="user-library-read playlist-read-private"
        ))
    
    def get_track_info(self, spotify_url: str) -> Track:
        # Extract track ID from URL
        track_id = spotify_url.split('/')[-1]
        
        # Get track info from Spotify
        track_info = self.sp.track(track_id)
        audio_features = self.sp.audio_features(track_id)[0]
        
        return Track(
            id=track_id,
            title=track_info['name'],
            artist=track_info['artists'][0]['name'],
            bpm=audio_features['tempo'],
            key=self._convert_key(audio_features['key'], audio_features['mode']),
            camelot_position=self._get_camelot_position(audio_features['key'], 
                                                      audio_features['mode']),
            energy_level=audio_features['energy'],
            spotify_url=spotify_url
        )
    
    def import_playlist(self, playlist_url: str) -> list[Track]:
        # Extract playlist ID from URL
        playlist_id = playlist_url.split('/')[-1]
        
        # Get playlist tracks
        results = self.sp.playlist_tracks(playlist_id)
        tracks = []
        
        for item in results['items']:
            track = item['track']
            audio_features = self.sp.audio_features(track['id'])[0]
            
            tracks.append(Track(
                id=track['id'],
                title=track['name'],
                artist=track['artists'][0]['name'],
                bpm=audio_features['tempo'],
                key=self._convert_key(audio_features['key'], audio_features['mode']),
                camelot_position=self._get_camelot_position(audio_features['key'], 
                                                          audio_features['mode']),
                energy_level=audio_features['energy'],
                spotify_url=f"https://open.spotify.com/track/{track['id']}"
            ))
        
        return tracks
    
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