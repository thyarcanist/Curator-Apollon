import tkinter as tk
from tkinter import ttk, messagebox
from typing import List
from models.library import MusicLibrary, Track
from services.spotify_service import SpotifyService
from services.analysis_service import AnalysisService

class MainWindow:
    def __init__(self, root, library: MusicLibrary, 
                 spotify_service: SpotifyService,
                 analysis_service: AnalysisService):
        self.root = root
        self.library = library
        self.spotify_service = spotify_service
        self.analysis_service = analysis_service
        
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
        # Track list
        self.track_list = ttk.Treeview(self.library_frame, 
                                      columns=('Title', 'Artist', 'BPM', 'Key'),
                                      show='headings')
        self.track_list.heading('Title', text='Title')
        self.track_list.heading('Artist', text='Artist')
        self.track_list.heading('BPM', text='BPM')
        self.track_list.heading('Key', text='Key')
        self.track_list.pack(expand=True, fill='both')
        
        # Control buttons
        controls = ttk.Frame(self.library_frame)
        controls.pack(fill='x', pady=5)
        
        ttk.Button(controls, text='Add Track', 
                  command=self._add_track_dialog).pack(side='left', padx=5)
        ttk.Button(controls, text='Import Playlist', 
                  command=self._import_playlist_dialog).pack(side='left', padx=5)
        ttk.Button(controls, text='Remove Selected', 
                  command=self._remove_selected).pack(side='left', padx=5)
    
    def _setup_analysis_view(self):
        # Analysis details
        self.analysis_details = ttk.LabelFrame(self.analysis_frame, text='Track Analysis')
        self.analysis_details.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Will add Camelot wheel visualization here
        
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
        dialog = tk.Toplevel(self.root)
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
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Spotify Playlist")
        dialog.geometry("500x150")
        
        ttk.Label(dialog, text="Enter Spotify Playlist URL:").pack(pady=5)
        url_entry = ttk.Entry(dialog, width=50)
        url_entry.pack(fill='x', padx=20)
        
        def handle_import():
            try:
                # Show authentication instructions
                messagebox.showinfo(
                    "Spotify Authentication",
                    "You will be redirected to Spotify to authenticate.\n\n"
                    "After authorizing, you will be redirected to apollon.occybyte.com.\n\n"
                    "Copy the FULL URL from your browser and paste it in the next dialog."
                )
                url = url_entry.get()
                tracks = self.spotify_service.import_playlist(url)
                for track in tracks:
                    self.library.add_track(track)
                dialog.destroy()
                messagebox.showinfo("Success", f"Imported {len(tracks)} tracks")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(dialog, text="Import", command=handle_import).pack(pady=20)
    
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