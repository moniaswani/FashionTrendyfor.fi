#!/usr/bin/env python3
"""
Diagnostic script to check folder and dependencies
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    print("=" * 60)
    print("CHECKING DEPENDENCIES")
    print("=" * 60)
    
    packages = {
        'rembg': 'rembg',
        'PIL': 'Pillow',
        'numpy': 'numpy'
    }
    
    missing = []
    for module, package in packages.items():
        try:
            __import__(module)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is NOT installed")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"\n💡 Install with: pip install {' '.join(missing)}")
        return False
    else:
        print(f"\n✓ All dependencies installed!")
        return True

def check_folder(folder_path):
    """Check folder contents"""
    print("\n" + "=" * 60)
    print("CHECKING FOLDER")
    print("=" * 60)
    print(f"Path: {folder_path}")
    
    if not os.path.exists(folder_path):
        print(f"\n❌ Folder does not exist!")
        return False
    
    if not os.path.isdir(folder_path):
        print(f"\n❌ Path exists but is not a folder!")
        return False
    
    print(f"✓ Folder exists")
    
    path = Path(folder_path)
    all_items = list(path.iterdir())
    
    print(f"\n📁 Total items in folder: {len(all_items)}")
    
    if len(all_items) == 0:
        print("   Folder is empty!")
        return False
    
    # Count by type
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
    images = [f for f in all_items if f.is_file() and f.suffix.lower() in image_extensions]
    other_files = [f for f in all_items if f.is_file() and f.suffix.lower() not in image_extensions]
    folders = [f for f in all_items if f.is_dir()]
    
    print(f"\n📊 Breakdown:")
    print(f"   Images: {len(images)}")
    print(f"   Other files: {len(other_files)}")
    print(f"   Subfolders: {len(folders)}")
    
    if images:
        print(f"\n🖼️  Image files found:")
        for img in images[:10]:
            size_mb = img.stat().st_size / (1024 * 1024)
            print(f"   - {img.name} ({size_mb:.2f} MB)")
        if len(images) > 10:
            print(f"   ... and {len(images) - 10} more images")
        return True
    else:
        print(f"\n❌ No image files found!")
        if other_files:
            print(f"\nOther files in folder:")
            for f in other_files[:5]:
                print(f"   - {f.name} (type: {f.suffix})")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python diagnostic.py <folder_path>")
        print("\nExample:")
        print("  python diagnostic.py /path/to/your/images")
        return
    
    folder_path = sys.argv[1]
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check folder
    folder_ok = check_folder(folder_path)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if deps_ok and folder_ok:
        print("✓ Everything looks good! You can run the segmentation script.")
        print(f"\nRun this command:")
        print(f"  python runway_segmentation.py \"{folder_path}\"")
    else:
        print("❌ Issues found. Please fix the problems above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
