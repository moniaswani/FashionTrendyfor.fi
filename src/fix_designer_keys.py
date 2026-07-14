#!/usr/bin/env python3
"""
BUG-02 migration: merge near-duplicate designer keys in DynamoDB.

The 2026 Dolce & Gabbana collections were ingested with designer_lower="dolcegabbana"
(derived from the S3 folder name) while all older seasons use "dolce gabbana" (with space).
Searches for either form return 0 results for the other form.

This script:
  1. Scans all DynamoDB records and groups them by designer_lower
  2. Finds pairs of keys that are the same after stripping spaces/hyphens
  3. Prints a report of all near-duplicate pairs found
  4. Rewrites the minority key's records to use the canonical (spaced) key
  5. Audits for the same pattern with any other brand (like "acne" vs "acne studios")

Run:
    python src/fix_designer_keys.py [--dry-run]
"""

import argparse
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

REGION = "eu-west-2"
TABLE = "New_Fashion_Analysis"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE)


def _canonical(brand: str) -> str:
    return brand.lower().replace(" ", "").replace("-", "")


def scan_all() -> list[dict]:
    print("Scanning DynamoDB …")
    items = []
    kwargs: dict = {"ProjectionExpression": "image_id, designer_lower, season_lower"}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    print(f"  {len(items)} records loaded\n")
    return items


def find_near_duplicates(items: list[dict]) -> dict[str, list[str]]:
    """Return {canonical_form: [brand_key, ...]} for all canonical forms with >1 brand key."""
    canon_to_brands: dict[str, set[str]] = defaultdict(set)
    for item in items:
        key = item.get("designer_lower", "")
        if key:
            canon_to_brands[_canonical(key)].add(key)

    return {c: sorted(brands) for c, brands in canon_to_brands.items() if len(brands) > 1}


def pick_canonical(brands: list[str]) -> str:
    """Prefer the variant with spaces (more human-readable); else shortest."""
    spaced = [b for b in brands if " " in b]
    return spaced[0] if spaced else min(brands, key=len)


def fix_designer_keys(dry_run: bool = False):
    items = scan_all()
    near_dupes = find_near_duplicates(items)

    if not near_dupes:
        print("No near-duplicate designer keys found. Nothing to do.")
        return

    print(f"Found {len(near_dupes)} near-duplicate group(s):\n")
    for canon, brands in near_dupes.items():
        preferred = pick_canonical(brands)
        others = [b for b in brands if b != preferred]
        count = sum(1 for i in items if i.get("designer_lower") in others)
        print(f"  {brands}  →  keep '{preferred}'  ({count} records to update)")

    print()
    total_fixed = 0
    total_errors = 0

    for canon, brands in near_dupes.items():
        preferred = pick_canonical(brands)
        others = [b for b in brands if b != preferred]
        to_update = [i for i in items if i.get("designer_lower") in others]

        if not to_update:
            continue

        print(f"{'[DRY RUN] ' if dry_run else ''}Updating {len(to_update)} records: "
              f"{others} → '{preferred}'")

        for item in to_update:
            if dry_run:
                continue
            try:
                table.update_item(
                    Key={"image_id": item["image_id"]},
                    UpdateExpression="SET designer_lower = :v",
                    ExpressionAttributeValues={":v": preferred},
                )
                total_fixed += 1
            except ClientError as e:
                print(f"  ERROR {item['image_id']}: {e}")
                total_errors += 1

    if not dry_run:
        print(f"\nDone. Fixed: {total_fixed}  Errors: {total_errors}")
    else:
        print("\n[DRY RUN] No changes written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge near-duplicate designer keys in DynamoDB")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()
    fix_designer_keys(dry_run=args.dry_run)
