#!/usr/bin/env python3
"""
Runway Model Image Segmentation Script
Uses rembg (U-2-Net) to segment runway models from backgrounds
"""

import os
from pathlib import Path
from rembg import remove
from PIL import Image
import argparse


def process_images(input_folder, output_folder, alpha_matting=False):
    """
    Process all images in input folder and save segmented versions to output folder
    
    Args:
        input_folder: Path to folder containing input images
        output_folder: Path to folder where segmented images will be saved
        alpha_matting: Enable alpha matting for better edge quality (slower)
    """
    # Create output folder if it doesn't exist
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Supported image formats
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
    
    # Get all image files from input folder
    input_path = Path(input_folder)
    image_files = [f for f in input_path.iterdir() 
                   if f.is_file() and f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"No images found in {input_folder}")
        return
    
    print(f"Found {len(image_files)} images to process")
    print(f"Output folder: {output_folder}")
    print("-" * 50)
    
    # Process each image
    for idx, image_file in enumerate(image_files, 1):
        try:
            print(f"Processing [{idx}/{len(image_files)}]: {image_file.name}")
            
            # Open image
            with Image.open(image_file) as img:
                # Remove background
                output = remove(
                    img,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=10
                )
                
                # Save with transparent background (PNG format)
                output_file = output_path / f"{image_file.stem}_segmented.png"
                output.save(output_file, "PNG")
                
                print(f"✓ Saved: {output_file.name}")
                
        except Exception as e:
            print(f"✗ Error processing {image_file.name}: {str(e)}")
            continue
    
    print("-" * 50)
    print(f"Processing complete! Segmented images saved to: {output_folder}")


def main():
    parser = argparse.ArgumentParser(
        description="Segment runway model images using rembg (U-2-Net)"
    )
    parser.add_argument(
        "input_folder",
        help="Path to folder containing input images"
    )
    parser.add_argument(
        "-o", "--output",
        default="output_segmented",
        help="Path to output folder (default: output_segmented)"
    )
    parser.add_argument(
        "--alpha-matting",
        action="store_true",
        help="Enable alpha matting for better edge quality (slower)"
    )
    
    args = parser.parse_args()
    
    # Check if input folder exists
    if not os.path.isdir(args.input_folder):
        print(f"Error: Input folder '{args.input_folder}' does not exist")
        return
    
    # Process images
    process_images(args.input_folder, args.output, args.alpha_matting)


if __name__ == "__main__":
    main()