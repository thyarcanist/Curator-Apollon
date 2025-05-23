# Curator Apollon: Data Models for Music Library and Tracks
# Copyright (C) 2024 Occybyte
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import json
import os
from pathlib import Path

@dataclass
class Track:
    id: str
    title: str
    artist: str
    bpm: float
    key: str
    camelot_position: str
    energy_level: float
    spotify_url: Optional[str] = None
    album: Optional[str] = None
    time_signature: str = "4/4"  # Default to common time
    album_art_url: Optional[str] = None  # Add this field
    genres: List[str] = field(default_factory=list)

class MusicLibrary:
    def __init__(self):
        self.tracks: List[Track] = []
        self.observers: List = []
        self.save_file_path: Path = self._get_save_file_path()
        self._load_library()
    
    def _get_app_data_dir(self) -> Path:
        """Gets the application data directory, creating it if necessary."""
        if os.name == 'nt': # Windows
            app_data_base = Path(os.getenv('APPDATA', ''))
        else: # Linux, macOS, other Unix-like
            app_data_base = Path(os.getenv('XDG_DATA_HOME', Path.home() / ".local" / "share"))
        
        app_dir = app_data_base / "CuratorApollon"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    def _get_save_file_path(self) -> Path:
        """Determines the full path to the library save file."""
        return self._get_app_data_dir() / "library.json"

    def _save_library(self):
        """Saves the current music library to a JSON file."""
        try:
            tracks_as_dicts = [asdict(track) for track in self.tracks]
            with open(self.save_file_path, 'w', encoding='utf-8') as f:
                json.dump(tracks_as_dicts, f, indent=4)
            # print(f"Library saved to {self.save_file_path}")
        except IOError as e:
            print(f"Error saving library: {e}")
        except TypeError as e:
            print(f"Error serializing library for saving: {e}")

    def _load_library(self):
        """Loads the music library from a JSON file if it exists."""
        if not self.save_file_path.exists():
            # print(f"No library file found at {self.save_file_path}. Starting fresh.")
            self.tracks = []
            return

        try:
            with open(self.save_file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            self.tracks = []
            for track_data in loaded_data:
                # Ensure all required fields are present, provide defaults for optionals if missing
                # This basic Track(**track_data) assumes JSON matches dataclass fields perfectly.
                # For robustness, might add more checks or default value handling here if schema evolves.
                try:
                    # Ensure genres is a list, as old saves might not have it or have None
                    if 'genres' not in track_data or track_data['genres'] is None:
                        track_data['genres'] = [] 
                    self.tracks.append(Track(**track_data))
                except TypeError as te:
                    print(f"Error creating Track object from data: {track_data}. Error: {te}")
            # print(f"Library loaded successfully from {self.save_file_path}. {len(self.tracks)} tracks.")
        except IOError as e:
            print(f"Error loading library file: {e}. Starting with an empty library.")
            self.tracks = []
        except json.JSONDecodeError as e:
            print(f"Error decoding library JSON from {self.save_file_path}: {e}. Starting with an empty library.")
            self.tracks = []
        except Exception as e:
            print(f"An unexpected error occurred during library load: {e}. Starting fresh.")
            self.tracks = []
        finally:
            self._notify_observers() # Notify even if loading failed / empty

    def add_track(self, track: Track):
        """Add a single track and save the library."""
        if not any(t.id == track.id for t in self.tracks): # Avoid duplicates by ID
            self.tracks.append(track)
            self._save_library()
            self._notify_observers()
        else:
            print(f"Track with ID {track.id} already exists in library.")
    
    def add_tracks(self, tracks_to_add: List[Track]):
        """Add multiple tracks at once and save the library."""
        added_count = 0
        for track in tracks_to_add:
            if not any(t.id == track.id for t in self.tracks):
                self.tracks.append(track)
                added_count += 1
        if added_count > 0:
            self._save_library()
            self._notify_observers()
        # print(f"Added {added_count} new tracks to the library.")
    
    def remove_track(self, track_to_remove: Track):
        """Remove a single track and save the library."""
        initial_len = len(self.tracks)
        self.tracks = [t for t in self.tracks if t.id != track_to_remove.id]
        if len(self.tracks) < initial_len:
            self._save_library()
            self._notify_observers()
            # print(f"Removed track: {track_to_remove.title}")
    
    def clear(self):
        """Clear all tracks from the library and save."""
        if not self.tracks: return # No need to save if already empty
        self.tracks.clear()
        self._save_library()
        self._notify_observers()
        # print("Library cleared.")
    
    def get_all_tracks(self) -> List[Track]:
        return self.tracks.copy()
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def _notify_observers(self):
        for observer in self.observers:
            if hasattr(observer, '_update_track_list') and callable(observer._update_track_list):
                try:
                    observer._update_track_list()
                except Exception as e:
                    print(f"Error notifying observer {observer}: {e}") 