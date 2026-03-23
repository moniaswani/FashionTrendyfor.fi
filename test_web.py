from playwright.sync_api import sync_playwright
import json

def scrape_article(article_url):
    base = "https://www.archivebuttons.com/articles?article="
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base + article_url, wait_until="networkidle")

        # Access iframe content
        iframe = page.frame_locator("iframe").first
        
        # Fix: use .first to avoid strict mode violation
        author = iframe.locator("[data-testid='BylineName']").first.inner_text()
        date = iframe.locator("time").first.inner_text()
        paras = iframe.locator("article p").all_inner_texts()
        # Filter out any consent/ad paragraph noise
        paras = [p for p in paras if len(p) > 50]

        browser.close()
        return {
            "url": article_url,
            "author": author,
            "date": date,
            "paragraphs": paras
        }

# Example usage
urls = [
    "https://www.vogue.com/fashion-shows/fall-2023-ready-to-wear/chanel",
]

for url in urls:
    data = scrape_article(url)
    print(json.dumps(data, indent=2))