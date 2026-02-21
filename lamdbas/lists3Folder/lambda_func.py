import boto3
import json
import re

s3 = boto3.client("s3")
BUCKET = "runwayimages"

def lambda_handler(event, context):
    response = s3.list_objects_v2(Bucket=BUCKET, Delimiter='/')
    folders = [prefix["Prefix"].rstrip("/") for prefix in response.get("CommonPrefixes", [])]
    
    folder_map = {}

    for folder in folders:
        # Example folder: "chanel-ready-to-wear-fall-winter-2025-paris"
        parts = folder.split("-")

        # Find the index where "ready" or "readyto" appears — start of "ready-to-wear"
        ready_index = next((i for i, p in enumerate(parts) if "ready" in p), None)

        if ready_index:
            # Brand = everything before "ready"
            brand = " ".join(parts[:ready_index])
        else:
            # If "ready" not found, take the first two words as brand fallback
            brand = " ".join(parts[:2])

        # Season = everything after "ready-to-wear"
        season_parts = parts[ready_index + 3:] if ready_index is not None else parts[2:]
        season = "-".join(season_parts)

        brand = brand.replace("-", " ").strip().lower()
        season = season.strip().lower()

        if brand not in folder_map:
            folder_map[brand] = {}

        folder_map[brand][season] = folder

    return {
    "statusCode": 200,
    "headers": {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,GET"
    },
    "body": json.dumps(folder_map)
    }
