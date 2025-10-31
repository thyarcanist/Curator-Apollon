# Curator Apollon: Main Window UI and Application View Logic
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

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledFrame
from typing import List, Optional
from models.library import MusicLibrary, Track
from services.spotify_service import SpotifyService
from services.analysis_service import AnalysisService
from services.entropy_service import EntropyService
from models.profile import ProfileManager
from services.musicbrainz_service import MusicBrainzService
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
                 analysis_service: AnalysisService,
                 entropy_service: Optional[EntropyService],
                 profile_manager: ProfileManager,
                 musicbrainz_service: MusicBrainzService):
        self.root = root
        
        # Make window scale with screen
        self.root.state('zoomed')  # Windows fullscreen
        
        # Configure grid weights for proper scaling
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.library = library
        self.spotify_service = spotify_service
        self.analysis_service = analysis_service
        self.entropy_service = entropy_service
        self.profile_manager = profile_manager
        self.musicbrainz_service = musicbrainz_service
        self.current_playlist_url = None
        self.current_track = None  # Add this to track selected track
        # Preference flags
        self.liked_var = ttk.BooleanVar(value=False)
        self.loved_var = ttk.BooleanVar(value=False)
        self.mood_dep_var = ttk.BooleanVar(value=False)
        
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
        # Ensure UI reflects any tracks loaded at app start
        try:
            self.update()
        except Exception:
            pass
        self.set_status("Curator Apollon initialized.")
        if self.entropy_service is None:
            self.set_status("Warning: EntropyService (OccyByte API) not available. Quantum recommendations disabled.")
        
    def _setup_ui(self):
        # Create notebook for different views
        # Top bar with profile selection
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill='x')

        ttk.Label(top_bar, text='Profile:').pack(side='left', padx=(8, 4))
        self.profile_var = ttk.StringVar(value=self.profile_manager.get_current_profile())
        self.profile_combo = ttk.Combobox(top_bar, textvariable=self.profile_var,
                                          values=self.profile_manager.list_profiles(), state='readonly')
        self.profile_combo.pack(side='left', padx=(0, 8))

        def on_profile_change(event=None):
            new_profile = self.profile_var.get().strip() or 'default'
            try:
                self.profile_manager.set_current_profile(new_profile)
                # Rebind library to new profile
                if hasattr(self.library, 'observers') and self in getattr(self.library, 'observers', []):
                    try:
                        self.library.observers.remove(self)
                    except Exception:
                        pass
                self.library = MusicLibrary(new_profile)
                self.library.add_observer(self)
                self.update()
                self.set_status(f"Switched profile to '{new_profile}'")
            except Exception as e:
                self.set_status(f"Profile switch failed: {e}")

        self.profile_combo.bind('<<ComboboxSelected>>', on_profile_change)

        def on_new_profile():
            dialog = ttk.Toplevel(self.root)
            dialog.title("New Profile")
            ttk.Label(dialog, text="Profile name:").pack(padx=12, pady=(12, 4))
            name_var = ttk.StringVar()
            entry = ttk.Entry(dialog, textvariable=name_var)
            entry.pack(padx=12, pady=4, fill='x')
            entry.focus_set()

            def create_and_close():
                name = (name_var.get() or '').strip()
                if not name:
                    Messagebox.show_warning("Invalid Name", "Please enter a profile name.")
                    return
                self.profile_manager.set_current_profile(name)
                # refresh combo values
                self.profile_combo.configure(values=self.profile_manager.list_profiles())
                self.profile_var.set(name)
                on_profile_change()
                dialog.destroy()

            ttk.Button(dialog, text='Create', command=create_and_close, bootstyle='primary').pack(padx=12, pady=(6, 12))

        ttk.Button(top_bar, text='New Profile', command=on_new_profile, bootstyle='secondary').pack(side='left')

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

        # Deep Dive View
        self.deep_dive_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.deep_dive_frame, text='Deep Dive')
        self._setup_deep_dive_view()
    
    def _setup_library_view(self):
        """Setup the library view with consistent grid geometry management"""
        # Make library view scale
        self.library_frame.grid_rowconfigure(0, weight=1)
        self.library_frame.grid_columnconfigure(0, weight=1)
        
        # Track list with modern styling
        self.track_list = ttk.Treeview(
            self.library_frame, 
            columns=('Title', 'Artist', 'BPM', 'Key'),
            show='headings',
            bootstyle="dark"
        )
        
        # Configure columns
        for col in ('Title', 'Artist', 'BPM', 'Key'):
            self.track_list.heading(col, text=col)
            self.track_list.column(col, minwidth=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(
            self.library_frame, 
            orient="vertical", 
            command=self.track_list.yview
        )
        self.track_list.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout for track list and scrollbar
        self.track_list.grid(row=0, column=0, sticky='nsew', padx=10, pady=5)
        scrollbar.grid(row=0, column=1, sticky='ns', pady=5)
        
        # Control buttons frame
        controls = ttk.Frame(self.library_frame)
        controls.grid(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        
        # Configure the controls frame columns
        controls.columnconfigure(tuple(range(6)), weight=1)  # Equal width for 6 columns
        
        # Add buttons with grid
        ttk.Button(
            controls, 
            text='Add Track',
            bootstyle="primary",
            command=self._add_track_dialog
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            controls, 
            text='Import Playlist',
            bootstyle="primary",
            command=self._import_playlist_dialog
        ).grid(row=0, column=1, padx=5)
        
        ttk.Button(
            controls, 
            text='Remove Selected',
            bootstyle="danger",
            command=self._remove_selected
        ).grid(row=0, column=2, padx=5)
        
        ttk.Button(
            controls, 
            text='Remove All',
            bootstyle="danger",
            command=self._remove_all
        ).grid(row=0, column=3, padx=5)
        
        # Export button
        self.export_button = ttk.Button(
            controls,
            text="Export Playlist",
            command=self.export_playlist,
            bootstyle="secondary"
        )
        self.export_button.grid(row=0, column=4, padx=5)
        
        # Add track selection binding
        self.track_list.bind('<<TreeviewSelect>>', self._on_track_select)
    
    def _setup_analysis_view(self):
        """Setup the analysis view with playlist and track statistics"""
        self.analysis_scroll = ScrolledFrame(self.analysis_frame)
        self.analysis_scroll.pack(expand=True, fill='both', padx=5, pady=5)
        
        content = self.analysis_scroll.container
        
        # Use grid for better control
        content.grid_columnconfigure(0, weight=1)
        
        # Current Track Analysis
        self.current_track_frame = ttk.LabelFrame(content, text='Current Track Analysis')
        self.current_track_frame.grid(row=0, column=0, sticky='ew', padx=20, pady=10)
        
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

        # Preference toggles
        pref_frame = ttk.Frame(self.current_track_frame)
        pref_frame.pack(fill='x', padx=10, pady=(5, 5))

        def on_flag_change():
            if not self.current_track:
                return
            try:
                self.current_track.liked = bool(self.liked_var.get())
                self.current_track.loved = bool(self.loved_var.get())
                self.current_track.mood_dependent = bool(self.mood_dep_var.get())
                self.library.save()
                self.set_status("Preferences saved")
            except Exception as e:
                self.set_status(f"Error saving preferences: {e}")

        ttk.Checkbutton(pref_frame, text="Liked", variable=self.liked_var,
                        command=on_flag_change).pack(side='left', padx=(0, 10))
        ttk.Checkbutton(pref_frame, text="Loved", variable=self.loved_var,
                        command=on_flag_change).pack(side='left', padx=(0, 10))
        ttk.Checkbutton(pref_frame, text="Mood-dependent", variable=self.mood_dep_var,
                        command=on_flag_change).pack(side='left')
        
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
        
        # Playlist Analysis with better spacing
        playlist_stats = ttk.LabelFrame(
            content, 
            text='Playlist Analysis',
            style='Bold.TLabelframe'
        )
        playlist_stats.grid(row=1, column=0, sticky='ew', padx=20, pady=10)
        
        # Musical Statistics Section
        musical_stats = ttk.LabelFrame(
            playlist_stats, 
            text='Musical Statistics',
            style='Bold.TLabelframe'
        )
        musical_stats.pack(fill='x', padx=20, pady=10)
        
        musical_labels = [
            ('Average BPM:', 'N/A'),
            ('BPM Range:', 'N/A'),
            ('Common Keys:', 'N/A'),
            ('Average Energy:', 'N/A'),
            ('Common Camelot:', 'N/A'),
            ('Time Signatures:', 'N/A'),
            ('Common Genres:', 'N/A'),
            ('Total Genres:', 'N/A')
        ]
        
        self.musical_values = {}
        for label, default in musical_labels:
            # Create a frame for each stat to keep label and value on same line
            stat_frame = ttk.Frame(musical_stats)
            stat_frame.pack(fill='x', padx=10, pady=2)
            
            # Label and value on same line
            ttk.Label(stat_frame, text=label).pack(side='left')
            value_label = ttk.Label(stat_frame, text=default)
            value_label.pack(side='left', padx=(5, 0))  # Small padding between label and value
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
            ('Least Common Artist:', 'N/A'),
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
        """Setup the Discovery tab with entropy controls and recommendations display."""
        self.discovery_frame.grid_columnconfigure(0, weight=1)
        self.discovery_frame.grid_rowconfigure(1, weight=1) # For the recommendations list

        # Controls Frame
        controls_frame = ttk.Frame(self.discovery_frame, padding=10)
        controls_frame.grid(row=0, column=0, sticky="ew")
        controls_frame.grid_columnconfigure(1, weight=1) # Allow slider to expand

        ttk.Label(controls_frame, text="Entropy (Comfort Zone <-> Cosmic Drift):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.entropy_var = ttk.DoubleVar(value=0.25) # Default entropy
        self.entropy_slider = ttk.Scale(controls_frame, from_=0.0, to=1.0, 
                                        orient='horizontal', variable=self.entropy_var,
                                        command=self._on_entropy_slider_change) # Optional: update label on change
        self.entropy_slider.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.entropy_value_label = ttk.Label(controls_frame, text=f"{self.entropy_var.get():.2f}")
        self.entropy_value_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.get_recs_button = ttk.Button(controls_frame, text="Get Quantum Recommendations", 
                                            command=self._trigger_recommendations)
        self.get_recs_button.grid(row=0, column=3, padx=10, pady=5, sticky="e")

        if self.entropy_service is None:
            self.get_recs_button.config(state="disabled")
            ttk.Label(controls_frame, text="(OccyByte API N/A)", bootstyle="warning").grid(row=0, column=4, padx=5, pady=5, sticky="w")

        # Recommendations List Frame (to contain Treeview and Scrollbar)
        recs_list_frame = ttk.Frame(self.discovery_frame)
        recs_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        recs_list_frame.grid_rowconfigure(0, weight=1)
        recs_list_frame.grid_columnconfigure(0, weight=1)

        self.recommendations_tree = ttk.Treeview(recs_list_frame,
                                               columns=('Title', 'Artist', 'BPM', 'Key', 'Genres'),
                                               show='headings', bootstyle="dark")
        self.recommendations_tree.grid(row=0, column=0, sticky="nsew")

        recs_scrollbar = ttk.Scrollbar(recs_list_frame, orient="vertical", command=self.recommendations_tree.yview)
        self.recommendations_tree.configure(yscrollcommand=recs_scrollbar.set)
        recs_scrollbar.grid(row=0, column=1, sticky="ns")

        self.recommendations_tree.heading('Title', text='Title')
        self.recommendations_tree.heading('Artist', text='Artist')
        self.recommendations_tree.heading('BPM', text='BPM')
        self.recommendations_tree.heading('Key', text='Key')
        self.recommendations_tree.heading('Genres', text='Genres')

        self.recommendations_tree.column('Title', width=250, stretch=True)
        self.recommendations_tree.column('Artist', width=150, stretch=True)
        self.recommendations_tree.column('BPM', width=60, stretch=False, anchor="center")
        self.recommendations_tree.column('Key', width=80, stretch=False, anchor="center")
        self.recommendations_tree.column('Genres', width=200, stretch=True)
        
        # Add a way to select the seed track for recommendations
        # For now, it will use self.current_track (selected from main library)
        # Could add a label: "Seed Track: [self.current_track.title if self.current_track else 'None']"
        self.seed_track_label = ttk.Label(controls_frame, text="Seed: None selected")
        self.seed_track_label.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="w")

    def _setup_deep_dive_view(self):
        self.deep_dive_frame.grid_columnconfigure(0, weight=1)
        self.deep_dive_frame.grid_rowconfigure(1, weight=1)

        controls = ttk.Frame(self.deep_dive_frame, padding=10)
        controls.grid(row=0, column=0, sticky='ew')
        ttk.Label(controls, text="Artist Deep Dive (MusicBrainz)").grid(row=0, column=0, sticky='w')
        self.dd_status = ttk.Label(controls, text="Idle")
        self.dd_status.grid(row=0, column=1, sticky='e')

        ttk.Button(controls, text="Deep Dive Selected Artist", command=self._deep_dive_current_artist,
                   bootstyle='primary').grid(row=1, column=0, pady=6, sticky='w')

        # Results tree
        results_frame = ttk.Frame(self.deep_dive_frame)
        results_frame.grid(row=1, column=0, sticky='nsew')
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        self.dd_tree = ttk.Treeview(results_frame, columns=("Title", "Type", "First-Release"), show='headings', bootstyle='dark')
        self.dd_tree.heading("Title", text="Release Group")
        self.dd_tree.heading("Type", text="Type")
        self.dd_tree.heading("First-Release", text="First Release Date")
        self.dd_tree.column("Title", width=400, stretch=True)
        self.dd_tree.column("Type", width=120, stretch=False)
        self.dd_tree.column("First-Release", width=140, stretch=False)
        self.dd_tree.grid(row=0, column=0, sticky='nsew')
        scr = ttk.Scrollbar(results_frame, orient='vertical', command=self.dd_tree.yview)
        self.dd_tree.configure(yscrollcommand=scr.set)
        scr.grid(row=0, column=1, sticky='ns')

    def _deep_dive_current_artist(self):
        if not self.current_track:
            Messagebox.show_info("No Artist", "Select a track first in Library to deep dive its artist.")
            return
        artist_name = self.current_track.artist
        try:
            self.dd_status.config(text=f"Searching '{artist_name}'...")
            artists = self.musicbrainz_service.search_artist(artist_name, limit=5)
            if not artists:
                self.dd_status.config(text="No artist match")
                return
            # pick top-scoring match
            artist = sorted(artists, key=lambda a: a.get('score', 0), reverse=True)[0]
            mbid = artist.get('id')
            self.dd_status.config(text=f"Fetching release groups...")
            rg_data = self.musicbrainz_service.get_release_groups_for_artist(mbid, limit=100, offset=0)
            rgs = rg_data.get('release-groups', [])
            # Render
            for item in self.dd_tree.get_children():
                self.dd_tree.delete(item)
            for rg in rgs:
                title = rg.get('title') or 'Untitled'
                rtype = rg.get('primary-type') or '—'
                fdate = rg.get('first-release-date') or '—'
                self.dd_tree.insert('', 'end', values=(title, rtype, fdate))
            self.dd_status.config(text=f"Found {len(rgs)} release groups")
        except Exception as e:
            self.dd_status.config(text="Error")
            Messagebox.show_error("Deep Dive Error", f"Failed to fetch data: {e}")

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
        """Show dialog to import a Spotify playlist"""
        dialog = ImportPlaylistDialog(self.root, self.spotify_service)
        
        # Wait for dialog to close and check result
        self.root.wait_window(dialog)
        
        if dialog.result:
            url = dialog.result
            print(f"Starting import of playlist: {url}")  # Debug print
            
            def on_import_complete(tracks):
                if tracks:
                    print(f"Import completed with {len(tracks)} tracks")  # Debug print
                    self.library.add_tracks(tracks)
                    self._update_analysis()
                    self.set_status(f"Imported {len(tracks)} tracks")
                else:
                    print("Import failed - no tracks found")  # Debug print
                    self.set_status("Import failed - no tracks found")
            
            try:
                self.set_status("Importing playlist...")
                self.current_playlist_url = url
                # Start the async import
                self.spotify_service.import_playlist_async(
                    url, 
                    callback=on_import_complete
                )
            except Exception as e:
                print(f"Import error: {str(e)}")  # Debug print
                self.set_status(f"Import error: {str(e)}")
                Messagebox.show_error(
                    message=f"Import failed: {str(e)}",
                    title="Import Error"
                )
    
    def _remove_selected(self):
        """Remove selected tracks from the library"""
        selected_items = self.track_list.selection()
        if not selected_items:
            return
            
        msg = "Are you sure you want to remove the selected track?" if len(selected_items) == 1 \
              else f"Are you sure you want to remove {len(selected_items)} tracks?"
            
        dialog = ScaledMessageDialog(
            self.root,
            "Confirm Remove",
            msg,
            buttons=['Yes:primary', 'No:secondary']
        )
        
        if dialog.result == 'Yes':
            tracks = self.library.get_all_tracks()
            for item in selected_items:
                idx = self.track_list.index(item)
                if 0 <= idx < len(tracks):
                    track = tracks[idx]
                    self.library.remove_track(track)
            
            self._update_analysis()
            self.set_status(f"Removed {len(selected_items)} track(s)")

    def _remove_all(self):
        """Remove all tracks from the library"""
        if not self.library.get_all_tracks():
            return
            
        dialog = ScaledMessageDialog(
            self.root,
            "Confirm Remove All",
            "Are you sure you want to remove ALL tracks?",
            buttons=['Yes:danger', 'No:secondary']
        )
        
        if dialog.result == 'Yes':
            self.library.clear()
            self._update_analysis()
            self.set_status("Removed all tracks")

    def export_playlist(self):
        """Handle playlist export"""
        tracks = self.library.get_all_tracks()
        if not tracks:
            Messagebox.show_warning(
                "No Tracks",
                "Your library is empty. Import or add tracks before exporting."
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
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("Curator Apollon - Playlist Export\n")
                    f.write("================================\n\n")
                    for i, track in enumerate(tracks, 1):
                        album_name = track.album if getattr(track, 'album', None) else "Unknown Album"
                        f.write(f"{i}. {track.title} - {track.artist} [{album_name}]\n")
                self.set_status(f"Playlist exported to {file_path}")
                Messagebox.show_info(
                    "Export Successful",
                    f"Playlist has been exported to:\n{file_path}"
                )
            except Exception as e:
                self.set_status("Export failed")
                Messagebox.show_error(
                    "Export Failed",
                    f"Failed to export playlist. Error: {e}"
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
            least_common_artist = min(artist_counts.items(), key=lambda x: x[1])
            
            self.literary_values['Most Common Artist:'].config(
                text=f"{most_common_artist[0]} ({most_common_artist[1]} tracks)"
            )
            self.literary_values['Least Common Artist:'].config(
                text=f"{least_common_artist[0]} ({least_common_artist[1]} tracks)"
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
        for track in tracks:
            sig = track.time_signature
            if sig != "Unknown":
                time_sigs[sig] = time_sigs.get(sig, 0) + 1
        
        if time_sigs:
            sig_display = []
            for sig, count in sorted(time_sigs.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(tracks)) * 100
                sig_display.append(f"{sig}({count}, {percentage:.1f}%)")
            
            self.musical_values['Time Signatures:'].config(text=", ".join(sig_display))
        else:
            self.musical_values['Time Signatures:'].config(text="N/A")

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

            # Update preference toggles
            self.liked_var.set(bool(getattr(self.current_track, 'liked', False)))
            self.loved_var.set(bool(getattr(self.current_track, 'loved', False)))
            self.mood_dep_var.set(bool(getattr(self.current_track, 'mood_dependent', False)))
            
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
            self.liked_var.set(False)
            self.loved_var.set(False)
            self.mood_dep_var.set(False)

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
        """Update musical analysis with essential stats"""
        if not tracks:
            return
            
        # BPM Analysis
        bpms = [t.bpm for t in tracks if t.bpm and t.bpm > 0]
        if bpms:
            avg_bpm = sum(bpms) / len(bpms)
            min_bpm = min(bpms)
            max_bpm = max(bpms)
            
            self.musical_values['Average BPM:'].config(text=f"{avg_bpm:.1f}")
            self.musical_values['BPM Range:'].config(text=f"{min_bpm:.1f} - {max_bpm:.1f}")
        else:
            self.musical_values['Average BPM:'].config(text="N/A")
            self.musical_values['BPM Range:'].config(text="N/A")
        
        # Key Analysis
        keys = [t.key for t in tracks if t.key and t.key != "Unknown"]
        if keys:
            key_counts = {}
            for key in keys:
                key_counts[key] = key_counts.get(key, 0) + 1
            common_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            key_display = ", ".join(f"{k}({v})" for k, v in common_keys)
            self.musical_values['Common Keys:'].config(text=key_display)
        else:
            self.musical_values['Common Keys:'].config(text="N/A")
        
        # Energy Analysis
        energies = [t.energy_level for t in tracks if t.energy_level is not None and t.energy_level > 0]
        if energies:
            avg_energy = sum(energies) / len(energies)
            self.musical_values['Average Energy:'].config(text=f"{avg_energy:.2f}")
        else:
            self.musical_values['Average Energy:'].config(text="N/A")
        
        # Camelot Analysis
        camelot = [t.camelot_position for t in tracks if t.camelot_position and t.camelot_position != "Unknown"]
        if camelot:
            camelot_counts = {}
            for pos in camelot:
                camelot_counts[pos] = camelot_counts.get(pos, 0) + 1
            common_pos = sorted(camelot_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            pos_display = ", ".join(f"{p}({v})" for p, v in common_pos)
            self.musical_values['Common Camelot:'].config(text=pos_display)
        else:
            self.musical_values['Common Camelot:'].config(text="N/A")
        
        # Time Signature Analysis
        time_sigs = {}
        for track in tracks:
            sig = track.time_signature
            if sig != "Unknown":
                time_sigs[sig] = time_sigs.get(sig, 0) + 1
        
        if time_sigs:
            sig_display = []
            for sig, count in sorted(time_sigs.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(tracks)) * 100
                sig_display.append(f"{sig}({count}, {percentage:.1f}%)")
            self.musical_values['Time Signatures:'].config(text=", ".join(sig_display))
        else:
            self.musical_values['Time Signatures:'].config(text="N/A")

        # Genre Analysis
        all_genres = []
        for track in tracks:
            if track.genres:
                all_genres.extend(track.genres)
        
        if all_genres:
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            # Most common genres
            common_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            genre_display = ", ".join(f"{g}({c})" for g, c in common_genres)
            
            self.musical_values['Common Genres:'].config(text=genre_display)
            self.musical_values['Total Genres:'].config(text=str(len(set(all_genres))))
        else:
            self.musical_values['Common Genres:'].config(text="N/A")
            self.musical_values['Total Genres:'].config(text="N/A")

    def _update_literary_analysis(self, tracks: List[Track]):
        """Update literary analysis with handling for missing features"""
        if not tracks:
            return
            
        # Literary Analysis
        artists = [t.artist for t in tracks]
        titles = [t.title for t in tracks]
        
        # Artist Analysis
        artist_counts = {}
        for artist in artists:
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
        
        if artist_counts:
            most_common_artist = max(artist_counts.items(), key=lambda x: x[1])
            least_common_artist = min(artist_counts.items(), key=lambda x: x[1])
            
            self.literary_values['Most Common Artist:'].config(
                text=f"{most_common_artist[0]} ({most_common_artist[1]} tracks)"
            )
            self.literary_values['Least Common Artist:'].config(
                text=f"{least_common_artist[0]} ({least_common_artist[1]} tracks)"
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
        for track in tracks:
            sig = track.time_signature
            if sig != "Unknown":
                time_sigs[sig] = time_sigs.get(sig, 0) + 1
        
        if time_sigs:
            sig_display = []
            for sig, count in sorted(time_sigs.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(tracks)) * 100
                sig_display.append(f"{sig}({count}, {percentage:.1f}%)")
            
            self.musical_values['Time Signatures:'].config(text=", ".join(sig_display))
        else:
            self.musical_values['Time Signatures:'].config(text="N/A")

    def _on_entropy_slider_change(self, value):
        self.entropy_value_label.config(text=f"{float(value):.2f}")

    def _trigger_recommendations(self):
        if self.entropy_service is None:
            Messagebox.show_warning("API Error", "EntropyService is not available. Cannot get recommendations.")
            return

        if self.current_track is None:
            Messagebox.show_info("No Seed Track", "Please select a track from the Library to use as a seed for recommendations.")
            return

        entropy_val = self.entropy_var.get()
        all_tracks = self.library.get_all_tracks()
        if not all_tracks:
            Messagebox.show_info("Empty Library", "Your music library is empty. Add some tracks first!")
            return

        self.set_status(f"Getting quantum recommendations with entropy {entropy_val:.2f} based on {self.current_track.title}...")
        
        try:
            # Call EntropyService (adjust num_recommendations as needed)
            recommended_tracks = self.entropy_service.recommend_tracks(
                current_tracks=all_tracks,
                current_playing_track=self.current_track,
                entropy_level=entropy_val,
                num_recommendations=10 
            )
        except Exception as e:
            print(f"Error calling recommend_tracks: {e}")
            Messagebox.showerror("Recommendation Error", f"An error occurred while generating recommendations: {e}")
            self.set_status("Error getting recommendations.")
            return

        # Clear previous recommendations
        for item in self.recommendations_tree.get_children():
            self.recommendations_tree.delete(item)

        if recommended_tracks:
            for track in recommended_tracks:
                genre_str = ", ".join(track.genres) if track.genres else "N/A"
                self.recommendations_tree.insert('', 'end', values=(
                    track.title, track.artist, f"{track.bpm:.0f}" if track.bpm else "N/A", 
                    track.camelot_position if track.camelot_position else "N/A", 
                    genre_str
                ))
            self.set_status(f"Displayed {len(recommended_tracks)} recommendations.")
        else:
            self.set_status("No recommendations found based on current settings and seed track.")
            # Optionally, insert a message into the treeview itself
            # self.recommendations_tree.insert('', 'end', values=("No recommendations found.", "", "", "", ""))

class ImportPlaylistDialog(ttk.Toplevel):
    """Custom dialog for importing playlists with proper sizing"""
    def __init__(self, parent, spotify_service, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title("Import Spotify Playlist")
        self.spotify_service = spotify_service
        self.result = None
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        
        # Status label
        self.status_label = ttk.Label(
            self,
            text="Checking authentication status...",
            foreground="gold",
            justify="center"
        )
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky='ew')
        
        # Auth button
        self.auth_button = ttk.Button(
            self,
            text="Check Auth",
            bootstyle="info",
            command=self._check_auth,
            width=15  # Make button wider
        )
        self.auth_button.grid(row=1, column=0, pady=10)
        
        # URL entry section
        url_frame = ttk.Frame(self)
        url_frame.grid(row=2, column=0, padx=20, pady=10, sticky='ew')
        url_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(
            url_frame,
            text="Enter Spotify Playlist URL:",
            foreground="gold"
        ).grid(row=0, column=0, pady=(0, 5), sticky='w')
        
        self.url_var = ttk.StringVar()
        self.url_entry = ttk.Entry(
            url_frame,
            textvariable=self.url_var,
            width=50  # Make entry wider
        )
        self.url_entry.grid(row=1, column=0, sticky='ew')
        
        # Import button
        self.import_button = ttk.Button(
            self,
            text="Import",
            bootstyle="primary",
            command=self._on_import,
            width=15,  # Make button wider
            state='disabled'  # Start disabled until auth check
        )
        self.import_button.grid(row=3, column=0, pady=20)
        
        # Set dialog size and position
        self.update_idletasks()
        width = 500  # Fixed width
        height = 200  # Fixed height
        
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(width, height)
        
        # Start auth check
        self.after(100, self._check_auth)
    
    def _check_auth(self):
        """Check Spotify authentication status"""
        try:
            self.spotify_service.ensure_authenticated()
            self.status_label.config(text="Authentication successful!")
            self.auth_button.config(state='disabled')
            self.import_button.config(state='normal')
            self.url_entry.focus_set()
        except Exception as e:
            self.status_label.config(text="Authentication failed. Please try again.")
            self.auth_button.config(state='normal')
            self.import_button.config(state='disabled')
    
    def _on_import(self):
        """Handle import button click"""
        url = self.url_var.get().strip()  # Add strip() to remove whitespace
        if not url:
            Messagebox.show_error(
                message="Please enter a playlist URL",
                title="Import Error"
            )
            return
            
        # Basic URL validation
        if not url.startswith('https://open.spotify.com/playlist/'):
            Messagebox.show_error(
                message="Please enter a valid Spotify playlist URL",
                title="Import Error"
            )
            return
            
        print(f"Dialog returning URL: {url}")  # Debug print
        self.result = url
        self.destroy()

class ScaledMessageDialog(ttk.Toplevel):
    """Custom dialog with uniform sizing and proper text scaling"""
    def __init__(self, parent, title, message, buttons=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title(title)
        self.result = None
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Message area with word wrap
        msg_frame = ttk.Frame(self)
        msg_frame.grid(row=0, column=0, padx=20, pady=20, sticky='nsew')
        msg_frame.grid_columnconfigure(0, weight=1)
        
        msg_label = ttk.Label(
            msg_frame, 
            text=message,
            wraplength=400,  # Wrap text at 400 pixels
            justify='center'
        )
        msg_label.grid(sticky='nsew')
        
        # Button area
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky='ew')
        
        if not buttons:
            buttons = ['OK:primary']
            
        # Center buttons
        btn_frame.grid_columnconfigure(len(buttons)-1, weight=1)
        
        for i, btn_spec in enumerate(buttons):
            text, style = btn_spec.split(':')
            btn = ttk.Button(
                btn_frame,
                text=text,
                bootstyle=style,
                command=lambda t=text: self._on_button(t),
                width=10  # Uniform button width
            )
            btn.grid(row=0, column=i, padx=5)
        
        # Center the dialog on parent
        self.update_idletasks()
        width = max(400, self.winfo_reqwidth() + 40)  # Min width 400
        height = self.winfo_reqheight() + 20
        
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set minimum size
        self.minsize(width, height)
        
        # Make dialog visible and wait for it to close
        self.wait_visibility()
        self.focus_set()
        self.wait_window()
    
    def _on_button(self, value):
        self.result = value
        self.destroy() 