# Curator Apollon: A Quantum-Powered Music Analysis and Discovery Tool
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
import os
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image, ImageTk
from models.library import MusicLibrary
from views.main_window import MainWindow
from services.spotify_service import SpotifyService
from services.analysis_service import AnalysisService
from services.entropy_service import EntropyService

# Load environment variables from .env file
# This should be one of the first things your application does.
load_dotenv()

class CuratorApollon:
    def __init__(self):
        self.root = ttk.Window(
            title="Curator Apollon",
            themename="darkly",
            size=(1200, 800)
        )
        self.root.geometry("1200x800")
        
        # Set window icon
        icon_path = Path(__file__).resolve().parent / "appearance" / "img" / "apollon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except Exception as e:
                print(f"Error setting icon: {e}")
        else:
            print(f"Icon not found at {icon_path}")
        
        # Initialize services and views
        self.library = MusicLibrary()
        self.spotify_service = SpotifyService()
        self.analysis_service = AnalysisService()
        
        # Instantiate EntropyService
        self.entropy_service = None # Initialize to None
        try:
            self.entropy_service = EntropyService() # Relies on ENV variables for API key/link
            print("EntropyService initialized successfully.")
        except ValueError as e:
            print(f"Critical: Failed to initialize EntropyService: {e}")
            print("Recommendation features requiring OccyByte API will be disabled.")
        except Exception as e: # Catch any other unexpected errors during init
            print(f"Unexpected error initializing EntropyService: {e}")
            print("Recommendation features may be unstable.")

        self.main_window = MainWindow(self.root, self.library, 
                                    self.spotify_service, 
                                    self.analysis_service,
                                    self.entropy_service) # Pass EntropyService
    
    def run(self):
        self.root.mainloop()

def main():
    app = CuratorApollon()
    app.run()

if __name__ == "__main__":
    main() 