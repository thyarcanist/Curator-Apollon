from PIL import Image
import os

def create_ico():
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "img", "laurel-circlet.png")
    dst_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "img", "laurel-circlet.ico")
    
    if os.path.exists(src_path):
        # Open PNG
        img = Image.open(src_path)
        
        # Convert to RGBA if not already
        img = img.convert('RGBA')
        
        # Create ICO file with multiple sizes
        icon_sizes = [(16,16), (32,32), (48,48), (64,64)]
        img.save(dst_path, format='ICO', sizes=icon_sizes)
        print(f"Created ICO file at {dst_path}")
    else:
        print(f"Source image not found at {src_path}")

if __name__ == "__main__":
    create_ico() 