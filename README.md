# Real Estate Listing Website in Armenia

Welcome to the **Real Estate Listing Website in Armenia** platform documentation. This repository contains the source code, data pipelines, web interface components, and automated testing suite for managing and visualizing real estate listings across Armenia (e.g., Yerevan, Gyumri, Vanadzor, Dilijan).

---

## Table of Contents
- [Overview](#overview)
- [File Structure](#file-structure)
- [How Data is Generated](#how-data-is-generated)
- [Execution & Command Line Usage](#execution--command-line-usage)
- [Running the Test Suite](#running-the-test-suite)
- [Web Interface Details](#web-interface-details)

---

## Overview

This project provides an end-to-end solution for collecting, processing, serving, and viewing Armenian real estate market data. It includes data generation/ingestion tools, CLI utilities for maintenance and bulk operations, an interactive web interface for end-users and agents, and a comprehensive test suite to ensure system reliability.

---

## File Structure
armenia-real-estate-website/
├── .gitignore
├── groups_config.json            # Configuration for Facebook Group IDs
├── index.html                    # Web UI layout and filter system
├── README.md                     # Project documentation
├── run_pipeline.py               # Main orchestration script running scraper & processor
├── run_tests.py                  # Test runner executing test suites across modules
├── script.js                     # Dynamic data fetching, multi-language & filter logic
├── style.css                     # Responsive dashboard styling
│
└── scrapers/                     # Modular scraping and data pipeline engine
    ├── base_scraper.py           # Abstract Base Class defining scraper interfaces
    │
    ├── facebook/                 # Facebook Group Playwright scraper module
    │   ├── fb_scraper.py         # Playwright-based scraper entry point
    │   ├── fb_session/           # Persistent browser user-data & session profile storage
    │   ├── groups_metadata/     # Per-group analytical metrics & run dynamic benchmarks
    │   ├── housing_posts_data/   # Target folder for extracted post JSON files
    │   ├── utilities/            # Facebook-specific storage & ID decoding tools
    │   │   ├── fb_metadata_storage.py
    │   │   └── fb_utils.py
    │   └── __tests__/            # Unit test suite for Facebook scraping logic
    │
    ├── processors/               # Master data consolidation engine
    │   ├── cleanup_master_listings.py # Post-processing cleanup and validation
    │   ├── generate_site_data.py # Merges, deduplicates, and converts price currencies
    │   ├── master_listings_json/ # Consolidated JSON files consumed by the Web UI
    │   └── __tests__/            # Unit test suite for post-processors & normalizers
    │
    └── utilities/                # Shared scraping utilities
        ├── browser_humanizer.py  # Human-like interaction behavior (scrolling, clicking)
        ├── housing_parser.py     # Regex & NLP parser for real estate text features
        ├── location_data.py      # Location dictionary & regex mapping engine
        └── time_utils.py         # Relative time parsing & timestamp tools

---

## How Data is Generated

The property data powering the application originates from two primary channels: automated scrapers/ingestion tools and synthetic seed generators for development.

### 1. Ingestion & Data Pipeline
* **Web Scraping & Aggregation**: The pipeline collects property listings from public regional sources (e.g., public listings across Yerevan districts like Kentron, Arabkir, and Ajapnyak).
* **Data Cleansing & Normalization**:
  * **Currency Standardization**: Values listed in USD ($) or EUR (€) are normalized into Armenian Dram (AMD / ֏) using daily central bank exchange rates.
  * **Geocoding & Location Normalization**: Address strings are standardized into administrative regions (Marzes), cities, and administrative districts, alongside latitude/longitude coordinates.
  * **Feature Extraction**: Unstructured text descriptions are parsed to extract structured fields (e.g., square meters, floor number, total building floors, renovation status, building type like *Stone* or *Monolith*, open/closed balconies).

---

## Execution & Command Line Usage

Commands to run the data generation pipeline for web scrapers

### CLI Commands

#### 1. Executing the pipeline
```bash
python run_pipeline.py -t 1

python run_pipeline.py -ns
```

---

## Running the Test Suite
The backend test suite covers API endpoints, data validation schemas, currency conversion logic, and database operations.

```bash
# Run all backend tests
python run_tests.py
```

---

## Web Interface Details

The front-end web application is designed to be fast, responsive, and tailored specifically to the Armenian real estate market context.

### Key Features
1. **Interactive Search & Filtering**:
   * **Location Filters**: Filter by Region (*Marz*), City, or Yerevan District (*Kentron, Arabkir, Shengavit, etc.*).
   * **Property Attributes**: Filter by price range (AMD / USD), area ($m^2$), number of bedrooms, building material (*Stone*, *Monolith*, *Panel*), and ceiling height.
   * **Transaction Types**: Switch seamlessly between *For Sale*, *Long-term Rent*, and *Daily Rent*.

2. **Multilingual Support**:
   * Native localization support for **Armenian** (hy), and **English** (en)