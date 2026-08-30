"""
One-time backfill: adds item_names/colors/materials to every existing
RunwayLooks row by aggregating from RunwayItems, matching the
denormalization src/excel_to_dynamodb.py now does at write time for new
data (see that file's derive_look_facets()). Needed because RunwayLooks
was already fully loaded (16,464 rows) before those fields existed.

Each RunwayLooks update here also lands in the table's DynamoDB Stream
(see src/dynamodb_setup.py's ensure_streams_enabled), so running this
after regenerateRunwayCache is deployed is what populates the S3 cache
for the first time.

Safe to re-run — every row is just overwritten with freshly computed
values.

Usage:
    python src/backfill_runway_looks_facets.py --dry-run
    python src/backfill_runway_looks_facets.py
"""

import argparse
import os

import boto3
from boto3.dynamodb.conditions import Key

REGION = os.environ.get("AWS_REGION", "eu-west-2")
LOOKS_TABLE = "RunwayLooks"
ITEMS_TABLE = "RunwayItems"


def derive_facets(item_rows: list[dict]) -> dict:
    item_names = sorted({r["item_name"] for r in item_rows if r.get("item_name")})
    colors = sorted({r["color"] for r in item_rows if r.get("color")})
    materials = sorted({r["material"] for r in item_rows if r.get("material")})
    return {"item_names": item_names, "colors": colors, "materials": materials}


def backfill(dry_run: bool = False) -> dict:
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    looks_table = dynamodb.Table(LOOKS_TABLE)
    items_table = dynamodb.Table(ITEMS_TABLE)

    report = {"looks_scanned": 0, "looks_updated": 0}

    scan_kwargs = {"ProjectionExpression": "look_id"}
    while True:
        page = looks_table.scan(**scan_kwargs)
        for row in page["Items"]:
            look_id = row["look_id"]
            report["looks_scanned"] += 1

            item_rows = items_table.query(
                KeyConditionExpression=Key("look_id").eq(look_id)
            )["Items"]
            facets = derive_facets(item_rows)

            if not dry_run:
                looks_table.update_item(
                    Key={"look_id": look_id},
                    UpdateExpression="SET item_names = :n, colors = :c, materials = :m",
                    ExpressionAttributeValues={
                        ":n": facets["item_names"],
                        ":c": facets["colors"],
                        ":m": facets["materials"],
                    },
                )
            report["looks_updated"] += 1

            if report["looks_scanned"] % 500 == 0:
                print(f"  ...{report['looks_scanned']} scanned")

        if "LastEvaluatedKey" not in page:
            break
        scan_kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Scan & compute only, no writes")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else f"LIVE (writing to {LOOKS_TABLE} in {REGION})"
    print(f"Backfilling item_names/colors/materials onto RunwayLooks [{mode}]...")

    report = backfill(dry_run=args.dry_run)

    print()
    print(f"Looks scanned: {report['looks_scanned']}")
    print(f"Looks updated: {report['looks_updated']}")


if __name__ == "__main__":
    main()
