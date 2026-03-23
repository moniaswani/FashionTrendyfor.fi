"""
DynamoDB client for the fashion agent.

Responsibilities:
    1. get_runway_data()       — query New_Fashion_Analysis via DesignerSeasonIndex GSI
    2. get/cache_article()     — read/write ArticleCache table
    3. get/cache_insights()    — read/write InsightsCache table

Season format mapping (agent input → DB season_lower):
    "fall-2023"   → "fall-winter-2023"
    "spring-2023" → "spring-summer-2023"

Required env vars:
    AWS_REGION   (default: eu-west-2)
    AWS credentials (standard boto3 chain: env vars, ~/.aws, instance role)
"""

import os
from collections import Counter
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "eu-west-2")
RUNWAY_TABLE = "New_Fashion_Analysis"
ARTICLE_CACHE_TABLE = "ArticleCache"
INSIGHTS_CACHE_TABLE = "InsightsCache"

_dynamodb = boto3.resource("dynamodb", region_name=REGION)
_runway = _dynamodb.Table(RUNWAY_TABLE)
_article_cache = _dynamodb.Table(ARTICLE_CACHE_TABLE)
_insights_cache = _dynamodb.Table(INSIGHTS_CACHE_TABLE)


# ── Season format helpers ─────────────────────────────────────────────────────

def _to_db_season(season: str) -> str:
    """
    Convert agent-facing season slug to the DB's season_lower format.

    "fall-2023"   → "fall-winter-2023"
    "spring-2023" → "spring-summer-2023"
    """
    year = season.split("-")[1]
    if season.startswith("fall-"):
        return f"fall-winter-{year}"
    if season.startswith("spring-"):
        return f"spring-summer-{year}"
    return season


# ── Runway data ───────────────────────────────────────────────────────────────

def get_runway_data(designer: str, season: str) -> dict:
    """
    Query New_Fashion_Analysis via DesignerSeasonIndex GSI and aggregate
    top colors, items, and materials for the collection.

    Args:
        designer: slug e.g. "chanel"
        season:   agent format e.g. "spring-2023", "fall-2023"

    Returns:
        {
            found: bool,
            designer, season, season_lower,
            total_looks: int,
            top_colors:    [{name, hex, count}],   # top 5
            top_items:     [{name, count}],         # top 5
            top_materials: [{name, count}],         # top 5
        }
    """
    designer_lower = designer.lower().replace("-", " ")
    season_lower = _to_db_season(season)

    items = []
    kwargs = {
        "IndexName": "DesignerSeasonIndex",
        "KeyConditionExpression": (
            Key("designer_lower").eq(designer_lower)
            & Key("season_lower").eq(season_lower)
        ),
    }

    # Paginate through all results
    while True:
        resp = _runway.query(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    if not items:
        return {
            "found": False,
            "designer": designer,
            "season": season,
            "season_lower": season_lower,
            "total_looks": 0,
        }

    color_counts: Counter = Counter()
    color_hex_map: dict = {}
    item_counts: Counter = Counter()
    material_counts: Counter = Counter()

    for item in items:
        color = item.get("color_name", "").strip()
        if color:
            color_counts[color] += 1
            color_hex_map[color] = item.get("color_hex", "")

        item_name = item.get("item_name", "").strip()
        if item_name:
            item_counts[item_name] += 1

        material = item.get("materials", "").strip()
        if material:
            material_counts[material] += 1

    return {
        "found": True,
        "designer": designer,
        "season": season,
        "season_lower": season_lower,
        "total_looks": len(items),
        "top_colors": [
            {"name": name, "hex": color_hex_map.get(name, ""), "count": count}
            for name, count in color_counts.most_common(5)
        ],
        "top_items": [
            {"name": name, "count": count}
            for name, count in item_counts.most_common(5)
        ],
        "top_materials": [
            {"name": name, "count": count}
            for name, count in material_counts.most_common(5)
        ],
    }


# ── Article cache ─────────────────────────────────────────────────────────────

def _article_key(source: str, designer: str, season: str) -> str:
    return f"{source}#{designer}#{season}"


def get_cached_article(source: str, designer: str, season: str) -> dict | None:
    """Returns cached article dict or None if not cached."""
    try:
        resp = _article_cache.get_item(Key={"cache_key": _article_key(source, designer, season)})
        return resp.get("Item")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("  [warn] ArticleCache table not found. Run: python cache_schema.py")
            return None
        raise


def cache_article(source: str, designer: str, season: str, article: dict) -> None:
    """Writes an article to ArticleCache. Only stores articles with parse_status='ok'."""
    if article.get("parse_status") != "ok":
        return
    try:
        _article_cache.put_item(Item={
            "cache_key": _article_key(source, designer, season),
            "cached_at": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in article.items() if v is not None},
        })
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("  [warn] ArticleCache table not found — skipping cache write. Run: python cache_schema.py")
            return
        raise


# ── Insights cache ────────────────────────────────────────────────────────────

def _insights_key(designer: str, season: str) -> str:
    return f"{designer}#{season}"


def get_cached_insights(designer: str, season: str) -> dict | None:
    """Returns cached insights dict or None if not cached."""
    try:
        resp = _insights_cache.get_item(Key={"cache_key": _insights_key(designer, season)})
        return resp.get("Item")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("  [warn] InsightsCache table not found. Run: python cache_schema.py")
            return None
        raise


def cache_insights(designer: str, season: str, insights: dict) -> None:
    """Writes synthesized insights to InsightsCache."""
    try:
        _insights_cache.put_item(Item={
            "cache_key": _insights_key(designer, season),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in insights.items() if v is not None},
        })
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("  [warn] InsightsCache table not found — skipping cache write. Run: python cache_schema.py")
            return
        raise
