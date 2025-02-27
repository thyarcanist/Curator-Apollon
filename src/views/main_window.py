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
import requests
import io

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
        
        # Add bold labelframe style
        self.style.configure(
            "Bold.TLabelframe.Label",
            font=('CommitMono', 10, 'bold'),
            foreground=COLORS['gold']
        )
        
        self.style.configure(
            "Bold.TLabelframe",
            borderwidth=2,
            relief="solid"
        )

        # Configure dialog geometry
        self.root.option_add('*Dialog.geometry', 'center')  # Center dialogs
        self.root.option_add('*Dialog.minsize', '300x100')  # Minimum size
        
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
        
        # Analysis View
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
    
    def _setup_analysis_view(self):
        """Setup the analysis view with playlist and track statistics"""
        self.analysis_scroll = ScrolledFrame(self.analysis_frame)
        self.analysis_scroll.pack(expand=True, fill='both', padx=5, pady=5)
        
        content = self.analysis_scroll.container
        
        # Current Track Analysis Section
        self.current_track_frame = ttk.LabelFrame(content, text='Current Track Analysis')
        self.current_track_frame.pack(fill='x', padx=10, pady=5)
        
        # Album art frame
        self.album_art_frame = ttk.Frame(self.current_track_frame)
        self.album_art_frame.pack(pady=10)
        
        # Album art label (will hold the image)
        self.album_art_label = ttk.Label(self.album_art_frame)
        self.album_art_label.pack()
        
        # Track details grid
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
        
        # Navigation buttons at the bottom
        nav_frame = ttk.Frame(self.current_track_frame)
        nav_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        self.prev_button = ttk.Button(
            nav_frame,
            text="← Previous",
            command=self._show_previous_track,
            bootstyle="secondary"
        )
        self.prev_button.pack(side='left', padx=5)
        
        self.next_button = ttk.Button(
            nav_frame,
            text="Next →",
            command=self._show_next_track,
            bootstyle="secondary"
        )
        self.next_button.pack(side='right', padx=5)
        
        # Playlist Analysis Section (with larger font and padding)
        playlist_stats = ttk.LabelFrame(
            content, 
            text='Playlist Analysis',
            style='Bold.TLabelframe'
        )
        playlist_stats.pack(fill='x', padx=10, pady=15)  # Added more padding
        
        # Musical Statistics Section
        musical_stats = ttk.LabelFrame(
            playlist_stats, 
            text='Musical Statistics',
            style='Bold.TLabelframe'
        )
        musical_stats.pack(fill='x', padx=10, pady=10)
        
        musical_labels = [
            ('Average BPM:', 'N/A'),
            ('BPM Range:', 'N/A'),
            ('Tracks with BPM:', 'N/A'),
            ('Common Keys:', 'N/A'),
            ('Tracks with Key:', 'N/A'),
            ('Average Energy:', 'N/A'),
            ('Tracks with Energy:', 'N/A'),
            ('Common Camelot:', 'N/A'),
            ('Tracks with Camelot:', 'N/A'),
            ('Time Signatures:', 'N/A'),
            ('Tracks with Time Sig:', 'N/A')
        ]
        
        self.musical_values = {}
        for label, default in musical_labels:
            ttk.Label(musical_stats, text=label).pack(anchor='w', padx=10, pady=2)
            value_label = ttk.Label(musical_stats, text=default)
            value_label.pack(anchor='w', padx=20, pady=2)
            self.musical_values[label] = value_label
        
        # Literary Statistics Section (with padding)
        literary_stats = ttk.LabelFrame(
            playlist_stats, 
            text='Literary Analysis',
            style='Bold.TLabelframe'
        )
        literary_stats.pack(fill='x', padx=10, pady=(20, 10))  # Added more top padding
        
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
        self.refresh_button = ttk.Button(
            playlist_stats,
            text="Refresh Statistics",
            command=self._update_analysis,
            bootstyle="secondary"
        )
        self.refresh_button.pack(pady=10)

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
        self._update_track_list()
        self._update_playlist_stats()
    
    def _update_track_list(self):
        """Update the track list display with error handling"""
        try:
            # Clear existing items
            for item in self.track_list.get_children():
                self.track_list.delete(item)
            
            # Add tracks to display
            for track in self.library.get_all_tracks():
                try:
                    self.track_list.insert(
                        '', 'end',
                        values=(
                            track.title,
                            track.artist,
                            f"{track.bpm:.0f}" if track.bpm and track.bpm > 0 else "N/A",
                            track.key if track.key != "Unknown" else "N/A"
                        )
                    )
                except Exception as e:
                    print(f"Error adding track to display: {e}")
            
            # Update analysis
            try:
                self._update_analysis()
            except Exception as e:
                print(f"Error updating analysis: {e}")
                self.set_status("Error updating analysis display")
            
        except Exception as e:
            print(f"Error updating track list: {e}")
            self.set_status("Error updating display")

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
                self._import_playlist()
                
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
            self.musical_values['BPM Range:'].config(text=f"{min_bpm:.1f} - {max_bpm:.1f}")
            self.musical_values['Tracks with BPM:'].config(
                text=f"{len(bpms)}/{len(tracks)} ({(len(bpms)/len(tracks))*100:.1f}%)"
            )
        else:
            self.musical_values['Average BPM:'].config(text="N/A")
            self.musical_values['BPM Range:'].config(text="N/A")
            self.musical_values['Tracks with BPM:'].config(text="0/0 (0%)")
        
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
            self.musical_values['Tracks with Time Sig:'].config(
                text=f"{sum(time_sigs.values())}/{len(tracks)} ({(sum(time_sigs.values())/len(tracks))*100:.1f}%)"
            )
        else:
            self.musical_values['Time Signatures:'].config(text="N/A")
            self.musical_values['Tracks with Time Sig:'].config(text="0/0 (0%)") 

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

    def _show_previous_track(self):
        """Show the previous track in the library"""
        if not self.current_track:
            return
            
        tracks = self.library.get_all_tracks()
        try:
            current_index = tracks.index(self.current_track)
            if current_index > 0:
                self.current_track = tracks[current_index - 1]
                self._update_current_track_analysis()
        except ValueError:
            pass

    def _show_next_track(self):
        """Show the next track in the library"""
        if not self.current_track:
            return
            
        tracks = self.library.get_all_tracks()
        try:
            current_index = tracks.index(self.current_track)
            if current_index < len(tracks) - 1:
                self.current_track = tracks[current_index + 1]
                self._update_current_track_analysis()
        except ValueError:
            pass

    def _update_current_track_analysis(self):
        """Update the current track analysis display"""
        if self.current_track:
            # Update album art
            if self.current_track.album_art_url:
                try:
                    # Download and display album art
                    response = requests.get(self.current_track.album_art_url, timeout=5)
                    if response.status_code == 200:
                        img_data = response.content
                        img = Image.open(io.BytesIO(img_data))
                        
                        # Increase size to 300x300 (was 200x200)
                        img = img.resize((300, 300), Image.Resampling.LANCZOS)
                        
                        # Convert to RGBA if needed
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        
                        # Keep reference to prevent garbage collection
                        self.current_album_art = ImageTk.PhotoImage(img)
                        self.album_art_label.config(image=self.current_album_art)
                    else:
                        print(f"Failed to load album art: HTTP {response.status_code}")
                        self.album_art_label.config(image='')
                except Exception as e:
                    print(f"Error loading album art: {e}")
                    self.album_art_label.config(image='')
            else:
                self.album_art_label.config(image='')
            
            # Update track details
            self.track_values['Title:'].config(text=self.current_track.title)
            self.track_values['Artist:'].config(text=self.current_track.artist)
            self.track_values['Album:'].config(text=self.current_track.album or 'N/A')
            self.track_values['BPM:'].config(text=str(self.current_track.bpm or 'N/A'))
            self.track_values['Key:'].config(text=self.current_track.key or 'N/A')
            self.track_values['Time Signature:'].config(text=self.current_track.time_signature)
            self.track_values['Energy Level:'].config(text=str(self.current_track.energy_level or 'N/A'))
            self.track_values['Camelot Position:'].config(text=str(self.current_track.camelot_position or 'N/A'))
            
            # Update navigation buttons
            tracks = self.library.get_all_tracks()
            try:
                current_index = tracks.index(self.current_track)
                self.prev_button.config(state='normal' if current_index > 0 else 'disabled')
                self.next_button.config(state='normal' if current_index < len(tracks) - 1 else 'disabled')
            except ValueError:
                self.prev_button.config(state='disabled')
                self.next_button.config(state='disabled')
        else:
            # Reset everything if no track is selected
            self.album_art_label.config(image='')
            for label in self.track_values.values():
                label.config(text='N/A')
            self.prev_button.config(state='disabled')
            self.next_button.config(state='disabled')

    def _import_playlist(self):
        """Import a playlist from Spotify URL"""
        url = self.current_playlist_url
        if not url:
            Messagebox.show_error(
                "Please enter a Spotify playlist URL",
                "Import Error"
            )
            return
        
        def on_import_complete(tracks):
            self.library.add_tracks(tracks)
            self._update_analysis()
            self.status_bar.config(text=f"Imported {len(tracks)} tracks")
            
        # Start import in background
        self.spotify_service.import_playlist_async(url, callback=on_import_complete)
        self.status_bar.config(text="Importing playlist...") 

    def _update_analysis(self):
        """Update all analysis displays"""
        try:
            tracks = self.library.get_all_tracks()
            if tracks:
                # Update musical analysis
                self._update_musical_analysis(tracks)
                # Update literary analysis
                self._update_literary_analysis(tracks)
                self.set_status(f"Analysis updated for {len(tracks)} tracks")
            else:
                self._reset_stats()
        except Exception as e:
            print(f"Error updating analysis: {e}")
            self.set_status("Error updating analysis")

    def _update_musical_analysis(self, tracks: List[Track]):
        """Update musical analysis with handling for missing features"""
        if not tracks:
            return
            
        # BPM Analysis
        valid_bpms = [t.bpm for t in tracks if t.bpm and t.bpm > 0]
        if valid_bpms:
            avg_bpm = sum(valid_bpms) / len(valid_bpms)
            min_bpm = min(valid_bpms)
            max_bpm = max(valid_bpms)
            
            self.musical_values['Average BPM:'].config(text=f"{avg_bpm:.1f}")
            self.musical_values['BPM Range:'].config(text=f"{min_bpm:.1f} - {max_bpm:.1f}")
            self.musical_values['Tracks with BPM:'].config(
                text=f"{len(valid_bpms)}/{len(tracks)} ({(len(valid_bpms)/len(tracks))*100:.1f}%)"
            )
        else:
            self.musical_values['Average BPM:'].config(text="N/A")
            self.musical_values['BPM Range:'].config(text="N/A")
            self.musical_values['Tracks with BPM:'].config(text="0/0 (0%)")
        
        # Key Analysis
        valid_keys = [t.key for t in tracks if t.key and t.key != "Unknown"]
        if valid_keys:
            key_counts = {}
            for key in valid_keys:
                key_counts[key] = key_counts.get(key, 0) + 1
            
            # Most common keys
            common_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            key_display = ", ".join(f"{k}({v})" for k, v in common_keys)
            
            self.musical_values['Common Keys:'].config(text=key_display)
            self.musical_values['Tracks with Key:'].config(
                text=f"{len(valid_keys)}/{len(tracks)} ({(len(valid_keys)/len(tracks))*100:.1f}%)"
            )
        else:
            self.musical_values['Common Keys:'].config(text="N/A")
            self.musical_values['Tracks with Key:'].config(text="0/0 (0%)")
        
        # Energy Analysis
        valid_energy = [t.energy_level for t in tracks if t.energy_level is not None and t.energy_level > 0]
        if valid_energy:
            avg_energy = sum(valid_energy) / len(valid_energy)
            self.musical_values['Average Energy:'].config(text=f"{avg_energy:.2f}")
            self.musical_values['Tracks with Energy:'].config(
                text=f"{len(valid_energy)}/{len(tracks)} ({(len(valid_energy)/len(tracks))*100:.1f}%)"
            )
        else:
            self.musical_values['Average Energy:'].config(text="N/A")
            self.musical_values['Tracks with Energy:'].config(text="0/0 (0%)")
        
        # Camelot Analysis
        valid_camelot = [t.camelot_position for t in tracks if t.camelot_position and t.camelot_position != "Unknown"]
        if valid_camelot:
            camelot_counts = {}
            for pos in valid_camelot:
                camelot_counts[pos] = camelot_counts.get(pos, 0) + 1
            
            # Most common positions
            common_pos = sorted(camelot_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            pos_display = ", ".join(f"{p}({v})" for p, v in common_pos)
            
            self.musical_values['Common Camelot:'].config(text=pos_display)
            self.musical_values['Tracks with Camelot:'].config(
                text=f"{len(valid_camelot)}/{len(tracks)} ({(len(valid_camelot)/len(tracks))*100:.1f}%)"
            )
        else:
            self.musical_values['Common Camelot:'].config(text="N/A")
            self.musical_values['Tracks with Camelot:'].config(text="0/0 (0%)")
        
        # Time Signature Analysis
        time_sigs = {}
        common_time = 0
        odd_time = 0
        
        for track in tracks:
            sig = track.time_signature
            if sig != "Unknown":
                time_sigs[sig] = time_sigs.get(sig, 0) + 1
                if sig == "4/4":
                    common_time += 1
                else:
                    odd_time += 1
        
        if time_sigs:
            sig_display = []
            for sig, count in sorted(time_sigs.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(tracks)) * 100
                sig_display.append(f"{sig}({count}, {percentage:.1f}%)")
            
            self.musical_values['Time Signatures:'].config(text=", ".join(sig_display))
            total_analyzed = sum(time_sigs.values())
            self.musical_values['Tracks with Time Sig:'].config(
                text=f"{total_analyzed}/{len(tracks)} ({(total_analyzed/len(tracks))*100:.1f}%)"
            )
        else:
            self.musical_values['Time Signatures:'].config(text="N/A")
            self.musical_values['Tracks with Time Sig:'].config(text="0/0 (0%)") 