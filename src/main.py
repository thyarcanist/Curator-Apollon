import tkinter as tk
from tkinter import ttk
from models.library import MusicLibrary
from views.main_window import MainWindow
from services.spotify_service import SpotifyService
from services.analysis_service import AnalysisService

class CuratorApollon:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Curator Apollon")
        self.root.geometry("1200x800")
        
        # Initialize core services
        self.spotify_service = SpotifyService()
        self.analysis_service = AnalysisService()
        self.library = MusicLibrary()
        
        # Initialize main window
        self.main_window = MainWindow(self.root, self.library, 
                                    self.spotify_service, 
                                    self.analysis_service)
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = CuratorApollon()
    app.run() 