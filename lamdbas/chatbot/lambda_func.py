import json
import re
import boto3
from datetime import datetime
from urllib.request import urlopen, Request
from html.parser import HTMLParser
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

REGION = "eu-west-2"
CLAUDE_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

insights_cache = dynamodb.Table("InsightsCache")
runway_table = dynamodb.Table("New_Fashion_Analysis")
articles_table = dynamodb.Table("ArticleCache")

SYSTEM_PROMPT = """You are a fashion intelligence assistant with access to structured analysis
combining editorial reviews (Vogue, WWD) with computer vision data from runway photographs.

When given insights data, answer conversationally and specifically — reference actual themes,
colors, materials, and tensions from the data. Keep answers concise (3-5 sentences unless
the user asks for more detail). Use fashion-forward language but stay accessible.

If no specific designer/season data is available, answer from general fashion knowledge."""


# ─── Claude helpers ──────────────────────────────────────────────────────────

def _call_claude(messages: list, system: str = SYSTEM_PROMPT) -> str:
    response = bedrock.converse(
        modelId=CLAUDE_MODEL,
        system=[{"text": system}],
        messages=messages,
        inferenceConfig={"maxTokens": 512, "temperature": 0.7},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def _extract_designer_season(question: str) -> dict:
    """Use Claude to pull designer + season from a natural language question."""
    prompt = f"""Extract the designer and season from this fashion question.
Return ONLY valid JSON, no explanation:
{{"designer": "slug", "season": "spring-YYYY or fall-YYYY"}}

Rules:
- designer: lowercase slug with hyphens (chanel, louis-vuitton, miu-miu, balenciaga)
- season: must be "spring-YYYY" or "fall-YYYY" format
- If either is missing or unclear, use null

Question: {question}"""

    raw = _call_claude(
        [{"role": "user", "content": [{"text": prompt}]}],
        system="You extract structured data from text. Return only valid JSON.",
    )
    try:
        text = raw.strip().strip("```json").strip("```").strip()
        return json.loads(text)
    except Exception:
        return {"designer": None, "season": None}


# ─── Q&A data helpers ─────────────────────────────────────────────────────────

def _get_insights(designer: str, season: str) -> dict | None:
    try:
        cache_key = f"{designer}#{season}"
        resp = insights_cache.get_item(Key={"cache_key": cache_key})
        return resp.get("Item")
    except ClientError:
        return None


def _to_db_season(season: str) -> str:
    year = season.split("-")[1]
    if season.startswith("fall-"):
        return f"fall-winter-{year}"
    if season.startswith("spring-"):
        return f"spring-summer-{year}"
    return season


def _get_raw_runway(designer: str, season: str) -> list:
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
    try:
        while True:
            resp = runway_table.query(**kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    except ClientError:
        pass
    return items


def _get_image_urls(designer: str, season: str, items: list, limit: int = 6) -> list[str]:
    designer_slug = designer.lower().replace(" ", "-")
    season_slug = _to_db_season(season)
    folder = f"{designer_slug}-ready-to-wear-{season_slug}-paris"
    base = f"https://runwayimages.s3.eu-west-2.amazonaws.com/{folder}"

    seen = set()
    urls = []
    for item in items:
        name = item.get("original_image_name", "")
        if name and name not in seen:
            seen.add(name)
            urls.append(f"{base}/{name}")
        if len(urls) >= limit:
            break
    return urls


def _insights_to_context(insights: dict) -> str:
    lines = [
        f"Designer: {insights.get('designer', '').title()}",
        f"Season: {insights.get('season', '')}",
        f"Data quality: {insights.get('data_quality', 'unknown')}",
        f"Sources: {', '.join(insights.get('sources_used', []))}",
        "",
        f"Critic themes: {', '.join(insights.get('critic_themes', []))}",
        f"Visual themes: {', '.join(insights.get('visual_themes', []))}",
        "",
        "Where critics and visuals agree:",
        *[f"  - {a}" for a in insights.get("agreements", [])],
        "",
        "Tensions / divergences:",
        *[f"  - {t}" for t in insights.get("tensions", [])],
        "",
        f"Narrative: {insights.get('narrative', '')}",
    ]
    return "\n".join(lines)


def _raw_runway_to_context(items: list, designer: str, season: str) -> str:
    from collections import Counter
    colors = Counter(i.get("color_name", "").strip() for i in items if i.get("color_name"))
    garments = Counter(i.get("item_name", "").strip() for i in items if i.get("item_name"))
    materials = Counter(i.get("materials", "").strip() for i in items if i.get("materials"))

    lines = [
        f"Designer: {designer.replace('-', ' ').title()}",
        f"Season: {season}",
        f"Total looks: {len(items)}",
        f"Top colors: {', '.join(f'{n} ({c})' for n, c in colors.most_common(5))}",
        f"Top garments: {', '.join(f'{n} ({c})' for n, c in garments.most_common(5))}",
        f"Top materials: {', '.join(f'{n} ({c})' for n, c in materials.most_common(5))}",
    ]
    return "\n".join(lines)


# ─── Scraping helpers ─────────────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """Extracts visible text from HTML, skipping scripts/styles."""
    def __init__(self):
        super().__init__()
        self._skip = False
        self.paragraphs = []
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer"):
            self._skip = True
        elif tag == "p":
            self._buf = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer"):
            self._skip = False
        elif tag == "p":
            text = " ".join(self._buf).strip()
            if len(text.split()) >= 10:  # only substantive paragraphs
                self.paragraphs.append(text)
            self._buf = []

    def handle_data(self, data):
        if not self._skip:
            cleaned = data.strip()
            if cleaned:
                self._buf.append(cleaned)


def _detect_scrape_intent(text: str) -> str | None:
    """Return URL if message is a scrape request, else None."""
    keywords = ("scrape", "save this article", "add this article",
                 "import this", "store this article", "fetch this article")
    lower = text.lower()
    if not any(k in lower for k in keywords):
        return None
    m = re.search(r'https?://[^\s]+', text)
    return m.group(0).rstrip(".,;)") if m else None


def _parse_vogue_url(url: str) -> dict | None:
    """Extract designer/season/source from a Vogue fashion-shows URL."""
    m = re.search(r'vogue\.com/fashion-shows/([^/?#]+)/([^/?#]+)', url)
    if not m:
        return None
    slug = m.group(1)   # e.g. "fall-2026-ready-to-wear"
    designer = m.group(2)  # e.g. "miu-miu"
    sm = re.match(r'(fall|spring)-(\d{4})', slug)
    if not sm:
        return None
    season = f"{sm.group(1)}-{sm.group(2)}"
    return {
        "designer": designer,
        "season": season,
        "source": "vogue",
        "cache_key": f"vogue#{designer}#{season}",
    }


def _fetch_text(url: str, extra_headers: dict | None = None, timeout: int = 20) -> str | None:
    """Fetch URL content with a browser-like User-Agent."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/plain,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    if extra_headers:
        headers.update(extra_headers)
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _scrape_vogue_article(vogue_url: str) -> dict:
    """
    Fetch article using Jina Reader API (r.jina.ai) which returns clean
    extracted text from any URL, bypassing bot protection.
    Falls back to archivebuttons proxy if Jina fails.
    """
    jina_url = f"https://r.jina.ai/{vogue_url}"
    proxy_url = f"https://www.archivebuttons.com/articles?article={vogue_url}"

    # Try Jina Reader first — returns clean markdown with Title/Author/body
    text = _fetch_text(jina_url, extra_headers={"X-Return-Format": "text"})

    title = ""
    author = ""
    body = ""

    if text and len(text.split()) > 30:
        # Jina format:
        # Title: <title>
        # URL Source: <url>
        # Markdown Content:
        # By <author>
        # <body text...>

        lines = text.splitlines()

        for line in lines[:10]:
            if line.lower().startswith("title:"):
                title = line.split(":", 1)[1].strip()
            elif line.lower().startswith("by ") and not author:
                author = line[3:].strip()

        # Body: everything after "Markdown Content:" header
        mc_idx = next(
            (i for i, l in enumerate(lines) if "markdown content" in l.lower()), None
        )
        body_lines = lines[mc_idx + 1:] if mc_idx is not None else lines[10:]

        # Strip author line from body if it appears at the top
        if body_lines and body_lines[0].lower().startswith("by "):
            if not author:
                author = body_lines[0][3:].strip()
            body_lines = body_lines[1:]

        body = " ".join(l for l in body_lines if l.strip())

    # Fallback: archivebuttons (may also be client-side but worth trying)
    if not body or len(body.split()) < 30:
        html = _fetch_text(proxy_url)
        if html:
            extractor = _TextExtractor()
            extractor.feed(html)
            fallback_body = " ".join(extractor.paragraphs)
            if len(fallback_body.split()) > len(body.split()):
                body = fallback_body

    parse_status = "ok" if len(body.split()) >= 50 else "partial"

    return {
        "ok": True,
        "title": title or "Unknown",
        "author": author or "Unknown",
        "body_text": body[:8000],
        "word_count": len(body.split()),
        "proxy_url": proxy_url,
        "parse_status": parse_status,
    }


def _handle_scrape_command(url: str) -> tuple[str, list]:
    """Scrape article, save to ArticleCache, return (answer, images)."""
    meta = _parse_vogue_url(url)
    if not meta:
        return ("Sorry, I can only scrape Vogue fashion-show review URLs "
                "(e.g. vogue.com/fashion-shows/fall-2026-ready-to-wear/miu-miu).", [])

    cache_key = meta["cache_key"]

    # Check if already saved
    try:
        existing = articles_table.get_item(Key={"cache_key": cache_key})
        if existing.get("Item"):
            item = existing["Item"]
            return (
                f"This article is already saved: **{item.get('title', cache_key)}** "
                f"({item.get('word_count', '?')} words, "
                f"status: {item.get('parse_status', 'unknown')}).",
                []
            )
    except Exception:
        pass

    # Scrape
    data = _scrape_vogue_article(url)
    if not data["ok"]:
        return f"Could not scrape the article: {data['error']}", []

    # Save to DynamoDB
    now = datetime.utcnow().isoformat() + "+00:00"
    db_item = {
        "cache_key": cache_key,
        "designer": meta["designer"],
        "season": meta["season"],
        "source": meta["source"],
        "url": data["proxy_url"],
        "title": data["title"],
        "author": data["author"],
        "body_text": data["body_text"],
        "word_count": data["word_count"],
        "parse_status": data["parse_status"],
        "scraped_at": now,
        "cached_at": now,
    }

    try:
        articles_table.put_item(Item=db_item)
    except Exception as e:
        return f"Fetched the article but failed to save it: {e}", []

    status_note = "" if data["parse_status"] == "ok" else " (partial content — site may be blocking)"
    return (
        f"Saved **{data['title']}** by {data['author']} "
        f"({data['word_count']} words){status_note}. "
        f"It will now appear in the Articles tab.",
        []
    )


# ─── Lambda handler ───────────────────────────────────────────────────────────

def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _response(200, {})

    try:
        body = json.loads(event.get("body") or "{}")
        question = body.get("question", "").strip()
        history = body.get("history", [])

        if not question:
            return _response(400, {"error": "No question provided."})

        # ── Scrape command detection ──────────────────────────────────────────
        scrape_url = _detect_scrape_intent(question)
        if scrape_url:
            answer, images = _handle_scrape_command(scrape_url)
            return _response(200, {"answer": answer, "images": images})

        # ── Normal Q&A ────────────────────────────────────────────────────────
        extracted = _extract_designer_season(question)
        designer = extracted.get("designer")
        season = extracted.get("season")

        context_block = ""
        image_urls = []
        if designer and season:
            insights = _get_insights(designer, season)
            if insights:
                context_block = f"\n\n[FASHION DATA — synthesized insights]\n{_insights_to_context(insights)}\n[END DATA]"
            raw = _get_raw_runway(designer, season)
            if raw:
                if not insights:
                    context_block = f"\n\n[FASHION DATA — raw runway analysis]\n{_raw_runway_to_context(raw, designer, season)}\n[END DATA]"
                image_urls = _get_image_urls(designer, season, raw)
            elif not insights:
                context_block = f"\n\n[No data available for {designer} {season}. Answer from general fashion knowledge.]"

        messages = []
        for msg in history[-10:]:
            role = msg.get("role")
            text = msg.get("text", "")
            if role in ("user", "assistant") and text:
                messages.append({"role": role, "content": [{"text": text}]})

        messages.append({
            "role": "user",
            "content": [{"text": question + context_block}],
        })

        answer = _call_claude(messages)
        return _response(200, {"answer": answer, "images": image_urls})

    except Exception as e:
        print("Error:", e)
        return _response(500, {"error": str(e)})


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body),
    }
