# Curator Apollon - MVP Specification
*Minimal Viable Product for Personal Music Analysis & Discovery*

## Core Purpose
A personal tool to analyze music libraries and discover new tracks based on music theory relationships and customizable entropy.
Going to open source it for community-curated metadata gathering, my own API will be used to power the randomness. At the minimum,
it can be used to import and then export a playlist without doing anything fishy because that's saved in your personal cache.

## 1. Essential Features

### Library Management
- Add individual tracks (manual or Spotify URL)
- Import Spotify playlists (fetches available metadata)
- Basic track removal (selected or all)
- **Persistent Library**: Saves and loads library to/from `library.json` in app data directory.
- Simple list view of library (Title, Artist, BPM, Key).

### Analysis Core
- **Track Data**: Displays BPM, key, Camelot position, energy level, album, time signature, genres.
- **Playlist Statistics**: Aggregated views for average BPM, common keys, energy, Camelot positions, time signatures, and genre distributions.
- **Literary Analysis**: Basic textual analysis of titles and artists (common words, character usage etc.).
- Album art display for the currently selected track.

### Discovery Engine (`EntropyService`)
- **Quantum Recommendations**: Generates track suggestions using true quantum randomness (via OccyByte API).
- **Entropy Slider**: Controls recommendation style from "Comfort Zone" (strict matches) to "Cosmic Drift" (musically adventurous, looser connections).
- **Dynamic Compatibility**: Entropy level influences matching strictness for:
    - BPM (tolerance expands with entropy).
    - Musical Key (Camelot wheel; allows more distant relations at higher entropy).
    - Time Signature (allows compatible changes at higher entropy).
    - Genres (from exact matches to broad keyword/thematic links at higher entropy).
- **Playlist Centroid**: At higher entropy levels, recommendations can be based on the musical centroid (average characteristics) of the current playlist, acting as a 'surrogate seed'.
- **No PRNG Fallback**: Relies exclusively on quantum source for randomness in shuffling and selection processes.

## 2. Primary Interface

### Main Views
```
[Library View]
• Track listing (Title, Artist, BPM, Key)
• Controls: Add Track, Import Playlist, Remove Selected, Remove All, Export Playlist.
• Track selection drives the Analysis and Discovery views.

[Analysis View]
• Current Track Details: Full metadata display including album art.
• Navigation: Previous/Next track in library.
• Playlist Analysis: Detailed musical and literary statistics for the entire library.
• Refresh button for stats.

[Discovery View]
• Entropy Slider: "Comfort Zone <-> Cosmic Drift" (0.0 to 1.0).
• Seed Track Display: Shows the currently selected track from the Library view used as the basis for recommendations.
• "Get Quantum Recommendations" Button: Initiates the recommendation process.
• Recommendations List: Displays suggested tracks (Title, Artist, BPM, Key, Genres).
```

## 3. Core Workflows

### Track Import & Management
1. Add single track (Spotify URL or manual entry).
2. Import entire Spotify playlist.
3. Library is automatically saved after modifications.
4. View and manage tracks in the Library View.

### Analysis Flow
1. Select a track in the Library View.
2. View detailed analysis of the selected track in the Analysis View.
3. View aggregated statistics for the entire library in the Analysis View.
4. Navigate through tracks using Previous/Next buttons.

### Discovery Flow
1. Ensure the library has tracks and select a desired "seed" track in the Library View.
2. Navigate to the Discovery View.
3. Adjust the Entropy Slider to the desired level of musical exploration.
4. Click "Get Quantum Recommendations".
5. Review the list of quantum-generated track suggestions.

## 4. Project Status & Features

### Current Implemented Features (as of this update)
- Spotify API connection for track and playlist import.
- Detailed track analysis and metadata display (BPM, Key, Camelot, Energy, Time Signature, Genres, Album Art).
- Robust library management with persistence (add, remove, clear, load/save).
- Comprehensive playlist-level statistical analysis (musical and literary).
- Quantum-powered recommendation engine (`EntropyService`) with:
    - Entropy-controlled compatibility logic.
    - Playlist centroid concept.
    - True random shuffling.
- Tabbed UI for Library, Analysis, and Discovery.

### Potential Future Enhancements / Goals
- Batch analysis of local files (if metadata can be extracted/provided).
- Advanced filtering and sorting in the library view.
- More sophisticated music theory visualizations.
- Direct playback integration (if feasible and permitted).
- User-configurable recommendation parameters (e.g., number of recommendations).
- Exporting generated recommendations.
- Semantic fingerprinting for title/mood analysis (advanced `EntropyService` feature).
- Weighted Markov chains, fractal affinity decay for recommendation evolution (advanced `EntropyService` features).

The goal is for it to reflect, you, the user in songform. 

## 5. Essential UX Elements

### Key Interactions
- Add/Remove tracks and import playlists.
- Select tracks to view detailed analysis.
- Adjust entropy slider and click to get quantum recommendations.
- View library, analysis, and discovery information in dedicated, clear tabs.
- Status bar for feedback on operations.

### Visual Priority
- Clean, dark-themed interface (`ttkbootstrap`).
- Clear data presentation in tables and lists.
- Intuitive controls for core actions.
- Consistent font and styling.

## 6. Basic Style Guide

### Interface
- Theme: `darkly` (from ttkbootstrap).
- Custom Font: `CommitMono` for a distinct look.
- High contrast text (Gold on Dark Grey/Black).
- Grid and pack layouts for structured and responsive design.

### Colors (Apollon Scheme)
- Primary Background: Dark Grey (`#1E1E1E`)
- Secondary Background / Widgets: Black (`#000000`)
- Primary Foreground/Accent: Gold (`#FFD700`)
- Text: White (`#FFFFFF`) or Gold.
- Status indicators and dialogs utilize theme defaults or specific accents (e.g., danger for removal).

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.