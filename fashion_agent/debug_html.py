"""
Debug helper — fetches raw HTML from a source and saves it to disk.
Use this to inspect what a site is actually returning when parsing fails.

Usage:
    python debug_html.py --source vogue --designer chanel --season spring-2023
    python debug_html.py --source wwd   --designer chanel --season spring-2023

Output: saves {source}_{designer}_{season}.html in the current directory.
Open the file in a browser or text editor to inspect the actual HTML.
"""

import argparse

from scraper import _build_url, _fetch_html, _DOMAINS


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and save raw HTML for debugging")
    parser.add_argument("--source", required=True, choices=["vogue", "wwd"])
    parser.add_argument("--designer", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--city", default="paris")
    args = parser.parse_args()

    url = _build_url(args.source, args.designer, args.season, args.city)
    domain = _DOMAINS[args.source]

    print(f"URL    : {url}")
    print(f"Domain : {domain}")
    print(f"Fetching...")

    html = _fetch_html(url, domain)

    if not html:
        print("FAILED — no HTML returned (check network / URL)")
        return

    filename = f"{args.source}_{args.designer}_{args.season}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Saved  : {filename}  ({len(html):,} chars)")
    print(f"\nQuick check — first 500 chars of body:")
    print("-" * 40)
    print(html[:500])


if __name__ == "__main__":
    main()
