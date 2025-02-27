from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Track:
    id: str
    title: str
    artist: str
    bpm: float
    key: str
    camelot_position: str
    energy_level: float
    spotify_url: str = None
    album: str = None
    time_signature: str = "4/4"  # Default to common time
    album_art_url: str = None  # Add this field
    genres: List[str] = None  # Add genres field

class MusicLibrary:
    def __init__(self):
        self.tracks = []
        self.observers = []
    
    def add_track(self, track: Track):
        """Add a single track"""
        self.tracks.append(track)
        self._notify_observers()
    
    def add_tracks(self, tracks: List[Track]):
        """Add multiple tracks at once"""
        for track in tracks:
            self.tracks.append(track)
        self._notify_observers()
    
    def remove_track(self, track: Track):
        if track in self.tracks:
            self.tracks.remove(track)
            self._notify_observers()
    
    def get_all_tracks(self) -> List[Track]:
        return self.tracks.copy()
    
    def clear(self):
        self.tracks.clear()
        self._notify_observers()
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def _notify_observers(self):
        for observer in self.observers:
            observer._update_track_list() 