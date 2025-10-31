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
from .contributions import TrackContribution, load_contributions_from_json

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
    liked: bool = False
    loved: bool = False
    mood_dependent: bool = False

class MusicLibrary:
    def __init__(self, profile_name: str = "default"):
        self.tracks: List[Track] = []
        self.observers: List = []
        self.app_data_dir: Path = self._get_app_data_dir(profile_name) # Store for reuse
        self.save_file_path: Path = self.app_data_dir / "library.json"
        
        # Load contributions
        self.contributions_file_path: Path = self.app_data_dir / "contributions.json"
        self.loaded_contributions: Dict[str, TrackContribution] = load_contributions_from_json(str(self.contributions_file_path))
        if self.loaded_contributions:
            print(f"Loaded {len(self.loaded_contributions)} track contributions from {self.contributions_file_path}")

        self._load_library()
    
    def _get_app_data_dir(self, profile_name: str) -> Path:
        """Gets the application data directory for a profile, creating it if necessary."""
        if os.name == 'nt': # Windows
            app_data_base = Path(os.getenv('APPDATA', ''))
        else: # Linux, macOS, other Unix-like
            app_data_base = Path(os.getenv('XDG_DATA_HOME', Path.home() / ".local" / "share"))
        
        app_dir = app_data_base / "CuratorApollon" / profile_name
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    def _get_save_file_path(self) -> Path:
        """Determines the full path to the library save file."""
        return self.app_data_dir / "library.json"

    def _apply_contribution_to_track(self, track: Track, contribution: TrackContribution):
        """Applies a contribution to a track, filling in missing (None or empty) fields."""
        if track.bpm is None and contribution.bpm is not None:
            track.bpm = contribution.bpm
        if not track.key and contribution.key: # Empty string check for key
            track.key = contribution.key
        if not track.time_signature and contribution.time_signature: # Empty string check for time_signature
            track.time_signature = contribution.time_signature
        if not track.camelot_position and contribution.camelot_key: # Empty string check for camelot_position
            track.camelot_position = contribution.camelot_key
        # For genres, we can extend existing genres with new ones from contribution, avoiding duplicates.
        if contribution.genre_keywords:
            existing_genres_lower = {g.lower() for g in track.genres}
            for genre in contribution.genre_keywords:
                if genre.lower() not in existing_genres_lower:
                    track.genres.append(genre)
        # Note: We are not currently overriding existing values in Track with contribution data if they already exist.
        # This is a design choice: contributions primarily fill *missing* data.

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

    def save(self):
        """Persist current library state to disk."""
        self._save_library()

    def _load_library(self):
        """Loads the music library from a JSON file if it exists."""
        if not self.save_file_path.exists():
            # print(f"No library file found at {self.save_file_path}. Starting fresh.")
            self.tracks = []
            # Still notify observers even if the library is fresh or file not found
            self._notify_observers()
            return

        try:
            with open(self.save_file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            self.tracks = []
            for track_data in loaded_data:
                try:
                    if 'genres' not in track_data or track_data['genres'] is None:
                        track_data['genres'] = []
                    
                    # Create the track object
                    track_obj = Track(**track_data)
                    
                    # Apply contributions if available for this track's ID
                    # Assuming track.id is the Spotify track ID used in contributions
                    if track_obj.id and track_obj.id in self.loaded_contributions:
                        contribution = self.loaded_contributions[track_obj.id]
                        self._apply_contribution_to_track(track_obj, contribution)
                        # print(f"Applied contribution to track {track_obj.id} during load.")

                    self.tracks.append(track_obj)
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
            # Apply contributions before adding to the library
            if track.id and track.id in self.loaded_contributions:
                contribution = self.loaded_contributions[track.id]
                self._apply_contribution_to_track(track, contribution)
                # print(f"Applied contribution to new track {track.id} before adding.")

            self.tracks.append(track)
            self._save_library()
            self._notify_observers()
        else:
            print(f"Track with ID {track.id} already exists in library.")
    
    def add_tracks(self, tracks_to_add: List[Track]):
        """Add multiple tracks at once and save the library."""
        added_count = 0
        newly_added_tracks = [] # Keep track of tracks actually added in this batch

        for track in tracks_to_add:
            if not any(t.id == track.id for t in self.tracks):
                # Apply contributions before adding to the library
                if track.id and track.id in self.loaded_contributions:
                    contribution = self.loaded_contributions[track.id]
                    self._apply_contribution_to_track(track, contribution)
                    # print(f"Applied contribution to new track {track.id} before batch adding.")
                
                self.tracks.append(track)
                newly_added_tracks.append(track) # Add to this list
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