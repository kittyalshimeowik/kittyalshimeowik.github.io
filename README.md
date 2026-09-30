# 🇦🇲 Armenia Real Estate Hub

An end-to-end real estate aggregation platform and interactive dashboard for the Armenian housing market. This repository contains the scraping engine, normalization pipelines, master deduplication processor, automated test suites, and responsive web interface for discovering properties across Armenia (Yerevan, Kotayk, Shirak, Lori, Tavush, and regional municipalities).

---

## Table of Contents
- [Overview](#overview)
- [Architecture & Data Flow](#architecture--data-flow)
- [Repository File Structure](#repository-file-structure)
- [Scraping & Ingestion Engine](#scraping--ingestion-engine)
- [Data Normalization & Processing](#data-normalization--processing)
- [Execution & Command Line Usage](#execution--command-line-usage)
- [Running the Test Suite](#running-the-test-suite)
- [Web Interface & Frontend Features](#web-interface--frontend-features)
- [Local Development & Serving](#local-development--serving)

---

## Overview

The **Armenia Real Estate Hub** collects, cleans, normalizes, deduplicates, and serves live property listings from Armenia's primary housing markets—primarily **Facebook Real Estate Groups** and **List.am**. 

The system features:
* **Multi-Source Scraping**: Automated browser scrapers utilizing Playwright for Facebook GraphQL traffic and `undetected-chromedriver` for List.am with anti-bot evasion.
* **Domain-Specific NLP & Regex Parser**: Multi-lingual extractor supporting Armenian, Russian, and English for prices, currencies, square meter areas, room counts, floor numbers, phone numbers, and neighborhood landmarks.
* **Two-Tier Deduplication**: High-speed phone + specification matching combined with bucketed fuzzy text similarity (`SequenceMatcher`) to merge duplicates while retaining the richest listing metadata.
* **Modern Lightweight Frontend**: Zero-dependency vanilla JavaScript and responsive CSS with fluid `clamp()` sizing, infinite scrolling, skeleton placeholders, bilingual localization (English / Armenian), and smart primary sorting.

---

## Architecture & Data Flow

```
[ Facebook Groups ]          [ List.am Categories ]
   (Playwright)             (Undetected-Chromedriver)
         │                             │
         ▼                             ▼
  scrapers/facebook/            scrapers/listam/
  housing_posts_data/           housing_posts_data/
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
       scrapers/processors/generate_site_data.py
         ├── Parse & Validate Text (housing_parser.py)
         ├── Standardize Locations (location_data.py)
         ├── Convert Currencies (AMD / USD @ Daily Rate)
         ├── Standardize UTC Timestamps (time_utils.py)
         ├── Deduplicate (Exact Phone/Specs + Bucketed Fuzzy)
         └── Prune Payloads for Display Feed
                        │
                        ▼
       scrapers/processors/master_listings_json/
               all_for_sale_rent.json
                        │
                        ▼
       Interactive Web UI (index.html + script.js)
```

---

## Repository File Structure

```text
armenia-real-estate-website/
├── .gitignore
├── groups_config.json              # Active Facebook Group target IDs and configurations
├── index.html                      # Semantic, responsive single-page web application
├── README.md                       # Comprehensive system and pipeline documentation
├── run_pipeline.py                 # Master orchestration pipeline (scrape -> process -> sync)
├── run_tests.py                    # Automated test runner discovering all __tests__ suites
├── script.js                       # Client-side catalog manager, filter engine & UI rendering
├── style.css                       # Modern CSS design system with fluid clamp() layout
├── translations.js                 # Bilingual dictionary and geographic translations module
│
└── scrapers/                       # Scraping and processing subsystem
    ├── base_scraper.py             # Abstract Base Class defining scraper contracts
    │
    ├── facebook/                   # Facebook Group scraper module
    │   ├── fb_scraper.py           # Playwright-based scraper capturing GraphQL post payloads
    │   ├── fb_session/             # Persistent browser user-data & authenticated session profile
    │   ├── groups_metadata/        # Per-group benchmark stats and extraction metadata
    │   ├── housing_posts_data/     # Extracted Facebook post JSON files
    │   ├── utilities/              # Facebook-specific storage and ID decoding tools
    │   │   ├── fb_metadata_storage.py
    │   │   └── fb_utils.py         # Login checks, DOM helpers, and GraphQL payload extraction
    │   └── __tests__/              # Unit tests for Facebook scraping utilities
    │       ├── test_fb_housing_extractor.py
    │       ├── test_fb_metadata_storage.py
    │       └── test_fb_utils.py
    │
    ├── listam/                     # List.am scraper module
    │   ├── list_am_scraper.py      # Undetected-Chromedriver scraper with humanized behavior
    │   ├── listam_config.json      # Category target mappings and runtime parameters
    │   ├── housing_posts_data/     # Extracted List.am category JSON files
    │   ├── utilities/              # List.am specific modular utilities
    │   │   └── listam_utils.py     # Date parsing, humanized scroll, anti-bot helpers, file I/O
    │   └── __tests__/              # Unit tests for List.am scraper components
    │       └── test_listam_scraper.py
    │
    ├── processors/                 # Master data consolidation and site data generator
    │   ├── cleanup_master_listings.py # Post-processing validator and deduplication tool
    │   ├── dedup_cache.json        # Persistent listing signatures cache
    │   ├── dedup_utils.py          # Shared deduplication, ghost detection, scoring, & price helpers
    │   ├── generate_site_data.py   # Consolidates, reparses, deduplicates, and converts currencies
    │   ├── master_listings_json/   # Output directory for consolidated web application data
    │   │   └── all_for_sale_rent.json # Primary unified feed consumed by the website
    │   └── __tests__/              # Unit tests for data generation and deduplication
    │       ├── test_cleanup_master_listings.py
    │       ├── test_data_generator.py
    │       └── test_dedup_utils.py
    │
    └── utilities/                  # Shared scraping and extraction utilities
        ├── browser_humanizer.py    # Human-like interaction behavior (scrolling, delays)
        ├── env_utils.py            # Virtualenv auto-bootstrapping & UTF-8 console output
        ├── housing_parser.py       # Domain-specific regex and NLP parser
        ├── location_data.py        # Location dictionary, regex rules & regional synonyms
        ├── time_utils.py           # Timestamp normalization and relative time parser
        └── __tests__/              # Unit tests for utilities
            ├── test_base_scraper.py
            ├── test_env_utils.py
            ├── test_location_and_parser.py
            └── test_time_utils.py
```

---

## Scraping & Ingestion Engine

### 1. Facebook Scraper (`scrapers/facebook/`)
* **Engine**: Built with **Playwright** (Chromium).
* **Interception**: Monitors and parses asynchronous Facebook GraphQL response streams (`response.text()`) to extract post text, creation dates, canonical IDs, and authors directly from the network payload without relying on fragile DOM selectors.
* **Session Persistence**: Maintains user state via `scrapers/facebook/fb_session/` to avoid login friction and bot verification challenges.

### 2. List.am Scraper (`scrapers/listam/`)
* **Engine**: Built with **`undetected-chromedriver`** and **BeautifulSoup4**.
* **Evasion**: Employs humanized cursor jitter, non-linear scrolling, random dwell pauses, and tab multitasking simulation to avoid Cloudflare/bot triggers.
* **Category Parsing**: Scrapes configured real estate sections (apartments for sale/rent, houses, land) and extracts structured attributes including floor info, square meters, building materials, and posted/renewed dates.

---

## Data Normalization & Processing

Data passes through [generate_site_data.py](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/processors/generate_site_data.py) to produce clean, high-density listing objects:

1. **Feature Extraction (`housing_parser.py`)**:
   * **Prices**: Detects numbers with Armenian Dram (`֏`, `դրամ`, `AMD`), US Dollars (`$`, `USD`, `դոլար`), and Euros (`€`, `EUR`). Excludes phone numbers, dimensions, postal codes, and calendar years (2020–2030) from false price matches.
   * **Size ($m^2$)**: Recognizes metrics such as `քմ`, `ք.մ.`, `sq.m.`, `m²`, `м²`.
   * **Rooms**: Parses room counts in Armenian (`3 սենյականոց`), Russian (`2-комн`), and English (`3 rooms`).
   * **Floors**: Captures building floor ratios (e.g., `3/5 հարկ`, `12/14`).
   * **Phones**: Sanitizes local Armenian dialing formats into standard international representation (`+374 XX XXX XXX`).
   * **Purpose & Zoning**: Classifies properties into **Housing / Residential** (apartments, residential houses, building plots) and **Agricultural** (agricultural designation, orchards, farms, greenhouses, arable land) with urban park suppression.

2. **Location Resolution (`location_data.py`)**:
   * Uses curated regex patterns to map freeform listing text to canonical districts and cities:
     * **Yerevan Districts**: Kentron / Center (bare `կենտրոն`, Mashtots, Sayat-Nova, Tumanyan, Nalbandyan, Pushkin, Argishti, Northern Ave), Arabkir (Adonts, Vratsakan, Mamikonyants, Azatutyan Ave, Babayan, Kasyan), Shengavit (Bagratunyants, 3rd Mas, Chekhov, Manandyan), Davtashen (Davitashēn, Pirumyan, Mikoyan), Ajapnyak (15th District, Shinaraner, Halabyan, Fuchik, Margaryan), Malatia-Sebastia, Nor Nork / Massiv, Avan, Erebuni, Nork-Marash, Nubarashen, Zeytun / Kanaker.
     * **Kotayk & Suburbs**: Abovyan, Nor Gyugh, Yeghvard, Jrvezh / Dzoraghbyur, Arinj, Kasagh / Proshyan, Tsaghkadzor.
     * **Ararat & Armavir**: Vagharshapat / Etchmiadzin, Ashtarak, Artashat, Vedi.
     * **Regional Hubs**: Dilijan, Gyumri, Vanadzor, Goris, Sevan, Charentsavan, Masis, Stepanavan, Martuni.

3. **Data Pruning & Ghost Record Elimination**:
   * Drops empty ghost records (`len(full_text) < 15` with zero extracted prices, sizes, rooms, or phones) during raw scraping, master compilation, and cleanup.
   * Filters out `General / Unclassified` and `Media-Only` records at generation time, reducing client payload bandwidth by ~30.7% and ensuring `all_for_sale_rent.json` contains only verified, displayable listings.
   * Eliminated orphaned `by_location/` storage slice redundancy in favor of fast in-memory client filtering.

4. **Currency Conversion**:
   * Converts all prices bidirectionally using a central reference rate (e.g. 1 USD = 364.18 AMD), storing both `amount_amd` and `amount_usd` alongside the original raw text.

5. **Two-Tier Deduplication**:
   * **Step 1 (Exact Specs & Phone)**: Matches identical phone numbers combined with matching prices, sizes, or rooms.
   * **Step 2 (Bucketed Fuzzy Match)**: Partitions listings by category and primary location, executing length-bounded `difflib.SequenceMatcher` checks to merge duplicate agency posts while preserving the highest completeness score.

---

## Execution & Command Line Usage

### Master Pipeline Orchestration
Run the entire end-to-end data pipeline using [run_pipeline.py](file:///d:/Projects/kittyalshimeowik.github.io/run_pipeline.py):

```bash
# Execute full pipeline: scrape all sources, process/deduplicate, and sync
python run_pipeline.py

# Run scraping with a max time limit per group/category (e.g., 5 minutes)
python run_pipeline.py -t 5.0

# Skip the scraping phase and directly run parsing, deduplication, and cleanup
python run_pipeline.py --no-scrape
# Short form:
python run_pipeline.py -ns

# Run scraping and processing without auto-committing/pushing to Git
python run_pipeline.py --no-push
# Short form:
python run_pipeline.py -np
```

### Standalone Data Generation & Cleanup
```bash
# Re-run site data generation from existing raw JSONs
python scrapers/processors/generate_site_data.py

# Run standalone deduplication and validation on the master JSON
python scrapers/processors/cleanup_master_listings.py
```

---

## Running the Test Suite

The repository includes a unified test runner [run_tests.py](file:///d:/Projects/kittyalshimeowik.github.io/run_tests.py) that discovers and executes all unit tests across the codebase:

```bash
python run_tests.py
```

### Test Coverage Breakdown (145 Total Tests)
* **`scrapers/utilities/__tests__/`**:
  * `test_location_and_parser.py`: Location dictionary matching, price extraction, phone normalization, size/room parsing, zoning & agricultural classification, street word boundary handling (`Bagratunyants`), and false-price rejection.
  * `test_time_utils.py`: Timestamp detection, relative time parsing (Armenian and English), epoch boundary validation.
  * `test_base_scraper.py`: BaseScraper interface, filesystem dataset loads, safe float parsing.
  * `test_env_utils.py`: Cross-platform virtualenv detection, UTF-8 console output reconfig, and project root discovery.
* **`scrapers/processors/__tests__/`**:
  * `test_data_generator.py`: Currency conversion, hash generation, deduplication logic, display pruning, master files filtering (ghosts & unclassified items), and sorting.
  * `test_cleanup_master_listings.py`: Record completeness scoring, phone+spec signatures, ghost record filtering, unclassified elimination, and duplicate cleaning.
  * `test_dedup_utils.py`: Ghost record heuristics, valid display categorization, Unicode NFKC text normalization, completeness scoring, deterministic MD5 hashing, canonical ID extraction, and price conversion.
* **`scrapers/facebook/__tests__/`**:
  * `test_fb_housing_extractor.py`: Multilingual text parsing, comma/dot price handling, room counts.
  * `test_fb_metadata_storage.py`: Benchmark JSON storage and analytical metrics tracking.
  * `test_fb_utils.py`: GraphQL payload unwrapping, story ID extraction, login state detection, relative time DOM lookups.
* **`scrapers/listam/__tests__/`**:
  * `test_listam_scraper.py`: Category config loading, date footer regex extraction, SafeFloatContext behavior.

---

## Web Interface & Frontend Features

The frontend is a fast, responsive static web application located at [index.html](file:///d:/Projects/kittyalshimeowik.github.io/index.html) with logic in [script.js](file:///d:/Projects/kittyalshimeowik.github.io/script.js) and styles in [style.css](file:///d:/Projects/kittyalshimeowik.github.io/style.css).

### Key Highlights
1. **Option A: Smart Primary Sort**:
   * Single clean dropdown with automatic background tie-breaking:
     * **Newest**: Chronological (`creation_timestamp` descending), tie-broken by lower price.
     * **Price: low to high**: Primary sort by ascending price; tie-broken by newest listing date, then larger size.
     * **Price: high to low**: Primary sort by descending price; tie-broken by newest listing date, then larger size.
     * **Size: large to small**: Primary sort by descending area ($m^2$); tie-broken by lower price, then newest listing date.
     * **Size: small to large**: Primary sort by ascending area ($m^2$); tie-broken by lower price, then newest listing date.
   * Null values (missing price or size) sort consistently to the bottom.

2. **Clean Currency & Rate Presentation**:
   * Direct primary price display in AMD (֏) or USD ($) without redundant secondary bracketed text.
   * Default currency automatically synchronizes with language selection (USD for English, AMD for Armenian) on initial load, language change, and filter reset, while remaining manually customizable.
   * In English mode (or USD selected), price per square meter pill displays formatted as **`$/m²`** (e.g. `$1,250/m²`). In Armenian mode, displays as `${rate} ֏/ քմ`.

3. **Clickable Card Rows & Centered Action**:
   * Entire card row acts as an accessible clickable link (`window.open(item.url, '_blank')`).
   * Protected against accidental triggers when dialing phone numbers (`tel:`) or highlighting text.
   * Centered "View original post" button with hover arrow micro-animation.

4. **Multi-Faceted Filtering**:
   * **Keyword Search**: Instant multi-token search across post text, district, street, author, or listing ID.
   * **Source Selection**: Filter between `All Sources`, `Facebook`, and `List.am`.
   * **Listing & Property Types**: Multi-select filters for *For Sale*, *For Rent*, *Apartment*, *House*, and *Land*, with independent **Include** or **Exclude** logic.
   * **Purpose / Zoning**: Dedicated filter to distinguish between **Housing / Residential** (apartments, residential houses, homestead building plots) and **Agricultural / Farming** (agricultural plots, orchards, greenhouses, arable land), with **Include/Exclude** mode and visual badges (`🌱 Agricultural`, `🏡 Residential`).
   * **Location Search & Multi-Select**: Real-time filterable location list with search input.
   * **Price Range**: Min and Max price thresholds synchronized with selected currency.
   * **Rooms**: Filter by minimum room count (`1+`, `2+`, `3+`, `4+`, `5+`).
   * **Active Filter Chips**: Removable badge chips showing active filter parameters with one-click clear buttons.

5. **Fluid Responsive Sizing & Above-the-Fold Priority**:
   * Modern typography and layout using CSS `clamp()` for fluid font sizes, container widths, and touch targets across mobile, tablet, and widescreen displays.
   * Compact sticky header maximizing vertical viewport space and displaying content immediately above the fold.
   * Collapsible filter sidebar that converts into an accordion drawer on mobile screens (`< 900px`).

6. **Bilingual Localization (i18n)**:
   * Instant toggle between **English** and **Հայերեն** (Armenian), synchronizing all labels, placeholders, badges, relative timestamps, and location district names. Preference is persisted in `localStorage`.

---

## Local Development & Serving

To view and test the web application locally:

```bash
# From the project root, start Python's built-in HTTP server:
python -m http.server 8000

# Open your browser and navigate to:
# http://localhost:8000/index.html
```

To run a syntax and lint validation on the frontend:
```bash
# Validate JavaScript syntax across modules
node -c translations.js script.js
```