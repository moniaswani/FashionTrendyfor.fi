"""
Live article scraper — fetches Vogue and WWD runway reviews on-demand.

URL formats:
    vogue: https://www.archivebuttons.com/articles?article=https://www.vogue.com/fashion-shows/{season}-ready-to-wear/{designer}
    wwd:   https://wwd.com/runway/{season}/{city}/{designer}/review/

Season format: "spring-2023", "fall-2023"

Returns:
    {
        source, designer, season, url,
        title, author, body_text, word_count,
        parse_status,   # "ok" | "failed"
        error,          # only present on failure
        scraped_at,
    }
"""

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ARCHIVEBUTTONS_BASE = "https://www.archivebuttons.com"
VOGUE_BASE = "https://www.vogue.com/fashion-shows"
WWD_BASE = "https://wwd.com"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ── URL builders ─────────────────────────────────────────────────────────────

def _build_url(source: str, designer: str, season: str, city: str = "paris") -> str:
    if source == "vogue":
        vogue_url = f"{VOGUE_BASE}/{season}-ready-to-wear/{designer}"
        return f"{ARCHIVEBUTTONS_BASE}/articles?article={vogue_url}"
    if source == "wwd":
        return f"{WWD_BASE}/runway/{season}/{city}/{designer}/review/"
    raise ValueError(f"Unknown source '{source}'. Expected 'vogue' or 'wwd'.")


# ── HTTP fetch ────────────────────────────────────────────────────────────────

def _fetch_html(url: str, domain: str) -> str | None:
    """
    Opens an httpx session, warms it up on the base domain to collect
    server-set cookies, then sets common consent cookie names before
    fetching the actual article URL.
    """
    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
        try:
            client.get(f"https://{domain}", timeout=10)
            for name in ["cookieconsent_status", "cookie_consent", "consent", "gdpr_consent"]:
                client.cookies[name] = "allow"
            resp = client.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text
            print(f"    HTTP {resp.status_code}")
        except Exception as e:
            print(f"    Fetch error: {e}")
    return None


# ── Playwright fetch (Vogue via archivebuttons iframe) ────────────────────────

def _fetch_vogue(url: str) -> dict:
    """
    Fetches a Vogue article via archivebuttons.com.
    archivebuttons renders the article inside an iframe — no cookie consent needed,
    just wait for networkidle then read the iframe content directly.
    Returns a parsed dict (same shape as _parse_vogue output), never raises.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)

            iframe = page.frame_locator("iframe").first

            # Author
            try:
                author = iframe.locator("[data-testid='BylineName']").first.inner_text(timeout=5000)
            except PlaywrightTimeout:
                author = ""

            # Title
            try:
                title = iframe.locator("h1").first.inner_text(timeout=3000)
            except PlaywrightTimeout:
                title = ""

            # Body paragraphs — filter out short noise (ads, captions)
            paras = iframe.locator("article p").all_inner_texts()
            paras = [p.strip() for p in paras if len(p.strip()) > 50]

            browser.close()

            if not paras:
                return {"parse_status": "failed", "error": "no paragraphs found in iframe — article may not have loaded"}

            return {
                "title": title,
                "author": author,
                "body_text": "\n\n".join(paras),
                "parse_status": "ok",
            }
    except Exception as e:
        return {"parse_status": "failed", "error": f"Playwright error: {e}"}


# ── Generic archivebuttons fetch (any URL) ────────────────────────────────────

def fetch_custom_article(url: str) -> dict:
    """
    Fetch any article URL via archivebuttons.com iframe.
    Uses the same iframe approach as Vogue — works with any paywalled publication.

    Args:
        url: Full article URL e.g. "https://www.businessoffashion.com/reviews/..."

    Returns:
        dict with parse_status "ok" or "failed". Never raises.
    """
    from urllib.parse import urlparse

    source = urlparse(url).netloc.replace("www.", "")
    ab_url = f"{ARCHIVEBUTTONS_BASE}/articles?article={url}"
    scraped_at = datetime.now(timezone.utc).isoformat()

    base = {"source": source, "url": url, "scraped_at": scraped_at}

    result = _fetch_vogue(ab_url)  # same iframe logic works for any site
    if result["parse_status"] == "ok":
        result["word_count"] = len(result["body_text"].split())
    return {**base, **result}


# ── Source-specific parsers ───────────────────────────────────────────────────

def _parse_vogue(html: str) -> dict:
    """
    Targets:
        <article class="RunwayShowReviewSection-...">
          <div data-testid="BodyWrapper"><div><p>...</p></div></div>
        </article>
    """
    # Quick sanity checks before parsing
    if len(html) < 5000:
        return {"parse_status": "failed", "error": f"page too small ({len(html):,} chars) — likely redirect or error page"}

    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    author = ""
    for sel in [{"rel": "author"}, {"class": "contributor"}, {"itemprop": "author"}]:
        tag = soup.find(attrs=sel)
        if tag:
            author = tag.get_text(strip=True)
            break

    # Primary: RunwayShowReviewSection → BodyWrapper
    body_el = None
    review_article = soup.find(
        "article",
        class_=lambda c: c and any("RunwayShowReviewSection" in cls for cls in c),
    )
    if review_article:
        body_el = review_article.find(attrs={"data-testid": "BodyWrapper"}) or review_article

    # Fallbacks for markup changes
    if body_el is None:
        body_el = (
            soup.find(attrs={"data-testid": "BodyWrapper"})
            or soup.find(attrs={"data-testid": "article-body"})
            or soup.find("article")
            or soup.find("main")
        )

    if body_el is None:
        html_lower = html.lower()
        if "cookie" in html_lower or "consent" in html_lower or "cookiewall" in html_lower:
            return {"parse_status": "failed", "error": "article body not found — probable cookie consent wall (cookie acceptance may not be working)"}
        return {"parse_status": "failed", "error": "article body not found — run debug_html.py to inspect raw HTML"}

    paragraphs = [p.get_text(strip=True) for p in body_el.find_all("p") if p.get_text(strip=True)]
    body_text = "\n\n".join(paragraphs)

    if len(body_text) < 100:
        return {"parse_status": "failed", "error": "article body too short — possible paywall"}

    return {"title": title, "author": author, "body_text": body_text, "parse_status": "ok"}


def _parse_wwd(html: str) -> dict:
    """
    Targets:
        h1.article-title       → title
        p.article-excerpt      → deck (prepended to body)
        .article-byline a[href*=/wwd-masthead/] → author
        div.article-body       → body (fallback: <article> minus gallery noise)
    """
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1", class_=lambda c: c and "article-title" in c) or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    excerpt_tag = soup.find("p", class_=lambda c: c and "article-excerpt" in c)
    excerpt = excerpt_tag.get_text(strip=True) if excerpt_tag else ""

    author = ""
    byline = soup.find(class_=lambda c: c and "article-byline" in c)
    if byline:
        author_link = byline.find("a", href=lambda h: h and "/wwd-masthead/" in h)
        if author_link:
            author = author_link.get_text(strip=True)

    body_el = soup.find(class_=lambda c: c and "article-body" in c)
    if body_el is None:
        article_el = soup.find("article")
        if article_el:
            for noise in article_el.find_all(
                class_=lambda c: c and any(
                    x in (c if isinstance(c, str) else " ".join(c))
                    for x in ["runway-featured-gallery", "social-share", "article-byline"]
                )
            ):
                noise.decompose()
            body_el = article_el

    if body_el is None:
        body_el = soup.find("main")

    if body_el is None:
        return {"parse_status": "failed", "error": "article body not found"}

    paragraphs = [
        p.get_text(strip=True)
        for p in body_el.find_all("p")
        if p.get_text(strip=True) and not (excerpt_tag and p == excerpt_tag)
    ]
    body_text = "\n\n".join(paragraphs)
    full_text = f"{excerpt}\n\n{body_text}".strip() if excerpt else body_text

    if len(full_text) < 100:
        return {"parse_status": "failed", "error": "article body too short — possible paywall"}

    return {"title": title, "author": author, "body_text": full_text, "parse_status": "ok"}


_PARSERS = {"vogue": _parse_vogue, "wwd": _parse_wwd}
_DOMAINS = {"vogue": "www.archivebuttons.com", "wwd": "wwd.com"}


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_article(
    source: str,
    designer: str,
    season: str,
    city: str = "paris",
) -> dict:
    """
    Fetch and parse a runway review article.

    Args:
        source:   "vogue" or "wwd"
        designer: slug e.g. "chanel", "louis-vuitton"
        season:   e.g. "spring-2023", "fall-2023"
        city:     city slug for WWD URLs, default "paris"

    Returns:
        dict with parse_status "ok" or "failed". On failure includes "error" key.
        Never raises — all errors are captured in the return dict.
    """
    base = {
        "source": source,
        "designer": designer,
        "season": season,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        url = _build_url(source, designer, season, city)
    except ValueError as e:
        return {**base, "parse_status": "failed", "error": str(e)}

    base["url"] = url
    if source == "vogue":
        parsed = _fetch_vogue(url)
    else:
        domain = _DOMAINS.get(source, "")
        html = _fetch_html(url, domain)
        if not html:
            return {**base, "parse_status": "failed", "error": "fetch failed — no HTML returned"}
        parsed = _PARSERS[source](html)

    if parsed["parse_status"] == "ok":
        parsed["word_count"] = len(parsed["body_text"].split())

    return {**base, **parsed}
