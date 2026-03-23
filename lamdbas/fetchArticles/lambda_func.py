import boto3
import json
import base64
from boto3.dynamodb.conditions import Key, Attr

REGION = "eu-west-2"
dynamodb = boto3.resource("dynamodb", region_name=REGION)
articles_table = dynamodb.Table("ArticleCache")
fashion_table = dynamodb.Table("New_Fashion_Analysis")


def get_representative_image(designer_hyphen: str, season: str):
    """
    Given article designer (e.g. "louis-vuitton") and season (e.g. "fall-2024"),
    return one original_image_name from New_Fashion_Analysis.
    """
    designer_lower = designer_hyphen.replace("-", " ")
    year = next((p for p in season.split("-") if p.isdigit()), None)
    try:
        resp = fashion_table.query(
            IndexName="DesignerSeasonIndex",
            KeyConditionExpression=Key("designer_lower").eq(designer_lower),
            Limit=20,
        )
        items = resp.get("Items", [])
        if year and items:
            matching = [i for i in items if year in i.get("season_lower", "")]
            if matching:
                return matching[0].get("original_image_name")
        if items:
            return items[0].get("original_image_name")
    except Exception:
        pass
    return None


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    params = event.get("queryStringParameters") or {}
    designer = params.get("designer", "").strip()
    season = params.get("season", "").strip()
    next_token = params.get("next_token")
    limit = min(int(params.get("limit", 20)), 100)

    filter_expr = Attr("parse_status").eq("ok")
    if designer:
        filter_expr &= Attr("designer").eq(designer)
    if season:
        filter_expr &= Attr("season").eq(season)

    scan_kwargs = {"FilterExpression": filter_expr, "Limit": limit}
    if next_token:
        try:
            scan_kwargs["ExclusiveStartKey"] = json.loads(
                base64.b64decode(next_token).decode("utf-8")
            )
        except Exception:
            pass

    resp = articles_table.scan(**scan_kwargs)
    items = resp.get("Items", [])

    # Enrich each article with a representative runway image (cached per designer+season)
    image_cache = {}
    for item in items:
        key = f"{item.get('designer', '')}#{item.get('season', '')}"
        if key not in image_cache:
            image_cache[key] = get_representative_image(
                item.get("designer", ""), item.get("season", "")
            )
        item["representative_image"] = image_cache[key]

    last_key = resp.get("LastEvaluatedKey")
    encoded_next = (
        base64.b64encode(json.dumps(last_key, default=str).encode("utf-8")).decode("utf-8")
        if last_key
        else None
    )

    return {
        "statusCode": 200,
        "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
        "body": json.dumps(
            {"items": items, "next_token": encoded_next, "count": len(items)},
            default=str,
        ),
    }
