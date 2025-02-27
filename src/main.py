import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
from PIL import Image, ImageTk
from models.library import MusicLibrary
from views.main_window import MainWindow
from services.spotify_service import SpotifyService
from services.analysis_service import AnalysisService

class CuratorApollon:
    def __init__(self):
        self.root = ttk.Window(
            title="Curator Apollon",
            themename="darkly",
            size=(800, 600)
        )
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "img", "laurel-circlet.png")
        if os.path.exists(icon_path):
            try:
                # Create PhotoImage from PNG
                icon = Image.open(icon_path)
                # Convert to RGBA if not already
                icon = icon.convert('RGBA')
                # Resize for Windows taskbar
                icon = icon.resize((32, 32), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(icon)
                # Set icon
                self.root.iconphoto(True, photo)
                # Keep reference
                self.icon_photo = photo
            except Exception as e:
                print(f"Warning: Could not set window icon: {str(e)}")
        
        # Initialize services and views
        self.library = MusicLibrary()
        self.spotify_service = SpotifyService()
        self.analysis_service = AnalysisService()
        self.main_window = MainWindow(self.root, self.library, 
                                    self.spotify_service, 
                                    self.analysis_service)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = CuratorApollon()
    app.run() 