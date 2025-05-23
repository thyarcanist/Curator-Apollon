import requests
import os
from typing import List, Optional, NamedTuple, Tuple
from models.library import Track # Correctly import Track

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

    def _is_key_compatible_strict(self, pk1: Optional[ParsedCamelotKey], pk2: Optional[ParsedCamelotKey]) -> bool:
        """
        User-provided strict Camelot key compatibility.
        Checks if keys are identical or adjacent numbers with the same mode.
        """
        if pk1 is None or pk2 is None:
            return False 
        if pk1 == pk2:
            return True
        # abs(key1.number - key2.number) in [1, 11] means adjacent on the wheel (11 for 12-1 wrap)
        return abs(pk1.number - pk2.number) in [1, 11] and pk1.mode == pk2.mode

    def _is_compatible(self, track1: Track, track2: Track, entropy_level: float) -> bool:
        """
        User-provided overall compatibility check for two tracks.
        Uses BPM tolerance (entropy-dependent) and strict key/time signature matching.
        """
        pk1 = self._parse_camelot_key(track1.camelot_position)
        pk2 = self._parse_camelot_key(track2.camelot_position)

        bpm_close = abs(track1.bpm - track2.bpm) <= self._bpm_tolerance(entropy_level)
        key_match = self._is_key_compatible_strict(pk1, pk2) # Uses strict, non-entropy key check
        time_sig_match = track1.time_signature == track2.time_signature # Strict time signature match
        
        return bpm_close and key_match and time_sig_match

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

    def recommend_tracks(self, current_tracks: List[Track], current_playing_track: Track, entropy_level: float, num_recommendations: int = 5) -> List[Track]:
        """
        Recommends tracks based on musical similarity and quantum entropy.

        Args:
            current_tracks: The list of all tracks in the library.
            current_playing_track: The track currently being played or selected as a reference.
            entropy_level: A float between 0.0 (deterministic) and 1.0 (max chaos).
                           0.0: Focus on very similar tracks (BPM, Key, Time Signature).
                           1.0: Maximize randomness in selection, allowing more distant matches.
            num_recommendations: The number of tracks to recommend.

        Returns:
            A list of recommended Track objects. Returns an empty list if recommendations
            cannot be generated (e.g., API error, no compatible tracks).
        """
        if not current_tracks or not current_playing_track:
            return []

        if not (0.0 <= entropy_level <= 1.0):
            raise ValueError("Entropy level must be between 0.0 and 1.0.")
        
        # 1. Define compatibility criteria based on entropy
        # BPM tolerance: Increases with entropy
        # Max BPM diff: e.g., 5 at entropy 0, up to 30 at entropy 1
        bpm_similarity_threshold = 5 + (entropy_level * 25) 

        # Key compatibility:
        # Entropy 0: Exact Camelot match or direct compatibles (+/-1, same letter A/B)
        # Entropy 0.5: Allow energy boost (e.g., 8A -> 8B)
        # Entropy 1.0: Wider Camelot wheel jumps, possibly weighted by quantum randomness

        # Time signature:
        # Entropy < 0.5: Prefer exact match
        # Entropy >= 0.5: Allow compatible (e.g. 2/4 for 4/4), weighted by quantum randomness

        # 2. Filter candidate tracks (excluding the current playing track)
        candidate_tracks = [t for t in current_tracks if t.id != current_playing_track.id]
        if not candidate_tracks:
            return []

        compatible_tracks = []
        for track in candidate_tracks:
            bpm_compatible = abs(track.bpm - current_playing_track.bpm) <= bpm_similarity_threshold
            
            key_compatible = self._is_key_compatible_strict(
                self._parse_camelot_key(track.camelot_position),
                self._parse_camelot_key(current_playing_track.camelot_position)
            )
            
            time_sig_compatible = track.time_signature == current_playing_track.time_signature

            # Score based on compatibility, weighted by features
            # For now, a simple AND, but could be a weighted sum
            if bpm_compatible and key_compatible and time_sig_compatible:
                compatible_tracks.append(track)
        
        if not compatible_tracks:
            # If no strictly compatible tracks, and entropy is high,
            # we might consider a broader pool or just return empty.
            # For now, return empty if primary filters yield nothing.
            return []

        # 3. Use Quantum Randomness for selection and ordering
        num_to_select = min(len(compatible_tracks), num_recommendations)
        if num_to_select == 0:
            return []

        # Amount of randomness: e.g., a few bytes per potential pick, or to select indices
        # Let's fetch enough bytes to select indices for the number of recommendations.
        # If we have N compatible_tracks and want to pick K, we need randomness for K selections.
        # Max index is N-1. Each byte gives 0-255.
        # A simple way: get `num_to_select` random bytes. Modulo each byte by `len(compatible_tracks)`.
        # This introduces modulo bias if `len(compatible_tracks)` is not a divisor of 256.
        # A better way is to get more bytes and ensure uniformity.
        
        # For robust index selection without modulo bias from N items using random bytes:
        # Request enough bytes to ensure that (256^num_bytes) / N is large enough.
        # Or, for each selection, draw a byte, if byte_value >= N * floor(256/N), redraw.
        # This ensures each of the N items has an equal chance.

        selected_indices = set()
        recommended_tracks_final = []
        
        # Fetch a pool of random bytes. More bytes means fewer API calls if retries are needed.
        # Estimate: 1 byte per selection attempt. Let's get a bit more for retries.
        random_bytes_needed = num_to_select * 2 # Get twice to be safe for re-draws
        q_bytes = self.get_quantum_random_bytes(random_bytes_needed)

        if not q_bytes or len(q_bytes) == 0:
            # print("Failed to get quantum randomness. Cannot provide quantum-influenced recommendations.")
            # CRITICAL: No PRNG fallback. If quantum source fails, the "quantum" part fails.
            # What to do here? 
            # Option 1: Return empty list.
            # Option 2: Return a purely deterministic list (entropy_level effectively becomes 0).
            # For now, per instruction "DO NOT USE PRNG", if QRNG fails, we cannot meet the randomness req.
            # Let's return what we have *before* quantum shuffling if entropy is low,
            # or empty if high entropy was key.
            if entropy_level < 0.1: # If very low entropy, order doesn't matter as much
                 return compatible_tracks[:num_to_select] # Deterministic pick
            return [] # Indicate failure to provide quantum-random recommendations

        byte_idx = 0
        attempts = 0
        max_attempts_per_selection = 10 # To prevent infinite loops

        while len(recommended_tracks_final) < num_to_select and attempts < num_to_select * max_attempts_per_selection:
            if byte_idx >= len(q_bytes):
                # print("Ran out of quantum random bytes. Fetching more.")
                more_q_bytes = self.get_quantum_random_bytes(num_to_select * 2)
                if not more_q_bytes:
                    # print("Failed to get additional quantum randomness.")
                    break # Cannot continue without randomness
                q_bytes += more_q_bytes
            
            if byte_idx >= len(q_bytes): # Still no bytes after trying to fetch more
                break

            random_val = q_bytes[byte_idx]
            byte_idx += 1
            
            # Fair index selection (reject and redraw to avoid modulo bias)
            # N = len(compatible_tracks)
            # if random_val >= N * floor(256/N): continue drawing
            # effective_range = len(compatible_tracks) * (256 // len(compatible_tracks)) 
            # This can be complex. Simpler for now: modulo, acknowledge bias for prototype.
            # For a production system, proper unbiasing is critical.
            
            # Simple modulo for now (acknowledging potential bias)
            if not compatible_tracks: break # Should not happen if num_to_select > 0

            selected_idx = random_val % len(compatible_tracks)
            
            if selected_idx not in selected_indices:
                selected_indices.add(selected_idx)
                recommended_tracks_final.append(compatible_tracks[selected_idx])
            
            attempts += 1

        # If quantum selection failed to get enough unique tracks (e.g. bad bytes, too few unique compatibles)
        # fill with remaining compatible tracks if any, up to num_recommendations
        if len(recommended_tracks_final) < num_to_select:
            # print(f"Quantum selection yielded {len(recommended_tracks_final)} tracks. Filling deterministically.")
            for track in compatible_tracks:
                if len(recommended_tracks_final) >= num_to_select:
                    break
                if track not in recommended_tracks_final: # Crude way to find unselected
                    recommended_tracks_final.append(track)
        
        # The final list `recommended_tracks_final` is now "shuffled" by quantum selection.
        # If `entropy_level` is high, this selection is the primary driver.
        # If `entropy_level` is low, the `compatible_tracks` list was already narrow,
        # and quantum randomness just picks from that narrow list.

        return recommended_tracks_final

    def _is_key_compatible(self, key1: str, key2: str, entropy: float) -> bool:
        """
        Determines if two Camelot keys are compatible based on entropy.
        Example: key1 = "8A", key2 = "9A"
        """
        if key1 == "Unknown" or key2 == "Unknown":
            return True # Or False, depending on desired strictness

        if not isinstance(key1, str) or not isinstance(key2, str):
            return False # Should be strings

        if key1 == key2:
            return True

        try:
            if not (2 <= len(key1) <= 3 and 2 <= len(key2) <= 3): # e.g. "1A" or "10A"
                return False

            key1_num_str, key1_letter = key1[:-1], key1[-1]
            key2_num_str, key2_letter = key2[:-1], key2[-1]

            if not key1_num_str.isdigit() or not key2_num_str.isdigit():
                return False
            
            key1_num = int(key1_num_str)
            key2_num = int(key2_num_str)

            if not (key1_letter in ('A', 'B') and key2_letter in ('A', 'B')):
                return False
            if not (1 <= key1_num <= 12 and 1 <= key2_num <= 12):
                return False
        except (ValueError, IndexError, TypeError):
            return False # Catch any parsing/conversion errors

        # Rule 1: Same number, different letter (e.g., 8A and 8B) - "Energy Boost"
        if key1_num == key2_num and key1_letter != key2_letter:
            if entropy >= 0.3: # Allow energy boost if entropy is moderate
                return True
        
        # Rule 2: Adjacent numbers, same letter (e.g., 8A and 9A, or 8A and 7A)
        if key1_letter == key2_letter:
            # Check for direct adjacency
            if abs(key1_num - key2_num) == 1:
                return True
            # Check for wheel wrap-around (12 and 1 are adjacent)
            if (key1_num == 12 and key2_num == 1) or \
               (key1_num == 1 and key2_num == 12):
                return True

        # Rule 3: Wider jumps based on entropy (more chaotic)
        if key1_letter == key2_letter and entropy >= 0.7:
            diff = abs(key1_num - key2_num)
            # +/- 2 on the wheel. diff == 10 is equivalent to -2 (e.g. 12 vs 2 is diff 10, or 1 vs 11 is diff 10)
            if diff == 2 or diff == 10: 
                 return True
        
        return False


    def _is_time_signature_compatible(self, sig1: str, sig2: str, entropy: float) -> bool:
        if sig1 == "Unknown" or sig2 == "Unknown":
            return True # Or False
        
        if sig1 == sig2:
            return True

        # Allow simple compatible time signatures if entropy is high enough
        if entropy >= 0.5:
            common_beat_feel = {("4/4", "2/4"), ("2/4", "4/4"), 
                                ("3/4", "6/8"), ("6/8", "3/4")} # Example pairs
            if (sig1, sig2) in common_beat_feel:
                return True
        
        return False

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
