from PIL import Image
from pathlib import Path

def create_ico():
    # Get the path to the source image
    src_path = Path(__file__).parent.parent / "appearance" / "img" / "laurel-circlet.png"
    dst_path = Path(__file__).parent.parent / "appearance" / "img" / "apollon.ico"
    
    if not src_path.exists():
        print(f"Source image not found: {src_path}")
        return
    
    # Open the PNG image
    img = Image.open(src_path)
    
    # Create ICO file with multiple sizes
    icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128)]
    img.save(dst_path, format='ICO', sizes=icon_sizes)
    print(f"Created ICO file: {dst_path}")

if __name__ == "__main__":
    create_ico() 