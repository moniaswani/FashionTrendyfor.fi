"""
Creates the DynamoDB tables for the NOWFASHION runway dataset
(runway_metadata_schema.xlsx: Looks + Items sheets).

These are NEW tables — separate from the existing `New_Fashion_Analysis`
table (which holds the old Bedrock-vision-derived data and is still used
by the live Lambdas / chatbot). Nothing here touches that table.

Tables:
    RunwayLooks   PK: look_id (S)
                  GSI: DesignerSeasonIndex  (designer_lower HASH, season_lower RANGE)
                  Stream: KEYS_ONLY — feeds lamdbas/regenerateRunwayCache,
                  which rebuilds the public runway_looks_index.json /
                  runway_facets.json cache on S3 whenever this table changes.

    RunwayItems   PK: look_id (S)  SK: item_index (N)
                  GSI: DesignerSeasonIndex  (designer_lower HASH, season_lower RANGE)
                  GSI: ColorItemIndex       (color HASH, item_name RANGE)

Run once — safe to re-run (skips tables that already exist, enables
streams on RunwayLooks if not already on).

Usage:
    python src/dynamodb_setup.py
"""

import os
import sys

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "eu-west-2")
_client = boto3.client("dynamodb", region_name=REGION)

TABLES = [
    {
        "TableName": "RunwayLooks",
        "AttributeDefinitions": [
            {"AttributeName": "look_id", "AttributeType": "S"},
            {"AttributeName": "designer_lower", "AttributeType": "S"},
            {"AttributeName": "season_lower", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "look_id", "KeyType": "HASH"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "DesignerSeasonIndex",
                "KeySchema": [
                    {"AttributeName": "designer_lower", "KeyType": "HASH"},
                    {"AttributeName": "season_lower", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "StreamSpecification": {
            "StreamEnabled": True,
            "StreamViewType": "KEYS_ONLY",
        },
    },
    {
        "TableName": "RunwayItems",
        "AttributeDefinitions": [
            {"AttributeName": "look_id", "AttributeType": "S"},
            {"AttributeName": "item_index", "AttributeType": "N"},
            {"AttributeName": "designer_lower", "AttributeType": "S"},
            {"AttributeName": "season_lower", "AttributeType": "S"},
            {"AttributeName": "color", "AttributeType": "S"},
            {"AttributeName": "item_name", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "look_id", "KeyType": "HASH"},
            {"AttributeName": "item_index", "KeyType": "RANGE"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "DesignerSeasonIndex",
                "KeySchema": [
                    {"AttributeName": "designer_lower", "KeyType": "HASH"},
                    {"AttributeName": "season_lower", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "ColorItemIndex",
                "KeySchema": [
                    {"AttributeName": "color", "KeyType": "HASH"},
                    {"AttributeName": "item_name", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


def create_tables() -> None:
    for schema in TABLES:
        name = schema["TableName"]
        try:
            _client.create_table(**schema)
            print(f"  Creating: {name} (waiting for ACTIVE...)")
            _client.get_waiter("table_exists").wait(TableName=name)
            print(f"  ✅ Active: {name}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"  Already exists: {name}")
            else:
                raise


def ensure_streams_enabled(table_name: str, view_type: str = "KEYS_ONLY") -> None:
    """Turns on a table's stream if it isn't already — needed for
    RunwayLooks, which was created (and fully loaded) before streams
    existed on it. No-op if streams are already on."""
    desc = _client.describe_table(TableName=table_name)["Table"]
    if desc.get("StreamSpecification", {}).get("StreamEnabled"):
        stream_arn = desc["LatestStreamArn"]
        print(f"  Streams already enabled: {table_name} ({stream_arn})")
        return

    _client.update_table(
        TableName=table_name,
        StreamSpecification={"StreamEnabled": True, "StreamViewType": view_type},
    )
    print(f"  Enabling streams on {table_name} (waiting for ACTIVE...)")
    _client.get_waiter("table_exists").wait(TableName=table_name)
    stream_arn = _client.describe_table(TableName=table_name)["Table"]["LatestStreamArn"]
    print(f"  ✅ Streams enabled: {table_name} ({stream_arn})")
    print("     Pass this as RunwayLooksStreamArn when deploying template.yaml.")


if __name__ == "__main__":
    print(f"Creating DynamoDB tables in {REGION}...")
    create_tables()
    ensure_streams_enabled("RunwayLooks")
    print("Done.")
    sys.exit(0)
