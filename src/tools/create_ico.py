from PIL import Image
from pathlib import Path

def create_ico():
    # Get the path to the PNG file
    src_dir = Path(__file__).parent.parent / "appearance" / "img"
    png_path = src_dir / "laurel-circlet.png"
    ico_path = src_dir / "apollon.ico"
    
    # Open the PNG and convert to ICO
    img = Image.open(png_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Create ICO file with multiple sizes
    img.save(ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
    
    print(f"Created ICO file at: {ico_path}")

if __name__ == "__main__":
    create_ico() 