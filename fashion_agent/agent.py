"""
Fashion Analysis Agent — CLI entrypoint.

Usage:
    python agent.py --designer chanel --season spring-2025
    python agent.py --designer chanel --season spring-2025 --sources vogue
    python agent.py --designer chanel --season spring-2025 --city milan
    python agent.py --designer chanel --season spring-2025 --no-cache
    python agent.py --designer chanel --season spring-2025 --dry-run

Required env vars:
    ANTHROPIC_API_KEY          Claude API key
    AWS_REGION                 default: eu-west-2
    AWS credentials            standard boto3 chain
"""

import argparse
import json
import sys

from analyst import analyze


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fashion runway analysis agent — combines editorial + visual data via Claude."
    )
    parser.add_argument(
        "--designer",
        required=True,
        help="Designer slug e.g. chanel, louis-vuitton, balenciaga",
    )
    parser.add_argument(
        "--season",
        required=True,
        help="Season in format spring-YYYY or fall-YYYY e.g. spring-2025, fall-2023",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["vogue", "wwd"],
        default=None,
        help="Sources to scrape (default: both vogue and wwd)",
    )
    parser.add_argument(
        "--city",
        default="paris",
        help="City slug for WWD URL (default: paris). Use e.g. milan, new-york, london",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force re-scrape and re-analyze, ignore all cached data",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse articles, print summary and prompt preview — do not call Claude or write to cache",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        default=None,
        help="Additional article URLs to scrape via archivebuttons (any publication)",
    )

    args = parser.parse_args()

    print(f"\nFashion Analysis Agent")
    print(f"{'─' * 40}")
    print(f"Designer : {args.designer}")
    print(f"Season   : {args.season}")
    print(f"Sources  : {args.sources or ['vogue', 'wwd']}")
    print(f"City     : {args.city}")
    if args.urls:
        print(f"Extra URLs: {len(args.urls)} custom article(s)")
    if args.dry_run:
        print(f"Mode     : dry-run (no Claude, no cache writes)")
    elif args.no_cache:
        print(f"Mode     : no-cache (force re-scrape + re-analyze)")
    print(f"{'─' * 40}\n")

    try:
        result = analyze(
            designer=args.designer,
            season=args.season,
            sources=args.sources,
            city=args.city,
            no_cache=args.no_cache,
            dry_run=args.dry_run,
            custom_urls=args.urls,
        )
    except EnvironmentError as e:
        print(f"\nConfiguration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'═' * 40}")
    print("Result:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
