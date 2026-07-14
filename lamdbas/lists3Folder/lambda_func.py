import boto3
import json

s3 = boto3.client("s3")
BUCKET = "runwayimages"


def _canonical_brand(brand: str) -> str:
    """
    Normalize a brand string to a canonical form used for near-duplicate detection.
    Strips spaces, hyphens, and lowercases everything.
    e.g. "dolce gabbana" and "dolcegabbana" both → "dolcegabbana"
    """
    return brand.lower().replace(" ", "").replace("-", "")


def lambda_handler(event, context):
    paginator = s3.get_paginator("list_objects_v2")
    folders = []
    for page in paginator.paginate(Bucket=BUCKET, Delimiter="/"):
        for prefix in page.get("CommonPrefixes", []):
            folders.append(prefix["Prefix"].rstrip("/"))

    # raw_map: brand_key -> {season -> folder}  (before merging)
    raw_map: dict[str, dict[str, str]] = {}

    for folder in folders:
        parts = folder.split("-")

        ready_index = next((i for i, p in enumerate(parts) if p == "ready"), None)

        if ready_index:
            brand = " ".join(parts[:ready_index])
            season_parts = parts[ready_index + 3:]  # skip "ready", "to", "wear"
        else:
            brand = " ".join(parts[:2])
            season_parts = parts[2:]

        brand = brand.replace("-", " ").strip().lower()
        season = "-".join(season_parts).strip().lower()

        if brand not in raw_map:
            raw_map[brand] = {}
        raw_map[brand][season] = folder

    # Merge near-duplicate brand keys (e.g. "dolcegabbana" → "dolce gabbana").
    # Rule: if two brand keys collapse to the same canonical form, keep the one
    # with spaces (more human-readable / historically correct) and merge all seasons.
    canonical_to_spaced: dict[str, str] = {}  # canonical → preferred brand key
    folder_map: dict[str, dict[str, str]] = {}

    for brand, seasons in sorted(raw_map.items()):
        canon = _canonical_brand(brand)
        if canon in canonical_to_spaced:
            preferred = canonical_to_spaced[canon]
            # Merge seasons into the preferred key (existing seasons win on conflict)
            for season, folder in seasons.items():
                folder_map[preferred].setdefault(season, folder)
        else:
            # Pick the spaced variant as canonical if both exist later; for now register this one
            canonical_to_spaced[canon] = brand
            folder_map[brand] = dict(seasons)

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(folder_map),
    }
