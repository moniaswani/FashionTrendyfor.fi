#!/usr/bin/env python3
"""
BUG-01 migration: fix original_image_name in DynamoDB to exactly match S3 object keys.

The ingestion script previously called .capitalize() on every hyphenated word, which
corrupted brand names like "Comme-des-Garcons" → "Comme-Des-Garcons". S3 object keys
are case-sensitive, so mismatched casing means images never load.

What this script does:
  1. Lists every object in the S3 bucket and builds a lookup:
       lowercase_key → actual_key   (e.g. "comme-des-garcons-..." → "Comme-des-Garcons-...")
  2. Scans the entire DynamoDB table
  3. For each record whose original_image_name doesn't match the real S3 key, updates it

Run:
    python src/fix_image_names.py [--dry-run]
"""

import argparse
import boto3
from botocore.exceptions import ClientError

REGION = "eu-west-2"
BUCKET = "runwayimages"
TABLE = "New_Fashion_Analysis"

s3 = boto3.client("s3", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE)


def build_s3_key_map() -> dict[str, str]:
    """Return {lowercase_basename: actual_s3_key_basename} for every object in the bucket."""
    print(f"Listing all objects in s3://{BUCKET} …")
    key_map: dict[str, str] = {}
    paginator = s3.get_paginator("list_objects_v2")
    count = 0
    for page in paginator.paginate(Bucket=BUCKET):
        for obj in page.get("Contents", []):
            full_key = obj["Key"]
            basename = full_key.split("/")[-1]
            key_map[basename.lower()] = basename
            count += 1
    print(f"  Found {count} S3 objects, {len(key_map)} unique basenames\n")
    return key_map


def scan_all_items() -> list[dict]:
    print("Scanning DynamoDB table …")
    items = []
    kwargs: dict = {"ProjectionExpression": "image_id, original_image_name"}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    print(f"  Found {len(items)} records\n")
    return items


def fix_image_names(dry_run: bool = False):
    key_map = build_s3_key_map()
    items = scan_all_items()

    needs_fix = []
    not_in_s3 = []

    for item in items:
        stored = item.get("original_image_name", "")
        if not stored:
            continue
        actual = key_map.get(stored.lower())
        if actual is None:
            not_in_s3.append(stored)
        elif actual != stored:
            needs_fix.append((item["image_id"], stored, actual))

    print(f"Records needing correction : {len(needs_fix)}")
    print(f"Records with no S3 match   : {len(not_in_s3)}")

    if not_in_s3:
        print("\nNo S3 match (sample, first 10):")
        for name in not_in_s3[:10]:
            print(f"  {name}")

    if not needs_fix:
        print("\nNothing to fix — all original_image_name values match S3.")
        return

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixing {len(needs_fix)} records …\n")
    fixed = 0
    errors = 0
    for image_id, wrong, correct in needs_fix:
        print(f"  {wrong}  →  {correct}")
        if dry_run:
            continue
        try:
            table.update_item(
                Key={"image_id": image_id},
                UpdateExpression="SET original_image_name = :v",
                ExpressionAttributeValues={":v": correct},
            )
            fixed += 1
        except ClientError as e:
            print(f"    ERROR: {e}")
            errors += 1

    if not dry_run:
        print(f"\nDone. Fixed: {fixed}  Errors: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix original_image_name casing in DynamoDB")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()
    fix_image_names(dry_run=args.dry_run)
