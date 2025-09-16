import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

def scrape_images_from_page(page_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ImageScraper/1.0; +https://example.com/bot)"
    }

    # Parse page URL to build folder name
    parsed_page = urlparse(page_url)
    if parsed_page.netloc == "nowfashion.com":
        path_after = parsed_page.path.strip('/')
    else:
        path_after = parsed_page.netloc + parsed_page.path
    folder_name = f"images_{path_after.replace('/', '_')}"
    os.makedirs(folder_name, exist_ok=True)

    # Fetch HTML
    response = requests.get(page_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch page: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # Locate the specific block by class
    container = soup.find(
        "div",
        class_="entry-content alignfull wp-block-post-content is-layout-flow wp-container-core-post-content-is-layout-a77db08e wp-block-post-content-is-layout-flow"
    )

    if not container:
        print("Target container not found.")
        return

    # Get only the images inside the container
    img_tags = container.find_all('img')

    print(f"Found {len(img_tags)} image tags in target block. Processing...")

    for img in img_tags:
        src = img.get('src')
        if not src:
            continue

        img_url = urljoin(page_url, src)
        if img_url.startswith("data:"):
            continue

        try:
            img_resp = requests.get(img_url, headers=headers)
            img_resp.raise_for_status()

            parsed_img = urlparse(img_url)
            filename = os.path.basename(parsed_img.path)
            if not filename:
                filename = f"image_{hash(img_url)}.jpg"

            filepath = os.path.join(folder_name, filename)

            with open(filepath, 'wb') as f:
                f.write(img_resp.content)
                print(f"Saved: {filepath}")

        except Exception as e:
            print(f"Error downloading {img_url}: {e}")

if __name__ == "__main__":
    page_url = "https://nowfashion.com/louis-vuitton-ready-to-wear-spring-summer-2025-paris/"
    scrape_images_from_page(page_url)
