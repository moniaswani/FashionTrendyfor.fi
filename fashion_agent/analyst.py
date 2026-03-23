"""
Core synthesis agent.

Pipeline:
    1. Check InsightsCache (skip if no_cache or dry_run)
    2. Per source: check ArticleCache, else scrape live
    3. Fetch aggregated runway data from New_Fashion_Analysis
    4. Build prompt and call Claude via AWS Bedrock
    5. Parse structured JSON response
    6. Cache insights and return

Required env vars:
    AWS_REGION  (default: eu-west-2)
    AWS credentials (standard boto3 chain)
"""

import json
import os

import boto3

from dynamo_client import (
    cache_article,
    cache_insights,
    get_cached_article,
    get_cached_insights,
    get_runway_data,
)
from scraper import fetch_article, fetch_custom_article

REGION = os.environ.get("AWS_REGION", "eu-west-2")
CLAUDE_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(designer: str, season: str, articles: list[dict], runway: dict) -> str:
    # Editorial section — only include articles that parsed successfully
    editorial_sections = []
    for article in articles:
        if article.get("parse_status") == "ok":
            editorial_sections.append(
                f"SOURCE: {article['source'].upper()}\n"
                f"Title: {article.get('title', '(untitled)')}\n"
                f"Author: {article.get('author') or 'unknown'}\n\n"
                f"{article['body_text']}"
            )

    editorial_text = (
        "\n\n---\n\n".join(editorial_sections)
        if editorial_sections
        else "No editorial coverage available for this collection."
    )

    # Runway data section
    if runway.get("found"):
        colors_str = ", ".join(
            f"{c['name']} ({c['count']} looks)" for c in runway["top_colors"]
        )
        items_str = ", ".join(f"{i['name']} ({i['count']})" for i in runway["top_items"])
        materials_str = ", ".join(f"{m['name']} ({m['count']})" for m in runway["top_materials"])
        runway_text = (
            f"Total looks analyzed: {runway['total_looks']}\n"
            f"Top colors by frequency: {colors_str}\n"
            f"Top garment types: {items_str}\n"
            f"Top materials: {materials_str}"
        )
    else:
        runway_text = "No runway image data available for this collection."

    sources_used = [a["source"] for a in articles if a.get("parse_status") == "ok"]

    return f"""You are a fashion intelligence analyst. Your task is to synthesize editorial criticism with computer vision data from runway images for {designer.title()}'s {season} collection.

## EDITORIAL COVERAGE
{editorial_text}

## RUNWAY IMAGE ANALYSIS
(Extracted from look-by-look computer vision analysis of runway photographs)
{runway_text}

## INSTRUCTIONS
Synthesize both data sources into structured insights. Pay special attention to where the editorial narrative and the visual data agree or diverge — divergences are the most analytically valuable output.

Respond ONLY with a valid JSON object in this exact format (no markdown, no explanation):

{{
  "critic_themes": ["theme1", "theme2"],
  "visual_themes": ["theme1", "theme2"],
  "agreements": ["point1", "point2"],
  "tensions": ["point1", "point2"],
  "narrative": "2-3 sentence brand story combining both sources.",
  "sources_used": {json.dumps(sources_used)},
  "data_quality": "high"
}}

Field definitions:
- critic_themes: 3-6 themes the critics identified in their editorial text
- visual_themes: 3-6 themes independently observable from the image data (colors, silhouettes, materials)
- agreements: 2-4 specific points where critic observations align with the visual data
- tensions: 1-4 points where critic observations diverge from, contradict, or add nuance beyond what the visual data shows — this is the most valuable output; be specific
- narrative: 2-3 sentences synthesizing editorial voice and visual evidence into a coherent brand story
- sources_used: list of sources that had usable content
- data_quality: "high" (both editorial and visual), "medium" (one source missing), or "low" (minimal data)

Respond with the JSON object only."""


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """
    Parse Claude's response as JSON.
    Handles cases where Claude wraps the JSON in markdown code fences.
    """
    text = raw.strip()
    if "```" in text:
        # Strip markdown fences
        parts = text.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{"):
                return json.loads(candidate)
    return json.loads(text)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def analyze(
    designer: str,
    season: str,
    sources: list[str] | None = None,
    city: str = "paris",
    no_cache: bool = False,
    dry_run: bool = False,
    custom_urls: list[str] | None = None,
) -> dict:
    """
    Run the full analysis pipeline for a designer/season collection.

    Args:
        designer:  slug e.g. "chanel", "louis-vuitton"
        season:    e.g. "spring-2025", "fall-2023"
        sources:   list of sources to scrape, default ["vogue", "wwd"]
        city:      city for WWD URL, default "paris"
        no_cache:  if True, ignore all caches and force fresh scrape + analysis
        dry_run:   fetch and parse but do not call Claude or write to cache

    Returns:
        Insights dict with keys: critic_themes, visual_themes, agreements,
        tensions, narrative, sources_used, data_quality, designer, season.
        On dry_run, returns a summary dict instead.
    """
    if sources is None:
        sources = ["vogue", "wwd"]

    # 1. Check insights cache
    if not no_cache and not dry_run:
        cached = get_cached_insights(designer, season)
        if cached:
            print(f"  [cache hit] insights already exist for {designer} / {season}")
            return cached

    # 2. Fetch articles — check article cache per source first
    articles: list[dict] = []
    for source in sources:
        article = None

        if not no_cache and not dry_run:
            article = get_cached_article(source, designer, season)
            if article:
                print(f"  [cache hit] {source} article")

        if article is None:
            print(f"  [scraping] {source}...")
            article = fetch_article(source, designer, season, city=city)
            status = article["parse_status"]
            detail = (
                f"{article.get('word_count', 0)} words"
                if status == "ok"
                else article.get("error", "unknown error")
            )
            print(f"    → {status} ({detail})")

            if not dry_run and status == "ok":
                cache_article(source, designer, season, article)

        articles.append(article)

    # 2b. Fetch any custom URLs via archivebuttons
    for url in (custom_urls or []):
        print(f"  [scraping] custom url: {url[:60]}...")
        article = fetch_custom_article(url)
        status = article["parse_status"]
        detail = f"{article.get('word_count', 0)} words" if status == "ok" else article.get("error", "unknown error")
        print(f"    → {status} ({detail})")
        articles.append(article)

    # 3. Fetch runway data
    print(f"  [runway data] querying New_Fashion_Analysis...")
    runway = get_runway_data(designer, season)
    print(f"    → {runway['total_looks']} looks found")

    # 4. Build prompt
    prompt = _build_prompt(designer, season, articles, runway)

    # Dry run — print prompt preview and return summary
    if dry_run:
        print("\n  [dry-run] Prompt preview (first 400 chars):")
        print("  " + prompt[:400].replace("\n", "\n  ") + "...\n")
        return {
            "designer": designer,
            "season": season,
            "dry_run": True,
            "articles": [
                {
                    "source": a["source"],
                    "parse_status": a.get("parse_status"),
                    "word_count": a.get("word_count", 0),
                    "error": a.get("error"),
                }
                for a in articles
            ],
            "runway_looks": runway.get("total_looks", 0),
            "runway_found": runway.get("found", False),
        }

    # 5. Call Claude via Bedrock
    print(f"  [claude] synthesizing with {CLAUDE_MODEL}...")
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    response = bedrock.converse(
        modelId=CLAUDE_MODEL,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1024},
    )

    # 6. Parse response
    raw = response["output"]["message"]["content"][0]["text"]
    try:
        insights = _extract_json(raw)
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Claude returned unparseable JSON: {e}\n\nRaw response:\n{raw}") from e

    insights["designer"] = designer
    insights["season"] = season

    # 7. Cache and return
    cache_insights(designer, season, insights)
    return insights
