import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
from PIL import Image, ImageTk
from models.library import MusicLibrary
from views.main_window import MainWindow
from services.spotify_service import SpotifyService
from services.analysis_service import AnalysisService
from pathlib import Path

class CuratorApollon:
    def __init__(self):
        self.root = ttk.Window(
            title="Curator Apollon",
            themename="darkly",
            size=(800, 600)
        )
        
        # Set window icon
        icon_path = Path(__file__).parent / "appearance" / "img" / "apollon.ico"
        if icon_path.exists():
            self.root.iconbitmap(default=str(icon_path))
        
        # Initialize services and views
        self.library = MusicLibrary()
        self.spotify_service = SpotifyService()
        self.analysis_service = AnalysisService()
        self.main_window = MainWindow(self.root, self.library, 
                                    self.spotify_service, 
                                    self.analysis_service)
    
    def run(self):
        self.root.mainloop()

def main():
    root = ttk.Window(themename="darkly")
    root.title("Curator Apollon")
    root.geometry("1200x800")
    
    # Set window icon
    icon_path = Path(__file__).parent / "appearance" / "img" / "apollon.ico"
    if icon_path.exists():
        root.iconbitmap(default=str(icon_path))
    
    library = MusicLibrary()
    spotify_service = SpotifyService()
    analysis_service = AnalysisService()
    
    app = MainWindow(root, library, spotify_service, analysis_service)
    root.mainloop()

if __name__ == "__main__":
    main() 