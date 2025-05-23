# src/models/contributions.py
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

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class TrackContribution:
    """
    Represents metadata contributions for a track.
    Used to fill in missing information in the main music library.
    """
    track_id_spotify: Optional[str] = None  # Primary key for matching to Track.id
    bpm: Optional[float] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None
    camelot_key: Optional[str] = None
    genre_keywords: List[str] = field(default_factory=list)
    
    # Optional fields for tracking source/quality of contribution
    source_description: Optional[str] = None
    confidence: Optional[float] = None  # e.g., 0.0 (low) to 1.0 (high)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrackContribution':
        """Creates a TrackContribution instance from a dictionary."""
        return cls(
            track_id_spotify=data.get("track_id_spotify"),
            bpm=data.get("bpm"),
            key=data.get("key"),
            time_signature=data.get("time_signature"),
            camelot_key=data.get("camelot_key"),
            genre_keywords=data.get("genre_keywords", []),
            source_description=data.get("source_description"),
            confidence=data.get("confidence")
        )

def load_contributions_from_json(filepath: str) -> Dict[str, TrackContribution]:
    """
    Loads track contributions from a JSON file.
    Returns a dictionary mapping Spotify track IDs to TrackContribution objects.
    """
    contributions_map: Dict[str, TrackContribution] = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item_idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        print(f"Warning: Contribution item at index {item_idx} is not a dictionary, skipping.")
                        continue
                    contribution = TrackContribution.from_dict(item)
                    if contribution.track_id_spotify:
                        if contribution.track_id_spotify in contributions_map:
                            # Handle duplicate Spotify IDs in contributions.
                            # For now, let's log a warning and prefer the first one encountered.
                            # A more sophisticated strategy (e.g., based on confidence) could be added.
                            print(f"Warning: Duplicate track_id_spotify '{contribution.track_id_spotify}' in contributions file. Using first entry.")
                        else:
                            contributions_map[contribution.track_id_spotify] = contribution
                    else:
                        print(f"Warning: Contribution item at index {item_idx} missing 'track_id_spotify', skipping.")
            else:
                print(f"Warning: Expected a list of contributions in {filepath}, got {type(data)}. No contributions loaded.")
    except FileNotFoundError:
        # This is not an error; the contributions file is optional.
        print(f"Contributions file not found: {filepath}. Proceeding without user-provided contributions.")
    except json.JSONDecodeError:
        print(f"Error decoding JSON from contributions file: {filepath}. Please check its format.")
    except Exception as e:
        # Catch other potential errors during loading.
        print(f"An unexpected error occurred while loading contributions from {filepath}: {e}")
    return contributions_map 