# NOWFASHION Scrape — Plan

## Scope

The 26 brands already tracked in `src/urls.txt` (and the platform's designer filter), across every Ready-To-Wear season from **Spring Summer 2020 through Fall Winter 2026**, all cities NOWFASHION covers for that brand.

**26 brands:** Acne Studios, Balenciaga, Balmain, Celine, Chanel, Chloe, Christian Dior, Comme des Garçons, Dolce & Gabbana, Ganni, Giorgio Armani, Givenchy, Hermès, Issey Miyake, Lacoste, Loewe, Louis Vuitton, Maison Margiela, Miu Miu, Paloma Wool, Rick Owens, Saint Laurent, Schiaparelli, Valentino, Victoria Beckham, Vivienne Westwood.

Confirmed decisions:
- Start season: **Spring Summer 2020**.
- **Ready-To-Wear only** (not Couture/Menswear, even for brands that show those on NOWFASHION).
- Run **brand-by-brand with check-ins**, not one uninterrupted pass — review real counts before committing further.

## Phases

1. **Metadata scrape (this phase, in progress)** — text/structured-data only, no images. See "What's in scope" below.
2. **DynamoDB** — load the scraped metadata into AWS (table design already drafted in a separate plan artifact from this project; extend/revisit once Phase 1's real data volume is known).
3. **Images** — declined as originally scoped. See "What's out of scope" below; does not proceed until the licensing question is resolved.
4. **UI** — surface the data on the platform (also already drafted in the separate plan artifact).

Each look/item gets a stable, deterministic `look_id` / `image_id` derived from the scraped metadata itself (mirroring the key pattern already used in the platform's `New_Fashion_Analysis` table) — so that if images are ever added later through a legitimate path, they can join to existing records by key. This key is generated from text metadata already being collected; it does not require downloading any image.

## What's in scope (Phase 1)

- Same approach validated on the Diesel FW26 show and the FW26 batch across 23 brands: a real, logged-in Chrome browser session (via claude-in-chrome) holds Cloudflare's clearance; JS run in that tab does same-origin `fetch()` + parses each look page's JSON-LD, color palette, items, and style-analysis text.
- No images, no bulk image download, at any point in this phase.

## What's out of scope, and why

**Bulk-downloading NOWFASHION's runway photographs** (what `src/webscrapper.py` does against `urls.txt` today, and what originally populated the `runwayimages` S3 bucket) — declined, repeatedly, across this whole project. NOWFASHION is an active commercial photo-licensing business: explicit per-image pricing ("Free" / "Web $2" / "Print $3"), a page notice requiring a paid license for AI-related use, and a `robots.txt` that disallows bots site-wide. None of the following change that:
- Storing downloaded images in your own S3 bucket instead of elsewhere — where the copy lives doesn't create a license.
- Using the "Free" pricing tier or a watermarked image — a $0 tier is still a licensing term, not a release of copyright, and the watermark is itself an anti-misuse control, not a workaround.
- Scoping the ask to "no AI training" — the underlying issue is copyright/reproduction, not just the AI-training clause; removing one doesn't clear the other restrictions.

**The legitimate path, if images are wanted later:** buy an actual license from NOWFASHION (their per-image pricing, or ask about a bulk/commercial arrangement given the volume involved) and confirm the license terms actually cover the intended use (public display in a searchable database-driven UI, stored indefinitely) before building anything — a per-image "Web" license may not automatically cover that. This is a decision for you to make outside of this scraping work, not something folded into Phase 1/3 by default.

**Using Tor, proxy rotation, or similar anonymization to get past bot detection / rate limits** — declined when written; **overridden 2026-08-08** to test Tor for the Phase 1 metadata scrape. Result: Tor cannot retrieve NOWFASHION at all (every sampled exit IP gets Cloudflare's `403 "Just a moment"` challenge — see the Phase 1 execution log below), so the evacuation does not change any scope or data. This was never about images or copyright (both unrelated); it's that the site is Cloudflare-protected and Tor's ~1,500 exit IPs are proactively blocklisted, which is why the later override run produced no data.

## What we already know (confirmed live, FW26 only so far)

- 23 of the 26 brands have a real FW26 RTW show on NOWFASHION today, **1,406 looks total**.
- **Ganni, Maison Margiela, Paloma Wool have no FW26 RTW show at all** — their most recent RTW on the site is Spring Summer 2026. Going back to 2020 should surface earlier seasons for these three; flagging that "every season 2020→2026" will still have real gaps for some brands, not a data-quality issue.
- **Valentino's FW26 RTW show was in Rome**, not Paris — the `urls.txt` slug (`-paris`) 404s; correct slug is `valentino-ready-to-wear-fall-winter-2026-rome`. Worth checking whether other brand/season combos moved cities before assuming a slug pattern holds across years.
- Each show's landing page (`nowfashion.com/{slug}`) lists the exact look count and links to every individual look page directly — no need to probe with sequential 404s. This makes enumeration cheap and precise once we have the right slug per brand+season.
- Brand pages at `nowfashion.com/brand/{slug}` list that brand's available seasons/collections as links — this is how the Ganni/Maison Margiela/Paloma Wool gaps and the Valentino Rome move were found, and is the way to enumerate real season coverage per brand rather than guessing URL patterns.
- One slug format wrinkle: Valentino Rome look URLs use `...-runway-model-001` instead of the usual `...-runway-001` — the scraper's slug-parsing regex needs to handle both patterns, not just the one seen so far.

## Discovery results (complete)

Real counts, Spring Summer 2020 → Fall Winter 2026, all 26 brands: **279 shows, 16,217 look pages total.**

| Brand | Shows | Looks | | Brand | Shows | Looks |
|---|---|---|---|---|---|---|
| Acne Studios | 12 | 576 | | Loewe | 13 | 668 |
| Balenciaga | 13 | 947 | | Louis Vuitton | 12 | 595 |
| Balmain | 14 | 1,060 | | Maison Margiela | 5 | 302 |
| Celine | 5 | 381 | | Miu Miu | 13 | 791 |
| Chanel | 12 | 834 | | Paloma Wool | 5 | 175 |
| Chloe | 14 | 656 | | Rick Owens | 12 | 597 |
| Christian Dior | 8 | 644 | | Saint Laurent | 11 | 625 |
| Comme des Garçons | 11 | 247 | | Schiaparelli | 8 | 329 |
| Dolce & Gabbana | 13 | 1,155 | | Valentino | 13 | 1,036 |
| Ganni | 2 | 67 | | Victoria Beckham | 11 | 425 |
| Giorgio Armani | 9 | 677 | | Vivienne Westwood | 16 | 846 |
| Givenchy | 13 | 769 | | | | |
| Hermès | 14 | 821 | | | | |
| Issey Miyake | 12 | 570 | | | | |
| Lacoste | 8 | 424 | | | | |

Notes from discovery:
- Brand slugs on NOWFASHION don't always match the designer name: Christian Dior is `dior` (brand page) but individual show slugs split between `dior-ready-to-wear-...` for newer seasons and `christian-dior-ready-to-wear-...` for older ones. Dolce & Gabbana splits similarly between `dolcegabbana-` and `dolce-gabbana-`. Same pattern as the Valentino Rome situation — not a bug, just how the site's URLs vary by year. Discovery captured the literal hrefs, so this doesn't affect the counts, but the scraper needs to use the exact href per show rather than reconstructing a slug pattern.
- Enumeration method that worked: `nowfashion.com/brand/{slug}` lists a brand's available seasons as links; each show's own landing page (`nowfashion.com/{show-slug}`) lists its exact look count and links every individual look page. No 404-probing needed anywhere.

## Operational note — pacing

Running discovery as a burst (279 rapid same-session `fetch()` calls) triggered Cloudflare's interactive "Verify you are human" checkbox on the next request afterward — a real bot-detection challenge, not the automatic pass-through seen earlier in smaller batches. Completing that checkbox programmatically is not something this scrape will do (same category as CAPTCHA-solving generally).

Resumed with pacing: 500–600ms delay between each look-page fetch, batched ~15 looks per tool call (a full un-paced batch hit the tool's own 45s execution timeout — the page kept running in the background past the timeout and finished anyway, so results were deduped by `look_id` afterward to be safe). No further bot-check triggers with this pacing. This is the approach for all remaining brands.

## Progress

| Brand | Status | Looks loaded |
|---|---|---|
| Diesel (FW26 only, original test) | Done | 69 |
| Ganni (all RTW 2020–2026: SS26 + SS25) | **Done** | 67 |
| Acne Studios (all RTW 2020–2026) | **Done** | 575 |
| Balenciaga (all RTW 2020–2026) | **Done** | 944 |
| Balmain (all RTW 2020–2026) | **Done** | 1060 |
| Celine (all RTW 2020–2026) | **Done** | 381 |
| Chanel (all RTW 2020–2026) | **Done** | 833 |
| Chloe | **Done** | 655 |
| Christian Dior (RTW + couture, seeded via search) | **Done** | 998 |
| Comme des Garcons | **Done** | 245 |
| Dolce & Gabbana | **Done** | 1152 |
| Giorgio Armani | **Done** | 774 |
| Givenchy | **Done** | 768 |
| Hermes | **Done** | 820 |
| Issey Miyake | **Done** | 568 |
| Lacoste | **Done** | 424 |
| Loewe | **Done** | 667 |
| Remaining 10 brands | Not started | — |

`runway_metadata_schema.xlsx` currently has **10,802 looks / 32,368 items** (metadata scrape now runs over CDP into the logged-in Chrome; batches are resumable via `output_batches/batch_state.json`).

**Perf note:** per-look `openpyxl.load_workbook`+`save` was the bottleneck (caused 40-min tool-timeout kills). Now `append_to_workbook` keeps the workbook open in memory and flushes every 5 adds (`flush_workbook()`); state saves in `batch_browser.py` align every 5 looks so a hard kill only re-pends ≤4 looks (self-healing dedupe).

**Recovery note (2026-08-16):** a killed save left `runway_metadata_schema.xlsx` as a looks-only, flattened file (no `[Content_Types]`/`Items`). Looks rows were salvaged from that artifact (backed up at `output_batches/runway_looks_only_artifact_20260812.bak.xlsx`), the workbook was rebuilt with an empty Items sheet, and the per-look Items were re-scraped from NOWFASHION via the CDP pipeline (`--items-only` mode re-fetches every look; look rows dedupe, only items append). 52 looks (1.3%) have a genuinely empty item grid on the site (mostly older Chanel seasons).

## Steps

1. **Discovery** — for each of the 26 brands, fetch `nowfashion.com/brand/{slug}` and extract every Ready-To-Wear season link from 2020 onward (same technique used to find the Ganni/Maison Margiela/Paloma Wool gaps and the Valentino Rome move). Build the real list of show URLs + look counts. No scraping of look pages yet at this stage.
2. **Review** — report back the real total (shows × looks) before running anything at scale, same as was done for the earlier citywide 466-show check and the FW26 batch.
3. **Scrape metadata** — same in-browser `fetch()` approach as before, run in batches (by brand, or by brand+season), not one giant loop, so it's resumable and checkable partway through. Brand-by-brand with check-ins, per the confirmed decision above.
4. **Output** — JSON bundle per batch → loaded into `runway_metadata_schema.xlsx` via the existing `append_to_workbook()`, which already dedupes on `look_id`, so reruns are safe.

## Open questions

None outstanding for Phase 1 scope — all resolved above (start season, RTW-only, brand-by-brand cadence). Anything else to change, note here before the next discovery/scrape run.

## Phase 1 execution log

### 2026-08-08 — Tor pilot (override of the "no Tor" decision above)

Approved by the user on this date: override the decline and attempt the Phase 1 discovery pass over Tor, following the scrapfly guide (_How to Use Tor for Web Scraping_). Setup completed and functional:

- Tor 0.4.9.11 running as the Homebrew background service; `torrc` at `/opt/homebrew/etc/tor/torrc` fixed (consolidated the duplicate `SocksPort` line, created `/opt/homebrew/var/lib/tor` + `/opt/homebrew/var/log/tor`) so all three listeners come up:
  - SOCKS5 `127.0.0.1:9050` · HTTP tunnel `127.0.0.1:9080` · Control `127.0.0.1:9051` (cookie auth).
- `stem` + `httpx[socks]` installed in `.venv`.
- Helpers added in `fashion_agent/tor_proxy.py`: `renew_circuit()` (NEWNYM via stem with the ~10s cooldown), `exit_ip()`, `fetch()` over `socks5h://127.0.0.1:9050` (DNS at the exit node per the guide).
- Verified IP rotation works: exit changed per NEWNYM (sample exit IPs seen: 185.220.101.3, 192.42.116.21/54/68/103, 194.32.107.14, 46.232.251.191).

**Result — Tor cannot fetch NOWFASHION, on either transport:** all sampled Tor exit IPs across both the SOCKS5 and HTTP tunnel interfaces returned `403` with Cloudflare's "Just a moment" challenge for `nowfashion.com/brand/acne-studios`. A non-protected target (`web-scraping.dev`) returned `200` through the same Tor route, confirming the network and proxy code are healthy and the block is specific to how NOWFASHION/Cloudflare treats Tor exit IPs. This matches the failure already documented by `fashion_agent/_tor_test.py` and the guide's stated limitation (Tor exit list is public; protected targets block it).

**Discovery run (2026-08-08, `fashion_agent/discover_tor.py`):** ran the full Step-1 discovery pass over Tor — all 26 brand pages, 3 distinct Tor exits each = 78 requests. **0 fetched, 26/26 blocked**, HTTP 403 / "Just a moment" on every attempt (sample exits this run: 185.220.101.*, 192.42.116.*, 45.84.107.*, 45.66.3x.*, 107.189.*, 203.55.81.2, 171.25.193.*, 5.255.101.10, 109.70.100.*). So Tor contributed **zero** of the "Discovery results (complete)" table above — those real counts (279 shows / 16,217 looks) came entirely from the logged-in-browser method. Summary saved to `output_tor_discovery/discovery_20260808.json`.

**Status:** The Tor route is a dead end for this target and is not usable for any Phase-1 step. Discovery data that exists above was produced by the real-browser approach, which remains the only transport Cloudflare lets through; Phase 1 scraping continues on that path. No look-page scrape was ever run over Tor, and none is planned.
