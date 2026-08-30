"""
Parses a NOWFASHION runway look page and appends its metadata to
runway_metadata_schema.xlsx (Looks + Items sheets).

NOWFASHION serves a Cloudflare bot challenge to automated requests — confirmed
against plain HTTP and both headless and non-headless Playwright, all three get
served "Just a moment..." instead of the real page. This script does not try to
defeat that challenge. Instead, feed it HTML already rendered in a real,
human-driven browser session:

    1. Open the look page in Chrome (e.g. via the claude-in-chrome tool, or by hand).
    2. Save the fully rendered page to a .html file, e.g. in the browser console:
           document.documentElement.outerHTML
       wrapped in a Blob + <a download> to trigger a save, or Cmd+S "Webpage, Complete".
    3. Run:
           python nowfashion_runway_scraper.py path/to/look_page.html [more.html ...]

Fields sourced from the page's own schema.org JSON-LD (designer, season, city,
look number, publication date, source URL) plus its on-page structured widgets:
the color-palette swatches (discrete hex values), the Items grid (discrete
name -> attribute-list pairs), and the Style Analysis grid (Silhouette/
Materials/Mood/Movement/Styling). Duplicate look_id rows are skipped.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
from bs4 import BeautifulSoup

XLSX_PATH = Path(__file__).resolve().parent.parent / "runway_metadata_schema.xlsx"

_META_RE = re.compile(
    r"^(?P<designer>[a-z0-9]+(?:-[a-z0-9]+)*?)-"
    r"(?P<collection>ready-to-wear|ready-wear|haute-couture|couture|menswear|womenswear|men-women|men-&-women)-"
    r"(?P<season>(?:spring|fall)-(?:summer|winter)-20\d{2})"
)
_TAIL_KEYWORDS = [
    "fashion-week-runway-model",
    "fashion-show-runway",
    "fashion-week-runway",
    "fashion-week-model",
    "runway-model",
    "fashion-week",
    "fashion-show",
    "model",
    "runway",
]


def _parse_slug_parts(slug: str) -> dict:
    """Derive designer/collection/season/city/look_number from a look slug.

    NOWFASHION has changed its look URL format over the years, so this is
    intentionally tolerant: e.g. `...-fashion-week-runway-001`,
    `...-fashion-week-runway-01`, `...-fashion-show-runway-0001`,
    `...-runway-0001`, `...-fashion-week-runway-model-001`, and the
    `ready-wear` (missing "-to-") typo variant.
    """
    m = _META_RE.match(slug)
    if not m:
        raise ValueError(f"URL slug didn't match expected NOWFASHION look pattern: {slug!r}")
    g = m.groupdict()
    designer = g["designer"]
    collection = g["collection"]
    season = g["season"]
    tail = slug[m.end():]
    digits = re.findall(r"\d+", tail)
    if not digits:
        raise ValueError(f"no look number found in slug: {slug!r}")
    look_number = int(digits[-1])
    city_tail = re.sub(r"\d+", "", tail)
    for kw in _TAIL_KEYWORDS:
        city_tail = city_tail.replace(kw, "")
    city = city_tail.strip("-").strip()
    return {
        "designer": designer,
        "collection": collection,
        "season": season,
        "city": city,
        "look_number": look_number,
    }

_COLLECTION_LABELS = {
    "ready-to-wear": "Ready To Wear",
    "ready-wear": "Ready To Wear",
    "haute-couture": "Haute Couture",
    "couture": "Couture",
    "menswear": "Menswear",
    "womenswear": "Womenswear",
    "men-women": "Men & Women",
    "men-&-women": "Men & Women",
}
_COLLECTION_ABBR = {
    "ready-to-wear": "rtw",
    "ready-wear": "rtw",
    "haute-couture": "couture",
    "couture": "couture",
    "menswear": "men",
    "womenswear": "women",
    "men-women": "menwomen",
    "men-&-women": "menwomen",
}

_COLORS = [
    "white", "black", "blue", "red", "green", "yellow", "brown", "grey", "gray",
    "pink", "purple", "orange", "beige", "navy", "tan", "cream", "ivory", "khaki",
    "maroon", "olive", "burgundy", "silver", "gold", "multicolor", "charcoal",
]
_MATERIALS = [
    "cotton", "denim", "leather", "wool", "silk", "linen", "polyester", "nylon",
    "cashmere", "velvet", "satin", "jersey", "tweed", "suede", "mesh", "lace",
    "knit", "corduroy", "canvas", "chiffon", "faux fur", "fur",
]
_MOOD_ADJECTIVES = [
    "grounded", "utilitarian", "whimsical", "chaotic", "edgy", "romantic",
    "minimalist", "maximalist", "dramatic", "playful", "elegant", "raw",
    "rebellious", "futuristic", "nostalgic", "ethereal", "bold", "subtle",
    "sophisticated", "casual", "structured", "fluid", "avant-garde", "classic",
    "sensual", "austere", "joyful", "moody", "dark", "vibrant", "subdued",
    "eclectic", "refined", "provocative", "theatrical", "understated",
    "opulent", "industrial", "polished", "relaxed", "grungy", "clean",
]


def _season_abbr(season_slug: str) -> str:
    match = re.match(r"(spring|fall)-(summer|winter)-(\d{4})", season_slug)
    first, second, year = match.groups()
    return f"{'s' if first == 'spring' else 'f'}{'s' if second == 'summer' else 'w'}{year[-2:]}"


def _labeled_value(soup: BeautifulSoup, label: str) -> str | None:
    for el in soup.select(".text-xs.uppercase.tracking-wider"):
        if el.get_text(strip=True) == label:
            sib = el.find_next_sibling()
            return sib.get_text(strip=True) if sib else None
    return None


def _json_ld(soup: BeautifulSoup, type_: str) -> dict:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("@type") == type_:
            return data
    return {}


def _style_field(soup: BeautifulSoup, label: str) -> str:
    for dt in soup.find_all("dt"):
        if dt.get_text(strip=True) == label:
            dd = dt.find_next_sibling("dd")
            return dd.get_text(strip=True) if dd else ""
    return ""


def _extract_mood_keywords(mood_sentence: str) -> str:
    lower = mood_sentence.lower()
    found = [w for w in _MOOD_ADJECTIVES if re.search(rf"\b{re.escape(w)}\b", lower)]
    # preserve order of appearance in the sentence
    found.sort(key=lambda w: lower.index(w))
    return "; ".join(found)


def parse_look_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    image_obj = _json_ld(soup, "ImageObject")
    product_obj = _json_ld(soup, "Product")
    source_url = image_obj.get("url") or product_obj.get("url") or ""

    slug = source_url.rstrip("/").rsplit("/", 1)[-1]
    parts = _parse_slug_parts(slug)

    designer = _labeled_value(soup, "Brand") or parts["designer"].replace("-", " ").title()
    location = _labeled_value(soup, "Location") or ""
    city = location.split(",")[0].strip() or (parts["city"].replace("-", " ").title() if parts["city"] else "")
    season = parts["season"].replace("-", " ").title()
    collection = _COLLECTION_LABELS.get(parts["collection"], parts["collection"].replace("-", " ").title())
    look_number = parts["look_number"]
    city_slug = parts["city"].replace(" ", "-") if parts["city"] else (city.lower().replace(" ", "-") if city else "")
    city_seg = f"-{city_slug}" if city_slug else ""
    look_id = (
        f"{parts['designer']}-{_COLLECTION_ABBR.get(parts['collection'], parts['collection'])}-"
        f"{_season_abbr(parts['season'])}{city_seg}-{look_number:03d}"
    )

    published = image_obj.get("datePublished", "")
    publication_date = published.split("T")[0] if published else ""

    palette = [
        sw["style"].split("background-color:")[-1].strip()
        for sw in soup.select(".img-detail-palette__swatch")
        if sw.get("style")
    ]

    mood_sentence = _style_field(soup, "Mood")

    look = {
        "look_id": look_id,
        "designer": designer,
        "designer_lower": designer.lower(),
        "season": season,
        "season_lower": season.lower().replace(" ", "-"),
        "collection": collection,
        "event": f"{city} Fashion Week",
        "city": city,
        "look_number": look_number,
        "publication_date": publication_date,
        "source_url": source_url,
        "color_palette_hex": "; ".join(palette),
        "mood_keywords": _extract_mood_keywords(mood_sentence),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "silhouette": _style_field(soup, "Silhouette"),
        "materials_note": _style_field(soup, "Materials"),
        "movement": _style_field(soup, "Movement"),
        "styling": _style_field(soup, "Styling"),
    }

    items = []
    for dt in soup.select(".img-detail-ai__grid--wide dt"):
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        item_name = dt.get_text(strip=True)
        dd_copy = BeautifulSoup(str(dd), "lxml")
        for sw in dd_copy.select(".img-detail-ai__item-swatch"):
            sw.decompose()
        raw = dd_copy.get_text(strip=True)
        tokens = [t.strip().lower() for t in raw.split(",") if t.strip() and t.strip().lower() != item_name.lower()]
        color = next((t for t in tokens if t in _COLORS), "")
        material = next((t for t in tokens if t in _MATERIALS), "")
        item_label = f"{color} {item_name}" if color else item_name
        items.append({
            "look_id": look_id,
            "item_name": item_name,
            "color": color,
            "material": material,
            "item_label": item_label,
        })

    return {"look": look, "items": items}


_FLUSH_EVERY = 10
_WB = None
_WB_SEEN_IDS: set[str] | None = None
_WB_ITEM_IDX: dict[str, set[tuple]] | None = None
_FLUSH_PENDING = 0


def _load_ids(looks_ws) -> set[str]:
    ids = set()
    for row in looks_ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            ids.add(row[0])
    return ids


def _load_item_idx(items_ws) -> dict[str, set[tuple]]:
    idx: dict[str, set[tuple]] = {}
    iid = items_ws[1][0].value
    for row in items_ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        lo = idx.setdefault(row[0], set())
        lo.add(tuple(v for v in row[1:] if v is not None))
    return idx


def flush_workbook(xlsx_path: Path = XLSX_PATH) -> None:
    global _FLUSH_PENDING
    if _WB is not None:
        tmp = xlsx_path.with_name(xlsx_path.name + ".tmp")
        _WB.save(tmp)
        os.replace(tmp, xlsx_path)
    _FLUSH_PENDING = 0


def append_to_workbook(result: dict, xlsx_path: Path = XLSX_PATH) -> bool:
    global _WB, _WB_SEEN_IDS, _WB_ITEM_IDX, _FLUSH_PENDING
    if _WB is None:
        _WB = openpyxl.load_workbook(xlsx_path)
        _WB_SEEN_IDS = _load_ids(_WB["Looks"])
        _WB_ITEM_IDX = _load_item_idx(_WB["Items"])

    looks_ws = _WB["Looks"]
    items_ws = _WB["Items"]

    look = result["look"]
    look_id = look["look_id"]
    items_header = [c.value for c in items_ws[1]]

    if look_id not in _WB_SEEN_IDS:
        looks_header = [c.value for c in looks_ws[1]]
        looks_ws.append([look.get(col, "") for col in looks_header])
        _WB_SEEN_IDS.add(look_id)
        existing = _WB_ITEM_IDX.setdefault(look_id, set())
        for item in result["items"]:
            fp = tuple(item.get(col, "") for col in items_header[1:])
            if fp in existing:
                continue
            items_ws.append([item.get(col, "") for col in items_header])
            existing.add(fp)
        _FLUSH_PENDING += 1
        if _FLUSH_PENDING >= _FLUSH_EVERY:
            flush_workbook()
        print(f"  added: {look_id} ({len(result['items'])} items)")
        return True

    n = 0
    existing = _WB_ITEM_IDX.setdefault(look_id, set())
    for item in result["items"]:
        fp = tuple(item.get(col, "") for col in items_header[1:])
        if fp in existing:
            continue
        items_ws.append([item.get(col, "") for col in items_header])
        existing.add(fp)
        n += 1
    if n == 0:
        print(f"  skip (look + items already present): {look_id}")
        return False
    _FLUSH_PENDING += 1
    if _FLUSH_PENDING >= _FLUSH_EVERY:
        flush_workbook()
    print(f"  added {n}/{len(result['items'])} items for existing {look_id}")
    return True


def main(html_paths: list[str]) -> None:
    for path_str in html_paths:
        path = Path(path_str)
        print(f"Parsing {path.name}...")
        html = path.read_text(encoding="utf-8")
        result = parse_look_html(html)
        append_to_workbook(result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
