import requests
import os
from typing import List, Optional, NamedTuple, Tuple
from models.library import Track # Correctly import Track
import math # For ceiling function if needed for centroid mode finding
from collections import Counter # For finding mode

# Placeholder for Track class if not imported, for type hinting
# class Track: # Remove placeholder
#     id: str
#     title: str
#     artist: str
#     bpm: float
#     key: str
#     camelot_position: str
#     energy_level: float
#     time_signature: str = "4/4"
#     # Add other fields as necessary based on your Track model

# Define broad genre keywords for thematic matching
# This list can be expanded and refined
BROAD_GENRE_KEYWORDS = [
    "ambient", "atmospheric", "soundtrack", "score", "experimental",
    "electronic", "synth", "idm", "techno", "house", "trance", "downtempo",
    "industrial", "ebm", "aggrotech", "noise",
    "rock", "metal", "punk", "alternative", "indie", "post-rock", "shoegaze",
    "classical", "orchestral", "choral",
    "jazz", "blues",
    "folk", "acoustic",
    "hip hop", "rap",
    "reggae", "dub",
    "world"
]

class ParsedCamelotKey(NamedTuple):
    number: int
    mode: str  # 'A' or 'B'

class EntropyService:
    def __init__(self, api_key: Optional[str] = None, api_link: Optional[str] = None):
        """
        Initializes the EntropyService.
        API key and link can be provided directly or set as environment variables
        OCCYBYTE_API_KEY and OCCYBYTE_API_LINK.
        """
        self.api_key = api_key or os.getenv("OCCYBYTE_API_KEY")
        self.api_link = api_link or os.getenv("OCCYBYTE_API_LINK")

        if not self.api_key:
            raise ValueError("OccyByte API key not provided or found in environment variables (OCCYBYTE_API_KEY).")
        if not self.api_link:
            raise ValueError("OccyByte API link not provided or found in environment variables (OCCYBYTE_API_LINK).")

    def get_quantum_random_bytes(self, size: int) -> Optional[bytes]:
        """
        Fetches raw, unwhitened quantum random data from the OccyByte Eris API.

        Args:
            size: The number of bytes of random data to fetch.

        Returns:
            A byte string containing the quantum random data, or None if an error occurs.
            Does not fall back to PRNG.
        """
        if size <= 0:
            # print("Requested size for random bytes must be positive.")
            return None

        url = f"{self.api_link.rstrip('/')}/api/eris/raw?size={size}"
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/octet-stream"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10) # 10-second timeout
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            
            # Optionally, check X-QDS-* headers for metadata if needed
            # qds_status = response.headers.get("X-QDS-Status")
            # print(f"QDS Status: {qds_status}")

            return response.content
        except requests.exceptions.HTTPError as e:
            # print(f"HTTP error occurred while fetching quantum randomness: {e}")
            # print(f"Response status: {e.response.status_code}")
            # print(f"Response body: {e.response.text}")
            # Consider more specific error handling based on status codes
            if e.response.status_code == 401: # Unauthorized
                # print("Authentication failed. Check your OccyByte API key.")
                pass
            elif e.response.status_code == 403: # Forbidden (e.g. key valid but no access to endpoint)
                 # print("Access forbidden. The API key may not have permission for this resource.")
                 pass
            return None
        except requests.exceptions.ConnectionError:
            # print("Connection error. Could not connect to the OccyByte API.")
            return None
        except requests.exceptions.Timeout:
            # print("Request timed out while fetching quantum randomness.")
            return None
        except requests.exceptions.RequestException as e:
            # print(f"An unexpected error occurred while fetching quantum randomness: {e}")
            return None

    def _parse_camelot_key(self, camelot_str: str) -> Optional[ParsedCamelotKey]:
        """Parses a Camelot string (e.g., '8A', '12B') into a ParsedCamelotKey object."""
        if not isinstance(camelot_str, str) or not (2 <= len(camelot_str) <= 3):
            return None
        try:
            number = int(camelot_str[:-1])
            mode = camelot_str[-1]
            if not (1 <= number <= 12 and mode in ('A', 'B')):
                return None
            return ParsedCamelotKey(number, mode)
        except ValueError:
            return None

    # User-provided helper methods (adapted)
    def _bpm_tolerance(self, entropy_level: float) -> int:
        """Calculates BPM tolerance based on entropy level."""
        return 5 + int(entropy_level * 20)  # expands range with entropy

    def _is_key_compatible(self, pk1: Optional[ParsedCamelotKey], pk2: Optional[ParsedCamelotKey], entropy_level: float) -> bool:
        """
        Determines Camelot key compatibility based on entropy_level.
        """
        if pk1 is None or pk2 is None:
            return False

        if pk1 == pk2:
            return True

        # Medium-Low Entropy (0.25 - 0.5): Adjacent numbers, same mode
        if entropy_level <= 0.5:
            # Adjacent numbers, same mode (e.g., 8A & 9A)
            is_adjacent_same_mode = (
                abs(pk1.number - pk2.number) == 1 and \
                pk1.mode == pk2.mode
            )
            # Wheel wrap-around for adjacency (12 and 1), same mode
            is_wrap_around_same_mode = (
                ((pk1.number == 12 and pk2.number == 1) or \
                 (pk1.number == 1 and pk2.number == 12)) and \
                pk1.mode == pk2.mode
            )
            if is_adjacent_same_mode or is_wrap_around_same_mode:
                return True
            if entropy_level <= 0.25: # Stricter for very low entropy
                return False 

        # Medium-High Entropy (0.5 - 0.75): Allow "energy boost" + medium-low rules
        if entropy_level > 0.5 and entropy_level <= 0.75:
            is_energy_boost = (pk1.number == pk2.number and pk1.mode != pk2.mode)
            is_adjacent_same_mode = (
                abs(pk1.number - pk2.number) == 1 and \
                pk1.mode == pk2.mode
            )
            is_wrap_around_same_mode = (
                ((pk1.number == 12 and pk2.number == 1) or \
                 (pk1.number == 1 and pk2.number == 12)) and \
                pk1.mode == pk2.mode
            )
            if is_energy_boost or is_adjacent_same_mode or is_wrap_around_same_mode:
                return True

        # High Entropy (0.75 - 1.0): Allow wider jumps + energy boost + medium-low rules
        if entropy_level > 0.75:
            is_energy_boost = (pk1.number == pk2.number and pk1.mode != pk2.mode)
            is_adjacent_same_mode = (
                abs(pk1.number - pk2.number) == 1 and \
                pk1.mode == pk2.mode
            )
            is_wrap_around_same_mode = (
                ((pk1.number == 12 and pk2.number == 1) or \
                 (pk1.number == 1 and pk2.number == 12)) and \
                pk1.mode == pk2.mode
            )
            # +/- 2 numbers, same mode (e.g., 8A to 10A or 8A to 6A)
            diff = abs(pk1.number - pk2.number)
            is_wider_jump_same_mode = (
                (diff == 2 or diff == 10) and pk1.mode == pk2.mode # diff 10 for wrap-around
            )
            if is_energy_boost or is_adjacent_same_mode or is_wrap_around_same_mode or is_wider_jump_same_mode:
                return True
        return False

    def _is_time_signature_compatible(self, ts1: str, ts2: str, entropy_level: float) -> bool:
        """Determines time signature compatibility based on entropy_level."""
        if ts1 is None or ts2 is None or ts1 == "Unknown" or ts2 == "Unknown":
            return False # Or True if we want to be lenient with unknowns
        
        if ts1 == ts2:
            return True

        # High Entropy (e.g., >= 0.6): Allow harmonically related time signatures
        if entropy_level >= 0.6:
            # Define common compatible pairs (can be expanded)
            compatible_pairs = {
                frozenset({"4/4", "2/4"}),
                frozenset({"4/4", "2/2"}), # Cut time
                frozenset({"3/4", "6/8"}), # Often interchangeable feel
                # Add more as needed, e.g., 12/8 with 4/4 (triplet feel vs straight)
            }
            if frozenset({ts1, ts2}) in compatible_pairs:
                return True
        
        return False

    def _get_track_genre_keywords(self, track_genres: List[str]) -> set:
        """Extracts broad genre keywords from a track's genre list."""
        if not track_genres:
            return set()
        
        found_keywords = set()
        normalized_genres = [g.lower() for g in track_genres]
        
        for broad_keyword in BROAD_GENRE_KEYWORDS:
            for genre_tag in normalized_genres:
                if broad_keyword in genre_tag: # Checking if "ambient" is in "dark ambient"
                    found_keywords.add(broad_keyword)
        return found_keywords

    def _are_genres_compatible(self, genres1: List[str], genres2: List[str], entropy_level: float) -> bool:
        """Determines genre compatibility based on entropy and broad keyword matching."""
        if not genres1 and not genres2: # Both have no genres
            return True # Or False, depending on desired behavior for ungenred tracks
        if not genres1 or not genres2: # One has genres, the other doesn't
            if entropy_level >= 0.75: # At high entropy, be lenient if one track lacks genres
                return True
            return False

        norm_genres1 = {g.lower() for g in genres1}
        norm_genres2 = {g.lower() for g in genres2}

        # Low Entropy: Require at least one exact shared genre tag
        if entropy_level < 0.3:
            return bool(norm_genres1.intersection(norm_genres2))

        # Medium Entropy: Prefer exact match, then check for shared broad keywords
        if entropy_level < 0.7:
            if norm_genres1.intersection(norm_genres2):
                return True
            # Check for shared broad keywords
            keywords1 = self._get_track_genre_keywords(genres1)
            keywords2 = self._get_track_genre_keywords(genres2)
            if keywords1.intersection(keywords2):
                return True
            return False
        
        # High Entropy: Any overlap (exact or keyword) is a weak positive signal, mostly permissive
        # For simplicity at high entropy, any thematic link is enough.
        # Or, simply return True to make genre less of a barrier.
        if norm_genres1.intersection(norm_genres2):
            return True
        keywords1 = self._get_track_genre_keywords(genres1)
        keywords2 = self._get_track_genre_keywords(genres2)
        if keywords1.intersection(keywords2):
            return True
        
        # At very high entropy, if no direct or keyword match, still might be compatible overall
        # The _is_compatible method will combine this with BPM, key, etc.
        # So if genres *don't* match at all, this will return False, but that might be overridden
        # by strong matches in other areas if we change how scores are combined.
        # For now, if no genre link found, return False unless entropy is maxed out.
        if entropy_level >= 0.9: # Very permissive at max chaos
            return True
        return False

    def _is_compatible(self, track1: Track, track2: Track, entropy_level: float) -> bool:
        """
        Overall compatibility check using entropy-aware helpers, now including genres.
        """
        pk1 = self._parse_camelot_key(track1.camelot_position)
        pk2 = self._parse_camelot_key(track2.camelot_position)

        bpm_close = abs(track1.bpm - track2.bpm) <= self._bpm_tolerance(entropy_level)
        key_match = self._is_key_compatible(pk1, pk2, entropy_level)
        time_sig_match = self._is_time_signature_compatible(track1.time_signature, track2.time_signature, entropy_level)
        genre_match = self._are_genres_compatible(track1.genres, track2.genres, entropy_level)
        
        # Adjust weighting based on entropy. At high entropy, individual failures are less critical if others match.
        if entropy_level < 0.5: # Stricter: all must match
            return bpm_close and key_match and time_sig_match and genre_match
        elif entropy_level < 0.8: # Medium: allow one mismatch if others strong
            # e.g., 3 out of 4 conditions met
            return sum([bpm_close, key_match, time_sig_match, genre_match]) >= 3
        else: # High entropy: very lenient, e.g., 2 out of 4, or even prioritize quantum shuffle more
            return sum([bpm_close, key_match, time_sig_match, genre_match]) >= 2

    def _quantum_shuffle(self, items: List, qr_bytes: bytes) -> List:
        """
        User-provided Fisher-Yates shuffle using QRNG bytes.
        Shuffles a copy of the items list.
        """
        if not qr_bytes or not items:
            return list(items) # Return a copy if no bytes or no items
        
        n = len(items)
        items_copy = list(items)
        
        byte_idx = 0
        for i in range(n - 1, 0, -1):  # Iterate from n-1 down to 1
            if byte_idx >= len(qr_bytes):
                # print("Warning: Not enough quantum bytes for a full shuffle.")
                break 
            
            random_byte_val = qr_bytes[byte_idx]
            j = random_byte_val % (i + 1)  # Determine swap index j such that 0 <= j <= i
            byte_idx += 1
            
            items_copy[i], items_copy[j] = items_copy[j], items_copy[i]
            
        return items_copy

    # Placeholder for centroid calculation - to be implemented next
    def _calculate_playlist_centroid(self, tracks: List[Track]) -> Optional[dict]:
        if not tracks:
            return None

        avg_bpm = 120.0
        valid_bpms = [t.bpm for t in tracks if t.bpm is not None and t.bpm > 0]
        if valid_bpms: avg_bpm = sum(valid_bpms) / len(valid_bpms)

        mode_camelot_parsed = None
        parsed_keys = [self._parse_camelot_key(t.camelot_position) for t in tracks]
        valid_parsed_keys = [pk for pk in parsed_keys if pk is not None]
        if valid_parsed_keys: mode_camelot_parsed = Counter(valid_parsed_keys).most_common(1)[0][0]
        
        mode_time_sig = "4/4"
        valid_time_sigs = [t.time_signature for t in tracks if t.time_signature and t.time_signature != "Unknown"]
        if valid_time_sigs: mode_time_sig = Counter(valid_time_sigs).most_common(1)[0][0]

        # Genre Centroid: Most common broad keywords
        all_track_keywords = []
        for t in tracks:
            all_track_keywords.extend(list(self._get_track_genre_keywords(t.genres)))
        
        centroid_genres_keywords = []
        if all_track_keywords:
            keyword_counts = Counter(all_track_keywords)
            # Take top N keywords, e.g., top 3, or those above a certain frequency
            centroid_genres_keywords = [kw for kw, count in keyword_counts.most_common(3)]
            
        return {
            'bpm': avg_bpm,
            'camelot_parsed': mode_camelot_parsed,
            'time_signature': mode_time_sig,
            'genre_keywords': centroid_genres_keywords # List of strings (broad keywords)
        }

    def recommend_tracks(self, current_tracks: List[Track], current_playing_track: Track, entropy_level: float, num_recommendations: int = 5) -> List[Track]:
        """
        Recommends tracks based on musical similarity (now more entropy-aware) and quantum entropy.
        Integrates a basic playlist centroid concept for high entropy.
        """
        if not current_tracks or not current_playing_track:
            return []
        if not (0.0 <= entropy_level <= 1.0):
            raise ValueError("Entropy level must be between 0.0 and 1.0.")

        candidate_tracks = [t for t in current_tracks if t.id != current_playing_track.id]
        if not candidate_tracks:
            return []

        playlist_centroid_features = self._calculate_playlist_centroid(current_tracks)
        
        # Create a pseudo-track object for the centroid if features are available
        # This helps in using the _is_compatible method with the centroid
        centroid_track_surrogate = None
        if playlist_centroid_features and playlist_centroid_features['camelot_parsed']:
            # Need to convert ParsedCamelotKey back to string for Track model, or adapt Track model/compatibility
            # For now, let's assume Track can be instantiated with these core features for comparison.
            # This part needs care: Track expects camelot_position as string.
            camelot_str_from_parsed = f"{playlist_centroid_features['camelot_parsed'].number}{playlist_centroid_features['camelot_parsed'].mode}"
            centroid_track_surrogate = Track(
                id="_playlist_centroid", 
                title="Playlist Centroid", 
                artist="Various", 
                bpm=playlist_centroid_features['bpm'], 
                key="", # Raw key not derived for centroid yet
                camelot_position=camelot_str_from_parsed, 
                energy_level=0.5, # Placeholder
                time_signature=playlist_centroid_features['time_signature'],
                genres=playlist_centroid_features.get('genre_keywords', []) # Use derived centroid genre keywords
            )

        compatible_tracks = []
        for track in candidate_tracks:
            is_compatible_with_current = self._is_compatible(track, current_playing_track, entropy_level)
            
            is_compatible_with_centroid = False
            if centroid_track_surrogate and entropy_level > 0.55: # Bias towards centroid at higher entropy
                centroid_compatibility_entropy = min(1.0, entropy_level + 0.15) # Slightly boost entropy for centroid matching
                is_compatible_with_centroid = self._is_compatible(track, centroid_track_surrogate, centroid_compatibility_entropy)

            if is_compatible_with_current or is_compatible_with_centroid:
                compatible_tracks.append(track)
        
        # Remove duplicates if a track was compatible with both
        if compatible_tracks:
            seen_ids = set()
            unique_compatible_tracks = []
            for track in compatible_tracks:
                if track.id not in seen_ids:
                    unique_compatible_tracks.append(track)
                    seen_ids.add(track.id)
            compatible_tracks = unique_compatible_tracks

        if not compatible_tracks:
            return []

        num_to_select = min(len(compatible_tracks), num_recommendations)
        if num_to_select == 0:
            return []

        bytes_for_shuffle = len(compatible_tracks) - 1 if len(compatible_tracks) > 1 else 0
        q_bytes = None
        if bytes_for_shuffle > 0:
            q_bytes = self.get_quantum_random_bytes(bytes_for_shuffle)

        if not q_bytes:
            if entropy_level < 0.1 or len(compatible_tracks) <= 1:
                return compatible_tracks[:num_to_select]
            return []
        
        shuffled_compatible_tracks = self._quantum_shuffle(compatible_tracks, q_bytes)
        return shuffled_compatible_tracks[:num_to_select]

# Example Usage (requires OCCYBYTE_API_KEY and OCCYBYTE_API_LINK to be set as env vars):
# if __name__ == "__main__":
#     try:
#         entropy_service = EntropyService()
#         
#         # Test quantum byte fetching
#         print("Fetching 10 quantum random bytes...")
#         q_bytes = entropy_service.get_quantum_random_bytes(10)
#         if q_bytes:
#             print(f"Received bytes: {q_bytes.hex()}")
#         else:
#             print("Failed to fetch quantum random bytes.")

#         # --- Mock Data for recommend_tracks ---
#         # Ensure you have a Track class defined or imported as per your project structure
#         # from models.library import Track 

#         mock_tracks = [
#             Track(id="t1", title="Song A", artist="Artist X", bpm=120.0, key="8A", camelot_position="8A", energy_level=0.7, time_signature="4/4"),
#             Track(id="t2", title="Song B", artist="Artist X", bpm=122.0, key="8A", camelot_position="8A", energy_level=0.6, time_signature="4/4"),
#             Track(id="t3", title="Song C", artist="Artist Y", bpm=125.0, key="9A", camelot_position="9A", energy_level=0.8, time_signature="4/4"),
#             Track(id="t4", title="Song D", artist="Artist Z", bpm=118.0, key="8B", camelot_position="8B", energy_level=0.5, time_signature="4/4"),
#             Track(id="t5", title="Song E", artist="Artist X", bpm=130.0, key="10A", camelot_position="10A", energy_level=0.9, time_signature="4/4"),
#             Track(id="t6", title="Song F", artist="Artist Y", bpm=120.0, key="7A", camelot_position="7A", energy_level=0.7, time_signature="3/4"),
#             Track(id="t7", title="Song G", artist="Artist Z", bpm=150.0, key="1A", camelot_position="1A", energy_level=0.8, time_signature="4/4"),
#             Track(id="t8", title="Song H", artist="Artist X", bpm=121.0, key="8A", camelot_position="8A", energy_level=0.6, time_signature="4/4"), # Duplicate-like
#         ]
#         current_song = mock_tracks[0]
#         
#         print(f"\nRecommending tracks based on '{current_song.title}' with low entropy (0.1):")
#         recommendations_low = entropy_service.recommend_tracks(mock_tracks, current_song, entropy_level=0.1, num_recommendations=3)
#         for track in recommendations_low:
#             print(f"  - {track.title} (BPM: {track.bpm}, Key: {track.camelot_position}, Sig: {track.time_signature})")

#         print(f"\nRecommending tracks based on '{current_song.title}' with high entropy (0.9):")
#         recommendations_high = entropy_service.recommend_tracks(mock_tracks, current_song, entropy_level=0.9, num_recommendations=3)
#         for track in recommendations_high:
#             print(f"  - {track.title} (BPM: {track.bpm}, Key: {track.camelot_position}, Sig: {track.time_signature})")
#             
#     except ValueError as e:
#         print(f"Initialization Error: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
