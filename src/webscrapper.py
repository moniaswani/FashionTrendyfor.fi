import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ImageScraper/1.0; +https://example.com/bot)"
}


def scrape_images_from_page(page_url: str):
    print(f"\nScraping: {page_url}")

    # Build folder name from URL
    parsed_page = urlparse(page_url)
    path_after = parsed_page.path.strip("/") or parsed_page.netloc
    subfolder_name = path_after.replace("/", "-")
    folder_name = os.path.join("images", subfolder_name)

    # ✅ Skip if already scraped
    if os.path.exists(folder_name) and os.listdir(folder_name):
        print(f"⏭️ Skipping (already scraped): {folder_name}")
        return

    os.makedirs(folder_name, exist_ok=True)

    # Fetch HTML
    response = requests.get(page_url, headers=HEADERS, timeout=15)
    if response.status_code != 200:
        print(f"❌ Failed to fetch page: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    container = soup.find(
        "div",
        class_="entry-content alignfull wp-block-post-content is-layout-flow "
               "wp-container-core-post-content-is-layout-a77db08e "
               "wp-block-post-content-is-layout-flow"
    )

    if not container:
        print("⚠️ Target container not found.")
        return

    img_tags = container.find_all("img")
    print(f"Found {len(img_tags)} images")

    for idx, img in enumerate(img_tags, start=1):
        src = img.get("src")
        if not src or src.startswith("data:"):
            continue

        img_url = urljoin(page_url, src)

        try:
            img_resp = requests.get(img_url, headers=HEADERS, timeout=15)
            img_resp.raise_for_status()

            parsed_img = urlparse(img_url)
            filename = os.path.basename(parsed_img.path) or f"image_{idx}.jpg"
            filepath = os.path.join(folder_name, filename)

            if os.path.exists(filepath):
                continue  # optional: skip existing files

            with open(filepath, "wb") as f:
                f.write(img_resp.content)

            print(f"✅ Saved: {filepath}")

        except Exception as e:
            print(f"❌ Error downloading {img_url}: {e}")


def load_urls_from_txt(file_path: str) -> list[str]:
    with open(file_path, "r") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


if __name__ == "__main__":
    url_file = "urls.txt"
    page_urls = load_urls_from_txt(url_file)

    print(f"Loaded {len(page_urls)} URLs")

    for url in page_urls:
        try:
            scrape_images_from_page(url)
        except Exception as e:
            print(f"❌ Failed scraping {url}: {e}")
