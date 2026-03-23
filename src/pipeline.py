#!/usr/bin/env python3
"""
Pipeline: scrape runway images → segment models out of background.

Steps:
  1. webscrapper.py  — downloads images from urls.txt into images/
  2. runway_segmentation.py — removes backgrounds, saves to segmented/

Run from project root:
    python pipeline.py
    python pipeline.py --skip-scrape     # only segment already-downloaded images
    python pipeline.py --skip-segment    # only scrape
    python pipeline.py --alpha-matting   # higher quality segmentation (slower)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

SRC = Path(__file__).parent          # scripts live alongside this file in src/
URLS_FILE = Path(__file__).parent / "urls.txt"
IMAGES_DIR = Path(__file__).parent / "images"
SEGMENTED_DIR = Path(__file__).parent / "segmented"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


def count_images(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in IMAGE_EXTS)


def count_segmented(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*") if f.is_file() and f.name.endswith("_segmented.png"))


def print_section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def run_scraper() -> bool:
    print_section("STEP 1 — Scraping runway images")

    urls = [l.strip() for l in URLS_FILE.read_text().splitlines()
            if l.strip() and not l.strip().startswith("#")]
    print(f"  URLs loaded: {len(urls)}")
    print(f"  Output dir : {IMAGES_DIR}/\n")

    images_before = count_images(IMAGES_DIR)
    t0 = time.time()

    result = subprocess.run(
        [sys.executable, str("webscrapper.py")],
        cwd=Path(__file__).parent,
        capture_output=False,   # stream output live
    )

    elapsed = time.time() - t0
    images_after = count_images(IMAGES_DIR)
    new_images = images_after - images_before

    print(f"\n  --- Scrape summary ---")
    print(f"  Exit code    : {result.returncode}")
    print(f"  Time         : {elapsed:.1f}s")
    print(f"  Images before: {images_before}")
    print(f"  Images after : {images_after}")
    print(f"  New downloads: {new_images}")

    return result.returncode == 0


def run_segmentation(alpha_matting: bool) -> bool:
    print_section("STEP 2 — Segmenting runway images")

    images_in = count_images(IMAGES_DIR)
    seg_before = count_segmented(SEGMENTED_DIR)

    print(f"  Input dir  : {IMAGES_DIR}/  ({images_in} images)")
    print(f"  Output dir : {SEGMENTED_DIR}/")
    print(f"  Alpha matting: {'yes (slower, higher quality)' if alpha_matting else 'no'}\n")

    cmd = [
        sys.executable,
        str(SRC / "runway_segmentation.py"),
        str(IMAGES_DIR),
        "-o", str(SEGMENTED_DIR),
    ]
    if alpha_matting:
        cmd.append("--alpha-matting")

    t0 = time.time()
    result = subprocess.run(cmd, cwd=Path(__file__).parent, capture_output=False)
    elapsed = time.time() - t0

    seg_after = count_segmented(SEGMENTED_DIR)
    new_segs = seg_after - seg_before

    print(f"\n  --- Segmentation summary ---")
    print(f"  Exit code       : {result.returncode}")
    print(f"  Time            : {elapsed:.1f}s")
    print(f"  Segmented before: {seg_before}")
    print(f"  Segmented after : {seg_after}")
    print(f"  Newly processed : {new_segs}")

    return result.returncode == 0


def print_final_status():
    print_section("PIPELINE COMPLETE — Final status")

    images = count_images(IMAGES_DIR)
    segmented = count_segmented(SEGMENTED_DIR)

    # Per-season breakdown
    if IMAGES_DIR.exists():
        seasons = sorted([d for d in IMAGES_DIR.iterdir() if d.is_dir()])
        if seasons:
            print(f"  {'Season folder':<55} {'imgs':>5}  {'segs':>5}")
            print(f"  {'-'*55} {'-----':>5}  {'-----':>5}")
            for season_dir in seasons:
                n_imgs = sum(1 for f in season_dir.rglob("*")
                             if f.is_file() and f.suffix.lower() in IMAGE_EXTS)
                # matching segmented subfolder
                rel = season_dir.relative_to(IMAGES_DIR)
                seg_dir = SEGMENTED_DIR / rel
                n_segs = sum(1 for f in seg_dir.rglob("*")
                             if f.is_file() and f.name.endswith("_segmented.png")) if seg_dir.exists() else 0
                status = "✓" if n_segs >= n_imgs and n_imgs > 0 else ("⚠" if n_imgs == 0 else "…")
                name = str(rel)[:55]
                print(f"  {status} {name:<54} {n_imgs:>5}  {n_segs:>5}")

    print(f"\n  Total images downloaded : {images}")
    print(f"  Total images segmented  : {segmented}")
    coverage = f"{segmented/images*100:.1f}%" if images else "N/A"
    print(f"  Segmentation coverage   : {coverage}")


def main():
    parser = argparse.ArgumentParser(description="Runway image scrape + segmentation pipeline")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping step")
    parser.add_argument("--skip-segment", action="store_true", help="Skip segmentation step")
    parser.add_argument("--alpha-matting", action="store_true", help="Enable alpha matting in rembg")
    args = parser.parse_args()

    t_total = time.time()

    scrape_ok = True
    if not args.skip_scrape:
        scrape_ok = run_scraper()
        if not scrape_ok:
            print("\n  [warn] Scraper exited with errors — continuing to segmentation anyway")

    seg_ok = True
    if not args.skip_segment:
        if count_images(IMAGES_DIR) == 0:
            print("\n  [skip] No images in images/ — skipping segmentation")
        else:
            seg_ok = run_segmentation(args.alpha_matting)

    print_final_status()

    total_elapsed = time.time() - t_total
    print(f"\n  Total pipeline time: {total_elapsed:.1f}s")
    print()

    sys.exit(0 if (scrape_ok and seg_ok) else 1)


if __name__ == "__main__":
    main()
