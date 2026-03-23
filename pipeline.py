#!/usr/bin/env python3
"""
Pipeline: scrape runway images → segment models out of background.

Skips any season folder that already exists in S3 (runwayimages bucket).

Steps:
  1. Resolve which URLs map to folders NOT yet in S3
  2. webscrapper.py  — downloads only new folders into images/
  3. runway_segmentation.py — removes backgrounds, saves to segmented/

Run from project root:
    python pipeline.py
    python pipeline.py --skip-scrape     # only segment already-downloaded images
    python pipeline.py --skip-segment    # only scrape
    python pipeline.py --alpha-matting   # higher quality segmentation (slower)
    python pipeline.py --dry-run         # just show what would be skipped/processed
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

SRC = Path(__file__).parent / "src"
URLS_FILE = Path(__file__).parent / "urls.txt"
IMAGES_DIR = Path(__file__).parent / "images"
SEGMENTED_DIR = Path(__file__).parent / "segmented"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}

S3_BUCKET = "runwayimages"
S3_REGION = "eu-west-2"


# ── Helpers ───────────────────────────────────────────────────────────────────

def url_to_folder_name(url: str) -> str:
    """Mirrors the folder-naming logic in webscrapper.py."""
    parsed = urlparse(url)
    path_after = parsed.path.strip("/") or parsed.netloc
    return path_after.replace("/", "-")


def count_images(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in IMAGE_EXTS)


def count_segmented(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for f in folder.rglob("*") if f.is_file() and f.name.endswith("_segmented.png"))


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── S3 check ──────────────────────────────────────────────────────────────────

def get_s3_folders(bucket: str, region: str) -> set[str]:
    """Return set of top-level folder prefixes already in the bucket."""
    s3 = boto3.client("s3", region_name=region)
    prefixes = set()
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Delimiter="/"):
            for cp in page.get("CommonPrefixes", []):
                # strip trailing slash: "louis-vuitton-fall-winter-2021-paris/"
                prefixes.add(cp["Prefix"].rstrip("/"))
    except ClientError as e:
        print(f"  [warn] Could not list S3 bucket ({e}) — treating all URLs as new")
    return prefixes


def resolve_new_urls(urls: list[str], s3_folders: set[str]) -> tuple[list[str], list[str]]:
    """Split URLs into (new, already_in_s3)."""
    new, existing = [], []
    for url in urls:
        folder = url_to_folder_name(url)
        if folder in s3_folders:
            existing.append(url)
        else:
            new.append(url)
    return new, existing


# ── Steps ─────────────────────────────────────────────────────────────────────

def run_scraper(new_urls: list[str], dry_run: bool) -> bool:
    print_section("STEP 1 — Scraping new runway images")

    if not new_urls:
        print("  Nothing to scrape — all URLs already exist in S3.")
        return True

    print(f"  URLs to scrape: {len(new_urls)}")
    for u in new_urls:
        print(f"    {u}")

    if dry_run:
        print("\n  [dry-run] Skipping actual scrape.")
        return True

    # Write a temp urls file containing only the new URLs
    tmp_urls = Path(__file__).parent / "_tmp_urls.txt"
    tmp_urls.write_text("\n".join(new_urls) + "\n")

    images_before = count_images(IMAGES_DIR)
    t0 = time.time()

    # webscrapper reads "urls.txt" from cwd, so point it at our tmp file via env
    # Easier: just swap urls.txt temporarily, or pass via stdin — simplest is
    # to write a fresh urls.txt for this run (we already wrote the full one; swap):
    original_urls_backup = URLS_FILE.read_text()
    URLS_FILE.write_text("\n".join(new_urls) + "\n")

    try:
        result = subprocess.run(
            [sys.executable, str(SRC / "webscrapper.py")],
            cwd=Path(__file__).parent,
        )
    finally:
        URLS_FILE.write_text(original_urls_backup)
        tmp_urls.unlink(missing_ok=True)

    elapsed = time.time() - t0
    images_after = count_images(IMAGES_DIR)

    print(f"\n  --- Scrape summary ---")
    print(f"  Exit code    : {result.returncode}")
    print(f"  Time         : {elapsed:.1f}s")
    print(f"  New images   : {images_after - images_before}")
    print(f"  Total in images/ : {images_after}")
    return result.returncode == 0


def run_segmentation(new_urls: list[str], alpha_matting: bool, dry_run: bool) -> bool:
    print_section("STEP 2 — Segmenting new runway images")

    # Only segment folders that correspond to new URLs
    new_folders = [IMAGES_DIR / url_to_folder_name(u) for u in new_urls]
    existing_new = [f for f in new_folders if f.exists() and count_images(f) > 0]

    if not existing_new:
        print("  No new image folders to segment.")
        return True

    print(f"  Folders to segment: {len(existing_new)}")
    for f in existing_new:
        print(f"    {f.name}  ({count_images(f)} images)")

    if dry_run:
        print("\n  [dry-run] Skipping actual segmentation.")
        return True

    seg_before = count_segmented(SEGMENTED_DIR)
    t0 = time.time()
    all_ok = True

    for folder in existing_new:
        rel = folder.relative_to(IMAGES_DIR)
        out_folder = SEGMENTED_DIR / rel
        cmd = [
            sys.executable,
            str(SRC / "runway_segmentation.py"),
            str(folder),
            "-o", str(out_folder),
        ]
        if alpha_matting:
            cmd.append("--alpha-matting")

        print(f"\n  Processing: {folder.name}")
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        if result.returncode != 0:
            all_ok = False

    elapsed = time.time() - t0
    seg_after = count_segmented(SEGMENTED_DIR)

    print(f"\n  --- Segmentation summary ---")
    print(f"  Time            : {elapsed:.1f}s")
    print(f"  Newly segmented : {seg_after - seg_before}")
    print(f"  Total segmented : {seg_after}")
    return all_ok


def print_final_status(new_urls: list[str], skipped_urls: list[str]):
    print_section("PIPELINE COMPLETE — Final status")

    print(f"  Skipped (already in S3) : {len(skipped_urls)}")
    for u in skipped_urls:
        print(f"    ✓ {url_to_folder_name(u)}")

    print(f"\n  Processed this run      : {len(new_urls)}")
    header = f"  {'Folder':<55} {'imgs':>5}  {'segs':>5}"
    print(header)
    print(f"  {'-'*55} {'-----':>5}  {'-----':>5}")
    for url in new_urls:
        name = url_to_folder_name(url)
        img_dir = IMAGES_DIR / name
        seg_dir = SEGMENTED_DIR / name
        n_imgs = count_images(img_dir)
        n_segs = count_segmented(seg_dir)
        status = "✓" if n_segs >= n_imgs > 0 else ("⚠" if n_imgs == 0 else "…")
        print(f"  {status} {name:<54} {n_imgs:>5}  {n_segs:>5}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Runway scrape + segmentation pipeline (S3-aware)")
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-segment", action="store_true")
    parser.add_argument("--alpha-matting", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without doing it")
    args = parser.parse_args()

    t_total = time.time()

    # Load all URLs
    all_urls = [
        l.strip() for l in URLS_FILE.read_text().splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    print(f"\n  Loaded {len(all_urls)} URLs from urls.txt")

    # Check S3 for already-uploaded folders
    print("  Checking S3 bucket for existing folders...")
    s3_folders = get_s3_folders(S3_BUCKET, S3_REGION)
    print(f"  Found {len(s3_folders)} existing folders in s3://{S3_BUCKET}/")

    new_urls, skipped_urls = resolve_new_urls(all_urls, s3_folders)
    print(f"  → {len(skipped_urls)} already in S3 (will skip)")
    print(f"  → {len(new_urls)} new (will process)")

    scrape_ok = True
    if not args.skip_scrape:
        scrape_ok = run_scraper(new_urls, args.dry_run)

    seg_ok = True
    if not args.skip_segment:
        seg_ok = run_segmentation(new_urls, args.alpha_matting, args.dry_run)

    print_final_status(new_urls, skipped_urls)

    print(f"\n  Total pipeline time: {time.time() - t_total:.1f}s\n")
    sys.exit(0 if (scrape_ok and seg_ok) else 1)


if __name__ == "__main__":
    main()
