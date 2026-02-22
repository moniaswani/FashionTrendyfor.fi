"""
Run this script locally to fetch Google Trends data for all designers
and upload the result to S3. Your home IP avoids Google rate limits.

Usage:
    python fetch_and_upload.py

Requirements:
    pip install pytrends pandas boto3 requests
"""

import json
import time
import datetime
import boto3
from pytrends.request import TrendReq

CACHE_BUCKET = "fashion-trends-cache"
CACHE_KEY = "designer_trends.json"
REGION = "eu-west-2"

s3 = boto3.client("s3", region_name=REGION)

# Hardcoded designer list — search terms used for Google Trends
DESIGNERS = [
    "Acne Studios",
    "Balenciaga",
    "Balmain",
    "Celine",
    "Chanel",
    "Chloe",
    "Dior",
    "Dolce & Gabbana",
    "Ganni",
    "Giorgio Armani",
    "Givenchy",
    "Hermes",
    "Issey Miyake",
    "Lacoste",
    "Loewe",
    "Maison Margiela",
    "Miu Miu",
    "Paloma Wool",
    "Rick Owens",
    "Yves Saint Laurent",
    "Schiaparelli",
    "Valentino",
    "Vivienne Westwood",
]


def fetch_trends_for_designers(designers):
    results = {}
    batches = [designers[i : i + 5] for i in range(0, len(designers), 5)]

    pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 25))

    for i, batch in enumerate(batches):
        print(f"  Fetching batch {i + 1}/{len(batches)}: {batch}")
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
                    print(f"    No data returned for {batch}")
                    for keyword in batch:
                        results[keyword] = []
                    break

                if "isPartial" in interest_df.columns:
                    interest_df = interest_df.drop(columns=["isPartial"])

                # Store raw weekly data ("YYYY-MM-DD") for richer charts
                for keyword in batch:
                    if keyword in interest_df.columns:
                        series = interest_df[keyword]
                        results[keyword] = [
                            {"date": str(idx)[:10], "value": int(val)}
                            for idx, val in series.items()
                        ]
                        print(f"    ✓ {keyword}: {len(results[keyword])} data points")
                    else:
                        results[keyword] = []
                        print(f"    - {keyword}: no data")

                # Polite delay between batches
                time.sleep(3)
                break

            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = (
                    "429" in error_str
                    or "too many" in error_str
                    or "response" in error_str
                )
                attempt += 1
                if is_rate_limit and attempt < max_attempts:
                    wait = base_delay * (2 ** attempt)
                    print(f"    Rate limited — waiting {wait}s (attempt {attempt}/{max_attempts})")
                    time.sleep(wait)
                else:
                    print(f"    Error for {batch}: {e}")
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
    print(f"\n✓ Uploaded to s3://{CACHE_BUCKET}/{CACHE_KEY}")


def main():
    print("=== Google Trends Fetcher ===\n")

    designers = DESIGNERS
    print(f"1. Using {len(designers)} designers: {designers}\n")

    print("2. Fetching Google Trends data...")
    trends_data = fetch_trends_for_designers(designers)

    payload = {
        "updated_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "designers": trends_data,
    }

    print("\n3. Uploading to S3...")
    save_to_s3(payload)

    designers_with_data = sum(1 for v in trends_data.values() if v)
    print(f"\nDone! {designers_with_data}/{len(designers)} designers have trend data.")


if __name__ == "__main__":
    main()
