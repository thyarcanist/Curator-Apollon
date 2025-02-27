import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledFrame
from typing import List
from models.library import MusicLibrary, Track
from services.spotify_service import SpotifyService
from services.analysis_service import AnalysisService
from tkinter import filedialog
from pathlib import Path
import tkinter.font as tkFont
from PIL import Image, ImageTk
import os

class MainWindow:
    def __init__(self, root, library: MusicLibrary, 
                 spotify_service: SpotifyService,
                 analysis_service: AnalysisService):
        self.root = root
        self.library = library
        self.spotify_service = spotify_service
        self.analysis_service = analysis_service
        self.current_playlist_url = None
        self.current_track = None  # Add this to track selected track
        
        # Load custom font
        font_path = Path(__file__).parent.parent / "appearance" / "fonts" / "CommitMono VariableFont.woff2"
        self.root.tk.call('font', 'create', 'CommitMono')
        self.root.tk.call('font', 'configure', 'CommitMono', '-family', str(font_path))
        
        # Set window icon (fixed)
        icon_path = Path(__file__).parent.parent / "appearance" / "img" / "laurel-circlet.png"
        if icon_path.exists():
            # Keep reference to prevent garbage collection
            self.icon_image = Image.open(icon_path)
            self.icon_photo = ImageTk.PhotoImage(self.icon_image)
            self.root.iconphoto(True, self.icon_photo)
        
        # Custom theme colors
        self.style = ttk.Style(theme="darkly")
        
        # Define Apollon color scheme
        COLORS = {
            'black': '#000000',
            'gold': '#FFD700',
            'dark_grey': '#1E1E1E',
            'light_grey': '#2D2D2D',
            'white': '#FFFFFF'
        }
        
        # Configure custom styles with new font
        self.style.configure("Treeview",
            background=COLORS['dark_grey'],
            foreground=COLORS['gold'],
            fieldbackground=COLORS['dark_grey'],
            rowheight=25,
            font='CommitMono 10'
        )
        
        self.style.configure("TButton",
            font='CommitMono 10',
            background=COLORS['black'],
            foreground=COLORS['gold']
        )
        
        self.style.configure("TLabel",
            background=COLORS['dark_grey'],
            foreground=COLORS['gold'],
            font='CommitMono 10'
        )
        
        self.style.configure("TFrame",
            background=COLORS['dark_grey']
        )
        
        self.style.configure("TNotebook",
            background=COLORS['dark_grey'],
            foreground=COLORS['gold']
        )
        
        self.style.configure("TNotebook.Tab",
            background=COLORS['black'],
            foreground=COLORS['gold'],
            padding=[10, 5]
        )
        
        # Add status bar at the bottom
        self.status_bar = ttk.Label(
            self.root,
            text="Ready",
            font='CommitMono 8',
            relief="sunken",
            padding=(5, 2)
        )
        self.status_bar.pack(side="bottom", fill="x")
        
        self._setup_ui()
        self.library.add_observer(self)
        
    def _setup_ui(self):
        # Create notebook for different views
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both')
        
        # Library View
        self.library_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.library_frame, text='Library')
        self._setup_library_view()
        
        # Playlist Info View
        self.playlist_info_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.playlist_info_frame, text='Playlist Info')
        self._setup_playlist_info_view()
        
        # Analysis View (merged)
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text='Analysis')
        self._setup_analysis_view()
        
        # Discovery View
        self.discovery_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.discovery_frame, text='Discovery')
        self._setup_discovery_view()
    
    def _setup_library_view(self):
        # Track list with modern styling
        self.track_list = ttk.Treeview(self.library_frame, 
                                      columns=('Title', 'Artist', 'BPM', 'Key'),
                                      show='headings',
                                      bootstyle="dark")
        
        # Configure columns
        for col in ('Title', 'Artist', 'BPM', 'Key'):
            self.track_list.heading(col, text=col)
            self.track_list.column(col, minwidth=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.library_frame, 
                                orient="vertical", 
                                command=self.track_list.yview)
        self.track_list.configure(yscrollcommand=scrollbar.set)
        
        # Pack with modern spacing
        self.track_list.pack(expand=True, fill='both', padx=10, pady=5, side='left')
        scrollbar.pack(fill='y', pady=5, side='right')
        
        # Control buttons in a modern layout
        controls = ttk.Frame(self.library_frame)
        controls.pack(fill='x', pady=10, padx=10)
        
        ttk.Button(controls, text='Add Track', 
                  bootstyle="primary",
                  command=self._add_track_dialog).pack(side='left', padx=5)
        ttk.Button(controls, text='Import Playlist', 
                  bootstyle="primary",
                  command=self._import_playlist_dialog).pack(side='left', padx=5)
        ttk.Button(controls, text='Remove Selected', 
                  bootstyle="danger",
                  command=self._remove_selected).pack(side='left', padx=5)
        ttk.Button(controls, text='Remove All', 
                  bootstyle="danger",
                  command=self._remove_all).pack(side='left', padx=5)
        
        # Export button
        self.export_button = ttk.Button(
            controls,
            text="Export Playlist",
            command=self.export_playlist,
            bootstyle="secondary"
        )
        self.export_button.pack(side="left", padx=5)
        
        # Add track selection binding
        self.track_list.bind('<<TreeviewSelect>>', self._on_track_select)
    
    def _setup_playlist_info_view(self):
        """Setup the playlist information view"""
        # Create main sections
        musical_stats = ttk.LabelFrame(self.playlist_info_frame, text='Musical Statistics')
        musical_stats.pack(fill='x', padx=10, pady=5)
        
        literary_stats = ttk.LabelFrame(self.playlist_info_frame, text='Literary Analysis')
        literary_stats.pack(fill='x', padx=10, pady=5)
        
        # Musical Statistics Section
        musical_grid = ttk.Frame(musical_stats)
        musical_grid.pack(padx=10, pady=5)
        
        musical_labels = [
            ('Average BPM:', '0'),
            ('Average Key:', 'N/A'),
            ('Max BPM:', '0'),
            ('Min BPM:', '0'),
            ('Most Common Key:', 'N/A'),
            ('Key Distribution:', 'N/A'),
            ('Time Signatures:', 'N/A'),
            ('Common Time Songs:', '0'),
            ('Odd Time Songs:', '0')
        ]
        
        self.musical_values = {}
        for i, (label, default) in enumerate(musical_labels):
            ttk.Label(musical_grid, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=2)
            value_label = ttk.Label(musical_grid, text=default)
            value_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
            self.musical_values[label] = value_label
        
        # Literary Statistics Section
        literary_grid = ttk.Frame(literary_stats)
        literary_grid.pack(padx=10, pady=5)
        
        literary_labels = [
            ('Most Common Artist:', 'N/A'),
            ('Most Used Word (count):', 'N/A'),
            ('Least Used Word (count):', 'N/A'),
            ('Top Characters:', 'N/A'),
            ('Special Characters:', 'N/A'),
            ('Numbers Used:', 'N/A'),
            ('Average Title Length:', '0'),
            ('Unique Artists:', '0'),
            ('Repeated Words:', 'N/A'),
            ('Title Pattern:', 'N/A')
        ]
        
        self.literary_values = {}
        for i, (label, default) in enumerate(literary_labels):
            ttk.Label(literary_grid, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=2)
            value_label = ttk.Label(literary_grid, text=default)
            value_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
            self.literary_values[label] = value_label
        
        # Refresh button
        ttk.Button(
            self.playlist_info_frame,
            text="Refresh Statistics",
            command=self._update_playlist_stats,
            bootstyle="secondary"
        ).pack(pady=10)

    def _setup_analysis_view(self):
        """Setup the analysis view with playlist and track statistics"""
        # Create scrollable frame for all content
        self.analysis_scroll = ScrolledFrame(self.analysis_frame)
        self.analysis_scroll.pack(expand=True, fill='both', padx=5, pady=5)
        
        content = self.analysis_scroll.container
        
        # Current Track Analysis Section
        self.current_track_frame = ttk.LabelFrame(content, text='Current Track Analysis')
        self.current_track_frame.pack(fill='x', padx=10, pady=5)
        
        track_grid = ttk.Frame(self.current_track_frame)
        track_grid.pack(padx=10, pady=5)
        
        track_labels = [
            ('Title:', 'N/A'),
            ('Artist:', 'N/A'),
            ('Album:', 'N/A'),
            ('BPM:', 'N/A'),
            ('Key:', 'N/A'),
            ('Time Signature:', 'N/A'),
            ('Energy Level:', 'N/A'),
            ('Camelot Position:', 'N/A')
        ]
        
        self.track_values = {}
        for i, (label, default) in enumerate(track_labels):
            ttk.Label(track_grid, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=2)
            value_label = ttk.Label(track_grid, text=default)
            value_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
            self.track_values[label] = value_label
        
        # Playlist Analysis Section
        playlist_stats = ttk.LabelFrame(content, text='Playlist Analysis')
        playlist_stats.pack(fill='x', padx=10, pady=5)
        
        # Musical Statistics Section
        musical_stats = ttk.LabelFrame(playlist_stats, text='Musical Statistics')
        musical_stats.pack(fill='x', padx=10, pady=5)
        
        musical_labels = [
            ('Average BPM:', '0'),
            ('Average Key:', 'N/A'),
            ('Max BPM:', '0'),
            ('Min BPM:', '0'),
            ('Most Common Key:', 'N/A'),
            ('Key Distribution:', 'N/A'),
            ('Time Signatures:', 'N/A'),
            ('Common Time Songs:', '0'),
            ('Odd Time Songs:', '0')
        ]
        
        self.musical_values = {}
        for i, (label, default) in enumerate(musical_labels):
            ttk.Label(musical_stats, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=2)
            value_label = ttk.Label(musical_stats, text=default)
            value_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
            self.musical_values[label] = value_label
        
        # Literary Statistics Section
        literary_stats = ttk.LabelFrame(playlist_stats, text='Literary Analysis')
        literary_stats.pack(fill='x', padx=10, pady=5)
        
        literary_labels = [
            ('Most Common Artist:', 'N/A'),
            ('Most Used Word (count):', 'N/A'),
            ('Least Used Word (count):', 'N/A'),
            ('Top Characters:', 'N/A'),
            ('Special Characters:', 'N/A'),
            ('Numbers Used:', 'N/A'),
            ('Average Title Length:', '0'),
            ('Unique Artists:', '0'),
            ('Repeated Words:', 'N/A'),
            ('Title Pattern:', 'N/A')
        ]
        
        self.literary_values = {}
        for i, (label, default) in enumerate(literary_labels):
            ttk.Label(literary_stats, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=2)
            value_label = ttk.Label(literary_stats, text=default)
            value_label.grid(row=i, column=1, sticky='w', padx=5, pady=2)
            self.literary_values[label] = value_label
        
        # Refresh button
        ttk.Button(
            playlist_stats,
            text="Refresh Statistics",
            command=self._update_playlist_stats,
            bootstyle="secondary"
        ).pack(pady=10)

    def _setup_discovery_view(self):
        # Entropy slider
        ttk.Label(self.discovery_frame, text='Entropy Level:').pack(pady=5)
        self.entropy_slider = ttk.Scale(self.discovery_frame, from_=0, to=1, 
                                      orient='horizontal')
        self.entropy_slider.pack(fill='x', padx=10)
        
        # Recommendations list
        self.recommendations_list = ttk.Treeview(self.discovery_frame,
                                               columns=('Title', 'Artist', 'Match'),
                                               show='headings')
        self.recommendations_list.pack(expand=True, fill='both', pady=5)
    
    def update(self):
        """Update UI when library changes"""
        self._refresh_track_list()
        self._update_playlist_stats()
    
    def _refresh_track_list(self):
        self.track_list.delete(*self.track_list.get_children())
        for track in self.library.get_all_tracks():
            self.track_list.insert('', 'end', values=(
                track.title,
                track.artist,
                track.bpm,
                track.key
            )) 

    def _add_track_dialog(self):
        """Open dialog for adding a track"""
        dialog = ttk.Toplevel(self.root)
        dialog.title("Add Track")
        dialog.geometry("400x400")
        
        def handle_spotify_import():
            try:
                url = spotify_url_entry.get()
                if url:
                    # Show authentication instructions
                    messagebox.showinfo(
                        "Spotify Authentication",
                        "You will be redirected to Spotify to authenticate.\n\n"
                        "After authorizing, you will be redirected to apollon.occybyte.com.\n\n"
                        "Copy the FULL URL from your browser and paste it in the next dialog."
                    )
                    track = self.spotify_service.get_track_info(url)
                    self.library.add_track(track)
                    dialog.destroy()
                    messagebox.showinfo("Success", "Track imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        # Spotify URL input
        ttk.Label(dialog, text="Spotify Track URL (optional):").pack(pady=5)
        spotify_url_entry = ttk.Entry(dialog)
        spotify_url_entry.pack(fill='x', padx=20)
        
        ttk.Button(dialog, text="Import from Spotify", 
                  command=handle_spotify_import).pack(pady=5)
        
        ttk.Label(dialog, text="- OR -").pack(pady=10)
        
        # Manual entry section
        manual_frame = ttk.LabelFrame(dialog, text="Manual Entry")
        manual_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(manual_frame, text="Title:").pack(pady=5)
        title_entry = ttk.Entry(manual_frame)
        title_entry.pack(fill='x', padx=20)
        
        ttk.Label(manual_frame, text="Artist:").pack(pady=5)
        artist_entry = ttk.Entry(manual_frame)
        artist_entry.pack(fill='x', padx=20)
        
        ttk.Label(manual_frame, text="BPM:").pack(pady=5)
        bpm_entry = ttk.Entry(manual_frame)
        bpm_entry.pack(fill='x', padx=20)
        
        ttk.Label(manual_frame, text="Key:").pack(pady=5)
        key_entry = ttk.Entry(manual_frame)
        key_entry.pack(fill='x', padx=20)
        
        def save_manual_track():
            try:
                track = Track(
                    id=f"manual_{len(self.library.tracks)}",
                    title=title_entry.get(),
                    artist=artist_entry.get(),
                    bpm=float(bpm_entry.get()),
                    key=key_entry.get(),
                    camelot_position="",
                    energy_level=0.5
                )
                self.library.add_track(track)
                dialog.destroy()
                messagebox.showinfo("Success", "Track added successfully!")
            except ValueError as e:
                messagebox.showerror("Error", "Please check your inputs")
        
        ttk.Button(manual_frame, text="Save Manual Entry", 
                  command=save_manual_track).pack(pady=20)
    
    def _import_playlist_dialog(self):
        """Open dialog for importing a Spotify playlist"""
        dialog = ttk.Toplevel(self.root)
        dialog.title("Import Spotify Playlist")
        dialog.geometry("500x200")
        
        # Status label
        status_label = ttk.Label(dialog, text="Checking authentication status...")
        status_label.pack(pady=5)
        
        def check_auth():
            status_label.config(text="Testing authentication...")
            dialog.update()
            
            if self.spotify_service.debug_auth():
                status_label.config(text="Authentication successful!")
                Messagebox.show_info(
                    message="Successfully authenticated with Spotify!",
                    title="Authentication Success"
                )
            else:
                status_label.config(text="Authentication failed - check console for details")
                Messagebox.show_error(
                    message="Authentication failed.\nPlease check the console for error details.",
                    title="Authentication Error"
                )
        
        ttk.Button(dialog, text="Check Auth", 
                  bootstyle="info",
                  command=check_auth).pack(pady=5)
        
        ttk.Label(dialog, text="Enter Spotify Playlist URL:").pack(pady=5)
        url_entry = ttk.Entry(dialog, width=50)
        url_entry.pack(fill='x', padx=20)
        
        def handle_import():
            try:
                url = url_entry.get()
                if not url:
                    Messagebox.show_error(
                        message="Please enter a playlist URL",
                        title="Error"
                    )
                    return
                
                self.set_status("Importing playlist...")
                self.current_playlist_url = url
                tracks = self.spotify_service.import_playlist(url)
                
                if tracks:
                    for track in tracks:
                        self.library.add_track(track)
                    dialog.destroy()
                    self.set_status(f"Successfully imported {len(tracks)} tracks")
                    Messagebox.show_info(
                        message=f"Successfully imported {len(tracks)} tracks",
                        title="Success"
                    )
                else:
                    self.set_status("Import failed - no tracks found")
                    Messagebox.show_error(
                        message="No tracks were imported",
                        title="Error"
                    )
                    
            except Exception as e:
                self.set_status(f"Import error: {str(e)}")
                Messagebox.show_error(
                    message=str(e),
                    title="Error"
                )
        
        ttk.Button(dialog, text="Import", 
                  bootstyle="primary-outline",
                  command=handle_import).pack(pady=20)
    
    def _remove_selected(self):
        """Remove selected tracks from the library"""
        selected_items = self.track_list.selection()
        for item_id in selected_items:
            values = self.track_list.item(item_id)['values']
            # Find and remove the track
            for track in self.library.get_all_tracks():
                if track.title == values[0] and track.artist == values[1]:
                    self.library.remove_track(track.id)
                    break 

    def _remove_all(self):
        """Remove all tracks from the library"""
        if len(self.library.get_all_tracks()) == 0:
            Messagebox.show_info(
                "No Tracks",
                "Library is already empty."
            )
            return
            
        # Ask for confirmation
        confirm = Messagebox.show_question(
            "Remove All Tracks",
            "Are you sure you want to remove all tracks from the library?",
            buttons=['Yes:danger', 'No:secondary']
        )
        
        if confirm == 'Yes':
            self.set_status("Removing all tracks...")
            # Get all track IDs and remove them
            for track in self.library.get_all_tracks():
                self.library.remove_track(track.id)
            
            # Reset current playlist URL since we cleared everything
            self.current_playlist_url = None
            
            self.set_status("All tracks removed")
            Messagebox.show_info(
                "Success",
                "All tracks have been removed from the library."
            )

    def export_playlist(self):
        """Handle playlist export"""
        if not self.current_playlist_url:
            Messagebox.show_warning(
                "No Playlist",
                "Please import a playlist first before exporting."
            )
            return
            
        self.set_status("Selecting export location...")
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="playlist_export.txt",
            title="Export Playlist"
        )
        
        if file_path:
            self.set_status("Exporting playlist...")
            if self.spotify_service.export_playlist_to_txt(self.current_playlist_url, file_path):
                self.set_status(f"Playlist exported to {file_path}")
                Messagebox.show_info(
                    "Export Successful",
                    f"Playlist has been exported to:\n{file_path}"
                )
            else:
                self.set_status("Export failed")
                Messagebox.show_error(
                    "Export Failed",
                    "Failed to export playlist. Please check the logs for details."
                )

    def set_status(self, message: str):
        """Update status bar message"""
        self.status_bar.config(text=message)
        self.root.update()

    def _update_playlist_stats(self):
        """Update all playlist statistics"""
        tracks = self.library.get_all_tracks()
        if not tracks:
            self._reset_stats()
            return
        
        # Calculate Musical Stats
        bpms = [t.bpm for t in tracks if t.bpm > 0]
        if bpms:
            avg_bpm = sum(bpms) / len(bpms)
            max_bpm = max(bpms)
            min_bpm = min(bpms)
            self.musical_values['Average BPM:'].config(text=f"{avg_bpm:.1f}")
            self.musical_values['Max BPM:'].config(text=f"{max_bpm:.1f}")
            self.musical_values['Min BPM:'].config(text=f"{min_bpm:.1f}")
        
        # Calculate Literary Stats
        artists = [t.artist for t in tracks]
        titles = [t.title for t in tracks]
        
        # Artist Analysis
        artist_counts = {}
        for artist in artists:
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
        
        if artist_counts:
            most_common_artist = max(artist_counts.items(), key=lambda x: x[1])
            self.literary_values['Most Common Artist:'].config(
                text=f"{most_common_artist[0]} ({most_common_artist[1]} tracks)"
            )
            self.literary_values['Unique Artists:'].config(text=str(len(set(artists))))
        
        # Character Analysis
        all_chars = ''.join(titles).lower()
        char_counts = {}
        special_chars = set()
        numbers = set()
        
        for char in all_chars:
            if char.isalnum():
                char_counts[char] = char_counts.get(char, 0) + 1
                if char.isnumeric():
                    numbers.add(char)
            elif not char.isspace():
                special_chars.add(char)
        
        # Sort characters by frequency
        top_chars = sorted(
            [(k, v) for k, v in char_counts.items() if k.isalpha()],
            key=lambda x: x[1],
            reverse=True
        )[:8]  # Top 8 characters
        
        self.literary_values['Top Characters:'].config(
            text=f"[{', '.join(f'{c[0]}({c[1]})' for c in top_chars)}]"
        )
        
        if special_chars:
            self.literary_values['Special Characters:'].config(
                text=f"[{', '.join(sorted(special_chars))}]"
            )
        
        if numbers:
            self.literary_values['Numbers Used:'].config(
                text=f"[{', '.join(sorted(numbers))}]"
            )
        
        # Enhanced Word Analysis
        words = []
        word_in_tracks = {}  # Count how many tracks contain each word
        
        # Words/symbols to ignore unless part of a known band/title
        ignore_words = {'the', 'a', 'an', 'and', 'or', 'but', 'nor', 'for', 'yet', 'so'}
        ignore_chars = {'-', '&', '+', 'x', 'vs', 'feat.', 'ft.', 'prod.'}
        
        # Known special cases (band names, common title patterns that should be preserved)
        special_cases = {
            'a$ap': 'asap',  # A$AP Rocky
            't-ara': 't-ara',  # T-ara
            'g-dragon': 'g-dragon',  # G-Dragon
            'x-japan': 'x-japan',  # X Japan
            'crosses': '†††',  # Crosses (†††)
            'day6': 'day6',  # DAY6
            'txt': 'txt',  # TXT (Tomorrow X Together)
        }
        
        def clean_word(word: str) -> str:
            """Clean a word while preserving special cases"""
            word = word.lower()
            
            # Check for special cases first
            for case, preserve in special_cases.items():
                if case in word:
                    return preserve
            
            # Remove common symbols if not part of special cases
            if word not in ignore_chars:
                for char in '()[]{}!?.,;:\'\"':
                    word = word.replace(char, '')
                
                # Remove standalone symbols
                if word in ignore_chars:
                    return ''
                
                # Remove common words unless they're part of a longer phrase
                if word in ignore_words and len(word) <= 3:
                    return ''
            
            return word
        
        for track in tracks:
            # Split on spaces and clean each word
            title_words = [clean_word(w) for w in track.title.split()]
            # Filter out empty strings and single characters
            title_words = [w for w in title_words if w and len(w) > 1]
            
            # Add to global word list
            words.extend(title_words)
            
            # Count unique words per track
            seen_words = set(title_words)
            for word in seen_words:
                word_in_tracks[word] = word_in_tracks.get(word, 0) + 1
        
        if words:
            # Filter out very common words for the "most used" statistic
            filtered_words = {k: v for k, v in word_in_tracks.items() 
                            if k not in ignore_words and len(k) > 1}
            
            if filtered_words:
                most_used = max(filtered_words.items(), key=lambda x: x[1])
                least_used = min(filtered_words.items(), key=lambda x: x[1])
                
                self.literary_values['Most Used Word (count):'].config(
                    text=f"{most_used[0]} (in {most_used[1]} tracks)"
                )
                self.literary_values['Least Used Word (count):'].config(
                    text=f"{least_used[0]} (in {least_used[1]} tracks)"
                )
                
                # Find meaningful repeated words
                repeated = [word for word, count in filtered_words.items() 
                          if count > 1 and word not in ignore_chars]
                if repeated:
                    self.literary_values['Repeated Words:'].config(
                        text=f"{', '.join(sorted(repeated)[:5])}..."
                    )
            
            # Analyze title patterns
            patterns = []
            if any('feat.' in t.lower() for t in titles):
                patterns.append('feat.')
            if any('remix' in t.lower() for t in titles):
                patterns.append('remix')
            if any('ft.' in t.lower() for t in titles):
                patterns.append('ft.')
            if any('prod.' in t.lower() for t in titles):
                patterns.append('prod.')
            
            if patterns:
                self.literary_values['Title Pattern:'].config(
                    text=f"Common: {', '.join(patterns)}"
                )
            
            # Average title length
            avg_length = sum(len(title) for title in titles) / len(titles)
            self.literary_values['Average Title Length:'].config(
                text=f"{avg_length:.1f} chars"
            )
        
        # Time Signature Analysis
        time_sigs = {}
        common_time = 0  # 4/4
        odd_time = 0     # anything not 4/4
        
        for track in tracks:
            sig = track.time_signature
            time_sigs[sig] = time_sigs.get(sig, 0) + 1
            
            if sig == "4/4":
                common_time += 1
            else:
                odd_time += 1
        
        # Format time signature distribution
        if time_sigs:
            sig_display = []
            for sig, count in sorted(time_sigs.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(tracks)) * 100
                sig_display.append(f"{sig}({count}, {percentage:.1f}%)")
            
            self.musical_values['Time Signatures:'].config(
                text=f"{', '.join(sig_display)}"
            )
            self.musical_values['Common Time Songs:'].config(
                text=f"{common_time} ({(common_time/len(tracks))*100:.1f}%)"
            )
            self.musical_values['Odd Time Songs:'].config(
                text=f"{odd_time} ({(odd_time/len(tracks))*100:.1f}%)"
            )
        
        self.set_status("Statistics updated")

    def _reset_stats(self):
        """Reset all statistics to default values"""
        for label in self.musical_values.values():
            label.config(text="N/A")
        for label in self.literary_values.values():
            label.config(text="N/A")
        self.set_status("Statistics reset - no tracks in library")

    def _on_track_select(self, event):
        """Handle track selection"""
        selected_items = self.track_list.selection()
        if selected_items:
            item_id = selected_items[0]  # Get first selected item
            values = self.track_list.item(item_id)['values']
            
            # Find the track in library
            for track in self.library.get_all_tracks():
                if track.title == values[0] and track.artist == values[1]:
                    self.current_track = track
                    self._update_current_track_analysis()
                    break
        else:
            self.current_track = None
            self._update_current_track_analysis()

    def _update_current_track_analysis(self):
        """Update the current track analysis display"""
        if self.current_track:
            self.track_values['Title:'].config(text=self.current_track.title)
            self.track_values['Artist:'].config(text=self.current_track.artist)
            self.track_values['Album:'].config(text=self.current_track.album or 'N/A')
            self.track_values['BPM:'].config(text=str(self.current_track.bpm or 'N/A'))
            self.track_values['Key:'].config(text=self.current_track.key or 'N/A')
            self.track_values['Time Signature:'].config(text=self.current_track.time_signature)
            self.track_values['Energy Level:'].config(text=str(self.current_track.energy_level or 'N/A'))
            self.track_values['Camelot Position:'].config(text=str(self.current_track.camelot_position or 'N/A'))
        else:
            # Reset all values if no track is selected
            for label in self.track_values.values():
                label.config(text='N/A') 