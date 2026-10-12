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

### 3. Deduplication & Master Catalog Assembly
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
