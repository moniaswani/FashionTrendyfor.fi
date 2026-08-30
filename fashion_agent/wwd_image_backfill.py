"""
General-purpose backfill of missing runway photos from a WWD gallery into
S3, keyed by look_id, joining against look metadata in RunwayLooks
(DynamoDB). Generalized from fashion_agent/wwd_balmain_images.py after the
same gap (RunwayLooks metadata exists, runwayimages S3 object never got
uploaded) turned up for a third designer — see the memory note
"WWD image backfill pattern" for the full method and gotchas.

This tool does NOT discover gallery IDs for you — that step stays manual
and deliberate: search https://wwd.com/wp-json/wp/v2/pmc-gallery?search=
<designer>+<season>, exclude "Backstage at.../Front Row at..." results,
and verify the photo count roughly matches the look count (off by ~1 is
normal — a finale look often isn't individually photographed) before
using an ID here. Spot-check at least one resolved photo against the
corresponding RunwayItems row's colors/items before trusting a new
gallery at scale.

Matches by the look number embedded in the WWD filename (not position),
since WWD's own numbering sometimes has internal gaps. See
extract_look_number() for the two filename gotchas this handles.

Usage:
    .venv/bin/python -m fashion_agent.wwd_image_backfill \\
        --designer ganni --season spring-summer-2026 --gallery-id 1238265944 --dry-run
    .venv/bin/python -m fashion_agent.wwd_image_backfill \\
        --designer ganni --season spring-summer-2026 --gallery-id 1238265944
"""
from __future__ import annotations

import argparse
import re
import time

import boto3
import httpx
from boto3.dynamodb.conditions import Key

REGION = "eu-west-2"
BUCKET = "runwayimages"
LOOKS_TABLE = "RunwayLooks"
PACE_S = 0.3

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def load_looks(designer_lower: str, season_lower: str) -> dict[int, str]:
    """Return {look_number: look_id} for one designer+season."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(LOOKS_TABLE)
    items = []
    kwargs = {
        "IndexName": "DesignerSeasonIndex",
        "KeyConditionExpression": Key("designer_lower").eq(designer_lower) & Key("season_lower").eq(season_lower),
        "ProjectionExpression": "look_id, look_number",
    }
    while True:
        page = table.query(**kwargs)
        items.extend(page["Items"])
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    out: dict[int, str] = {}
    for item in items:
        try:
            out[int(item["look_number"])] = item["look_id"]
        except (TypeError, ValueError, KeyError):
            continue
    return out


def fetch_gallery_photo_ids(client: httpx.Client, gallery_id: int) -> list[int]:
    r = client.get(f"https://wwd.com/wp-json/wp/v2/pmc-gallery/{gallery_id}", params={"_fields": "meta"})
    r.raise_for_status()
    return list(r.json()["meta"]["pmc-gallery"].values())


def resolve_media_urls(client: httpx.Client, media_ids: list[int]) -> dict[int, str]:
    out: dict[int, str] = {}
    for i in range(0, len(media_ids), 50):
        batch = media_ids[i : i + 50]
        r = client.get(
            "https://wwd.com/wp-json/wp/v2/media",
            params={"include": ",".join(str(m) for m in batch), "_fields": "id,source_url", "per_page": 100},
        )
        r.raise_for_status()
        for item in r.json():
            out[item["id"]] = item["source_url"]
    return out


def extract_look_number(url: str) -> int | None:
    """Grab the look number embedded in a WWD filename. Filenames often have
    an earlier season-encoding number too (Balmain-s22_097.jpg has "22" then
    "097"), and WordPress sometimes appends a long edit-timestamp suffix
    after that (..._097-e1633859397926.jpg) — the real look number is
    always <=4 digits and is the LAST such run before any long suffix."""
    fname = url.rsplit("/", 1)[-1]
    short_runs = [int(run) for run in re.findall(r"\d+", fname) if len(run) <= 4]
    return short_runs[-1] if short_runs else None


def build_number_to_url(client: httpx.Client, gallery_id: int) -> dict[int, str]:
    """Ordered by gallery position, so if a look number has duplicate photos
    (WWD sometimes re-uploads one with a -1 suffix), the first-listed one wins."""
    photo_ids = fetch_gallery_photo_ids(client, gallery_id)
    urls_by_id = resolve_media_urls(client, photo_ids)
    by_number: dict[int, str] = {}
    for photo_id in photo_ids:
        url = urls_by_id.get(photo_id)
        if not url:
            continue
        num = extract_look_number(url)
        if num is not None and num not in by_number:
            by_number[num] = url
    return by_number


def already_uploaded(s3, key: str) -> bool:
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--designer", required=True, help="designer_lower, e.g. ganni")
    ap.add_argument("--season", required=True, help="season_lower, e.g. spring-summer-2026")
    ap.add_argument("--gallery-id", required=True, type=int, help="WWD pmc-gallery post ID, pre-verified")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="re-upload even if the S3 key already exists (not needed for the normal gap-filling case)",
    )
    args = ap.parse_args()

    looks = load_looks(args.designer, args.season)
    if not looks:
        print(f"no RunwayLooks rows found for designer={args.designer!r} season={args.season!r}")
        return
    print(f"{args.designer} {args.season}: {len(looks)} looks")

    s3 = boto3.client("s3", region_name=REGION)
    with httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": _UA}) as client:
        by_number = build_number_to_url(client, args.gallery_id)
        print(f"  WWD gallery {args.gallery_id} has {len(by_number)} numbered photos")

        uploaded = 0
        for num in sorted(looks):
            look_id = looks[num]
            key = f"{look_id}.jpg"
            if not args.overwrite and already_uploaded(s3, key):
                continue
            src = by_number.get(num)
            if not src:
                print(f"    no WWD photo for look {num} ({look_id})")
                continue
            if args.dry_run:
                print(f"    [dry-run] would upload {key} <- {src}")
                uploaded += 1
                continue
            try:
                r = client.get(src)
                r.raise_for_status()
            except Exception as e:
                print(f"    download failed {key} ({type(e).__name__}: {e})")
                continue
            s3.put_object(Bucket=BUCKET, Key=key, Body=r.content, ContentType="image/jpeg")
            uploaded += 1
            print(f"    [{uploaded}] uploaded {key} ({len(r.content) // 1024} KB)")
            time.sleep(PACE_S)

    print(f"\nTotal uploaded: {uploaded}")


if __name__ == "__main__":
    main()
