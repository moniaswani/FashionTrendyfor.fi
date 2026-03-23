"""
Creates the two DynamoDB cache tables used by the fashion agent.
Run once before first use — safe to re-run (skips existing tables).

Tables:
    ArticleCache   PK: cache_key = "{source}#{designer}#{season}"
    InsightsCache  PK: cache_key = "{designer}#{season}"

Usage:
    python cache_schema.py
"""

import os
import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "eu-west-2")
dynamodb = boto3.client("dynamodb", region_name=REGION)

TABLES = [
    {
        "TableName": "ArticleCache",
        "AttributeDefinitions": [{"AttributeName": "cache_key", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "cache_key", "KeyType": "HASH"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "InsightsCache",
        "AttributeDefinitions": [{"AttributeName": "cache_key", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "cache_key", "KeyType": "HASH"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


def create_tables() -> None:
    for schema in TABLES:
        name = schema["TableName"]
        try:
            dynamodb.create_table(**schema)
            print(f"  Created: {name}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"  Already exists: {name}")
            else:
                raise


if __name__ == "__main__":
    print(f"Creating DynamoDB tables in {REGION}...")
    create_tables()
    print("Done.")
