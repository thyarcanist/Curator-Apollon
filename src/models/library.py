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

class MusicLibrary:
    def __init__(self):
        self.tracks: Dict[str, Track] = {}
        self.observers = []
    
    def add_track(self, track: Track) -> None:
        self.tracks[track.id] = track
        self._notify_observers()
    
    def remove_track(self, track_id: str) -> None:
        if track_id in self.tracks:
            del self.tracks[track_id]
            self._notify_observers()
    
    def get_track(self, track_id: str) -> Track:
        return self.tracks.get(track_id)
    
    def get_all_tracks(self) -> List[Track]:
        return list(self.tracks.values())
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def _notify_observers(self):
        for observer in self.observers:
            observer.update() 