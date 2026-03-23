#!/usr/bin/env python3
"""
Runway Model Image Segmentation Script (Recursive)
Preserves folder structure in output
"""

import os
from pathlib import Path
from rembg import remove
from PIL import Image
import argparse


def process_images(input_folder, output_folder, alpha_matting=False):
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}

    # Walk through all subfolders
    all_images = list(input_path.rglob("*"))

    image_files = [
        f for f in all_images
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

    if not image_files:
        print(f"No images found in {input_folder}")
        return

    print(f"Found {len(image_files)} images to process")
    print(f"Output root: {output_folder}")
    print("-" * 50)

    for idx, image_file in enumerate(image_files, 1):
        try:
            # Preserve relative folder structure
            relative_path = image_file.relative_to(input_path)
            output_subfolder = output_path / relative_path.parent
            output_subfolder.mkdir(parents=True, exist_ok=True)

            # Output file path
            output_file = output_subfolder / f"{image_file.stem}_segmented.png"

            # Skip if already processed
            if output_file.exists():
                print(f"→ Skipping (already processed): {relative_path}")
                continue

            print(f"Processing [{idx}/{len(image_files)}]: {relative_path}")

            with Image.open(image_file) as img:
                output = remove(
                    img,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=10
                )

                output.save(output_file, "PNG")
                print(f"✓ Saved: {output_file}")

        except Exception as e:
            print(f"✗ Error processing {image_file}: {str(e)}")
            continue


    print("-" * 50)
    print(f"Processing complete! Segmented images saved to: {output_folder}")


def main():
    parser = argparse.ArgumentParser(
        description="Segment runway model images using rembg (recursive)"
    )
    parser.add_argument(
        "input_folder",
        help="Path to root folder containing images"
    )
    parser.add_argument(
        "-o", "--output",
        default="output_segmented",
        help="Output root folder (default: output_segmented)"
    )
    parser.add_argument(
        "--alpha-matting",
        action="store_true",
        help="Enable alpha matting (slower, better edges)"
    )

    args = parser.parse_args()

    if not os.path.isdir(args.input_folder):
        print(f"Error: Input folder '{args.input_folder}' does not exist")
        return

    process_images(args.input_folder, args.output, args.alpha_matting)


if __name__ == "__main__":
    main()
