#!/usr/bin/env python3
import os
import sys
from PIL import Image

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_src = os.path.join(base_dir, 'icon.png')
    
    if not os.path.exists(icon_src):
        print(f"Source icon not found at {icon_src}", file=sys.stderr)
        sys.exit(1)
        
    home = os.path.expanduser('~')
    sizes = [16, 32, 48, 64, 128, 256, 512]
    img = Image.open(icon_src)
    
    for s in sizes:
        target_dir = os.path.join(home, '.local', 'share', 'icons', 'hicolor', f'{s}x{s}', 'apps')
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, 'sim-companies.png')
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(target_file, format='PNG')
        print(f"Installed icon: {target_file}")

if __name__ == '__main__':
    main()
