# 🤖 Scrapers & Data Pipeline Guide

This document describes the data ingestion pipeline, scraper implementations, text parsing algorithms, and execution workflows in the `scrapers/` directory.

---

## 🏗️ Scraper Architecture

The scrapers are structured using an Object-Oriented design rooted in [`BaseScraper`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/base_scraper.py):

```python
class BaseScraper:
    def __init__(self, source_name: str, output_dir: str):
        ...
    def run(self) -> List[Dict]:
        """Orchestrates scraping lifecycle: init, fetch, parse, store."""
        ...
    def fetch_listings(self) -> List[Dict]:
        """Source-specific extraction logic."""
        raise NotImplementedError
    def clean_and_normalize(self, raw_items: List[Dict]) -> List[Dict]:
        """Parses raw items into unified format."""
        ...
```

### Key Scraper Implementations

1. **Facebook Scraper (`scrapers/facebook/`)**:
   - Parses Facebook Group real estate feeds using headless browser sessions.
   - Extracts author names, group IDs, post text, uploaded image URLs, and relative time expressions (*"2 hrs ago"*, *"երեկ"*).
   - Resolves permalinks to individual posts for direct source access.

2. **List.am Scraper (`scrapers/listam/`)**:
   - Queries real estate categories on List.am.
   - Parses structured metadata (price, area, room count, floor, building type) from classified detail pages.
   - Extracts phone numbers and dealer/private owner designations.

---

## 🧹 Normalization & Processing (`scrapers/processors/`)

After raw scraping, listing items undergo processing through modular processors:

### 1. Housing & Location Parser (`scrapers/utilities/location_and_housing_parser.py`)
- **Location Entity Resolution**:
  - Regular expressions match Armenian (*Կենտրոն, Արաբկիր, Դավթաշեն*), Russian (*Кентрон, Арабкир*), and English names.
  - Resolves non-Yerevan regions including Kotayk, Ararat, Armavir, Gegharkunik, Lori, and Shirak.
- **Pricing & Currency Standardization**:
  - Automatically identifies dollar signs (`$`), Armenian dram symbols (`֏`, `դրամ`, `драм`), and numeric separators.
  - Computes `amount_usd` and `amount_amd` based on the prevailing reference exchange rate.
- **Zoning Classification**:
  - Evaluates Armenian keyword context:
    - **Residential / Housing**: Matches *բնակելի, տնամերձ, տուն կառուցելու, ИЖС*.
    - **Agricultural / Farming**: Matches *գյուղնշանակության, պտղատու այգի, վարելահող, ջերմոց*.
    - **Negative Guards**: Prevents false agricultural classification when listings describe nearby public parks (*սիրահարների այգի, զբոսայգի, օղակաձև այգի*).
- **Size & Room Counts**:
  - Detects square meters (*քմ, кв.м, sq.m, m²*).
  - Normalizes room numbers (*1 սենյակ, 2-սենյականոց, 3-room*).

### 2. Time Parser (`scrapers/utilities/time_utils.py`)
- Resolves relative timestamps into deterministic Unix epoch timestamps (`creation_timestamp`).
- Handles English (*"3 hours ago"*, *"yesterday"*) and Armenian (*"3 ժամ առաջ"*, *"երեկ"*) relative time tokens.

### 3. Storage & Data Regulation (`scrapers/utilities/storage.py`)
- **Transactional SQLite Database (`scrapers/data/listings.db`)**:
  - Replaces scattered, heavy JSON files with indexed, atomic SQL storage.
  - Automatically deduplicates and upserts records based on metadata completeness scores.
  - Indexes on `(is_active, creation_timestamp)`, `source`, and `(property_category, listing_type)`.
- **TTL Retention Policy**:
  - Automatically deactivates stale listings older than 60 days to prevent infinite data bloat.
- **Git Repository Size Regulation**:
  - Raw scraping dumps, browser sessions, and local SQLite databases are strictly excluded via `.gitignore`.
  - Only cleaned, minified public display catalogs (`master_listings_json/`) are synced to GitHub Pages.

### 4. Deduplication & Master Catalog Assembly
- Eliminates duplicate posts scraped from overlapping groups or re-posted classifieds.
- Writes the combined, sorted master catalog to:
  `scrapers/processors/master_listings_json/all_for_sale_rent.json`

---

## 🚀 Running the Pipeline

To execute the data collection and aggregation pipeline:

```bash
# Run full aggregation pipeline
python run_pipeline.py
```

### Automation & Scheduling
The pipeline can be scheduled via Cron (Linux/macOS) or Windows Task Scheduler:

```bash
# Example crontab entry: run every 3 hours
0 */3 * * * cd /path/to/repo && /path/to/repo/.venv/bin/python run_pipeline.py >> pipeline.log 2>&1
```

---

## 🛡️ Anti-Bot Protections & Real User Emulation Guidelines

External real estate platforms (primarily **List.am** and **Facebook**) enforce active anti-bot systems: Cloudflare Turnstile challenges, browser fingerprinting, rate limiting, and account checkpointing. To prevent automated bans during development, testing, and production runs, all browser interactions must act like genuine human users.

### 1. Browser Stealth Architecture
- **Undetected ChromeDriver (`undetected_chromedriver`)**:
  - Used for List.am scraping; matched directly to installed Chrome major version (`get_installed_chrome_major_version()`).
  - Launches in subprocess mode (`use_subprocess=True`) with automation flags removed (`--disable-blink-features=AutomationControlled`, `--no-sandbox`).
- **Persistent User Profiles**:
  - Browser sessions use persistent user data directories (`USER_DATA_DIR` under `~/Desktop/fb-scraper-project/`).
  - Never use clean disposable sessions for authenticated workflows; persistent profiles preserve validated cookies (`c_user`, `cf_clearance`).
- **Prohibition of Raw HTTP Requests**:
  - Never send raw `curl`, `requests`, `urllib`, or `fetch` calls to List.am or Facebook. Cloudflare blocks them immediately with HTTP 403. Always use the configured browser drivers or inspect local SQLite records.

### 2. Behavioral Humanization (`scrapers/utilities/browser_humanizer.py` & `listam_utils.py`)
- **Bézier Curve Mouse Dynamics (`move_mouse_bezier`)**:
  - Mouse pointer moves along randomized cubic Bézier curves with eased speed trajectories across 20–30 sub-steps (10–25ms delay).
  - Clicks target random offsets within buttons/links (20%–80% bounding box), avoiding artificial (0, 0) or dead-center clicks.
- **Natural Smooth Scrolling (`human_scroll`, `smooth_scroll`)**:
  - Incremental chunk scrolling (350–700 px) with 12–20ms step delays.
  - Injects natural backward scroll-backs (5%–15% probability of scrolling up 100–200 px) simulating reading pauses.
- **Multitasking Simulation (`simulate_random_tab_activity`)**:
  - 20% probability of opening an auxiliary tab, dwelling for 1.0–2.5 seconds, and switching back.
- **Randomized Jitter Delays**:
  - 1.5s to 3.5s randomized intervals between page navigations and item visits.
- **Global Rest Breaks (`check_global_break`)**:
  - 30s to 180s natural pauses every 8 to 12 minutes of active scraping.

### 3. Checkpoint Handling
- **Cloudflare Loops (`handle_cloudflare_loop`)**:
  - Automatically identifies "Just a moment..." and "Verify you are human" screens, pausing for user clearance without spamming requests.
- **Facebook Authentication (`wait_for_facebook_login`)**:
  - Inspects `c_user` cookie and login elements. Prompts for manual login if the session expires, strictly avoiding automated credential input.

