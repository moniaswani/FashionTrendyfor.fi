import json
import boto3
import time
import datetime
from pytrends.request import TrendReq
from botocore.exceptions import ClientError

RUNWAY_BUCKET = "runwayimages"
CACHE_BUCKET = "fashion-trends-cache"
CACHE_KEY = "designer_trends.json"
CACHE_TTL_HOURS = 24
REGION = "eu-west-2"

s3 = boto3.client("s3", region_name=REGION)


def get_cached_data():
    """Return parsed JSON from S3 if fresh (< CACHE_TTL_HOURS old), else None."""
    try:
        obj = s3.get_object(Bucket=CACHE_BUCKET, Key=CACHE_KEY)
        data = json.loads(obj["Body"].read())
        updated_at = datetime.datetime.fromisoformat(
            data["updated_at"].replace("Z", "+00:00")
        )
        age_hours = (
            datetime.datetime.now(tz=datetime.timezone.utc) - updated_at
        ).total_seconds() / 3600
        if age_hours < CACHE_TTL_HOURS:
            return data
        return None
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def get_designers_from_s3():
    """
    List folders in the runwayimages bucket and extract unique brand names
    using the same parsing logic as the lists3Folder lambda.
    Returns a sorted list of lowercase brand name strings.
    """
    response = s3.list_objects_v2(Bucket=RUNWAY_BUCKET, Delimiter="/")
    folders = [
        prefix["Prefix"].rstrip("/")
        for prefix in response.get("CommonPrefixes", [])
    ]

    brands = set()
    for folder in folders:
        parts = folder.split("-")
        ready_index = next(
            (i for i, p in enumerate(parts) if "ready" in p), None
        )
        if ready_index:
            brand = " ".join(parts[:ready_index])
        else:
            brand = " ".join(parts[:2])
        brand = brand.replace("-", " ").strip().lower()
        if brand:
            brands.add(brand)

    return sorted(brands)


def fetch_trends_for_designers(designers):
    """
    Query Google Trends for each designer (in batches of 5).
    Timeframe: last 5 years, worldwide.
    Returns: { "chanel": [{"date": "2021-02", "value": 72}, ...], ... }
    """
    results = {}
    batches = [designers[i : i + 5] for i in range(0, len(designers), 5)]

    pytrends = TrendReq(
        hl="en-US",
        tz=0,
        timeout=(10, 25),
        retries=2,
        backoff_factor=2,
        requests_args={"verify": True},
    )

    for batch in batches:
        attempt = 0
        max_attempts = 5
        base_delay = 5

        while attempt < max_attempts:
            try:
                pytrends.build_payload(
                    batch,
                    cat=0,
                    timeframe="today 5-y",
                    geo="",
                    gprop="",
                )
                interest_df = pytrends.interest_over_time()

                if interest_df.empty:
                    for keyword in batch:
                        results[keyword] = []
                    break

                if "isPartial" in interest_df.columns:
                    interest_df = interest_df.drop(columns=["isPartial"])

                for keyword in batch:
                    if keyword in interest_df.columns:
                        series = interest_df[keyword]
                        results[keyword] = [
                            {
                                "date": str(idx)[:7],  # "YYYY-MM"
                                "value": int(val),
                            }
                            for idx, val in series.items()
                        ]
                    else:
                        results[keyword] = []

                # Polite delay between batches
                time.sleep(2)
                break

            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = (
                    "429" in error_str
                    or "too many" in error_str
                    or "response" in error_str
                    or "quota" in error_str
                )
                attempt += 1
                if is_rate_limit and attempt < max_attempts:
                    # Exponential backoff with jitter
                    wait = base_delay * (2 ** attempt) + (time.time() % 1)
                    print(
                        f"[GoogleTrends] Rate limited on batch {batch}, "
                        f"retrying in {wait:.1f}s (attempt {attempt}/{max_attempts})"
                    )
                    time.sleep(wait)
                else:
                    print(f"[GoogleTrends] Error for batch {batch}: {e}")
                    for keyword in batch:
                        results.setdefault(keyword, [])
                    break

    return results


def save_to_s3(data):
    s3.put_object(
        Bucket=CACHE_BUCKET,
        Key=CACHE_KEY,
        Body=json.dumps(data, default=str),
        ContentType="application/json",
    )


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    try:
        # 1. Serve from cache if fresh
        cached = get_cached_data()
        if cached:
            print(f"[GoogleTrends] Serving {len(cached.get('designers', {}))} designers from cache")
            return build_response(200, cached)

        # 2. Get designer list from S3 runway folders
        print("[GoogleTrends] Cache miss or stale — rebuilding")
        designers = get_designers_from_s3()
        print(f"[GoogleTrends] Found {len(designers)} unique designers: {designers}")

        if not designers:
            return build_response(200, {
                "updated_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                "designers": {},
            })

        # 3. Fetch from Google Trends
        trends_data = fetch_trends_for_designers(designers)

        # 4. Build and save payload
        payload = {
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            "designers": trends_data,
        }
        save_to_s3(payload)
        print(f"[GoogleTrends] Saved {len(trends_data)} designers to S3")

        return build_response(200, payload)

    except Exception as e:
        print(f"[GoogleTrends] FATAL: {e}")
        return build_response(500, {"error": str(e)})
