# 🇦🇲 Armenia Real Estate Hub

An end-to-end real estate aggregation platform, data pipeline, and interactive dashboard for the Armenian housing market. Aggregates live property listings from **Facebook Real Estate Groups** and **List.am**, normalizing prices, specifications, and regional Armenian geographic entities into a fast, client-side web portal with visual regression and automated testing suites.

---

## 🧭 Documentation & Wiki

Detailed technical documentation and component guides are organized in the [`docs/`](file:///d:/Projects/kittyalshimeowik.github.io/docs/README.md) directory:

- 🏛️ **[System Architecture](file:///d:/Projects/kittyalshimeowik.github.io/docs/ARCHITECTURE.md)**: End-to-end architecture, data pipeline lifecycle, Mermaid flowcharts, and master data schema.
- 🤖 **[Scrapers & Pipeline Guide](file:///d:/Projects/kittyalshimeowik.github.io/docs/SCRAPERS_AND_PIPELINE.md)**: Facebook GraphQL and List.am scraping engines, Armenian regex housing parser, deduplication, and cron orchestration.
- 🎨 **[Frontend & Web Architecture](file:///d:/Projects/kittyalshimeowik.github.io/docs/FRONTEND_AND_UI.md)**: Zero-dependency web app, glassmorphism design system, multi-criteria filtering, smooth scrolling, Back-to-Top affordance, and bilingual localization (EN/HY).
- 📸 **[Testing & Visual Regression](file:///d:/Projects/kittyalshimeowik.github.io/docs/TESTING_AND_VISUAL_REGRESSION.md)**: Playwright headless runner, pixel-difference comparator, golden baselines, interactive HTML reporting, and E2E browser tests.

---

## ✨ Key Features

- **Live Aggregation**: Ingests real estate listings across Facebook public groups and List.am categories.
- **Multilingual Domain Parser**: Identifies prices (USD / AMD), sizes (m²), room counts, contact numbers, and zoning (Residential / Agricultural) across Armenian, Russian, and English listing bodies.
- **Modern Web Interface**:
  - **Visual Property Media**: Scraped listing photography with lazy loading, photo count badges, and graceful category-themed SVG vector fallbacks for 100% visual presentation.
  - **Interactive Google Maps**: Modal map viewer with zero-key embedded Google Maps iframe resolving recognized Yerevan streets, landmarks, and districts, plus direct 1-click external navigation.
  - Live feed header with pulse indicator and quick source stats.
  - Collapsible filter sidebar with smooth SVG rotation.
  - Instantaneous in-memory filtering (price, source, property type, zoning, multi-select locations, keywords).
  - Floating **Back to Top** button with scroll position tracking.
  - One-click **Share / Copy Link** button with floating toast notification.
  - Direct call button with clean international number formatting.
  - Infinite scroll pagination and skeleton loading placeholders.
  - Full bilingual localization (English / Հայերեն) with automatic currency alignment.
- **Automated Testing & Anti-Bot QA**:
  - 172+ automated unit and interactive browser test cases.
  - Visual regression testing across desktop, tablet, and mobile breakpoints with interactive HTML reports.
  - Strict human emulation & anti-detection safeguards (Bézier mouse curves, smooth jitter scrolling, Cloudflare challenge loops, and persistent session profiles) documented in [`.agents/rules/safe_scraping_and_browser_guidelines.md`](file:///d:/Projects/kittyalshimeowik.github.io/.agents/rules/safe_scraping_and_browser_guidelines.md).

---

## ⚡ Quickstart & Usage

### 1. Serve Web Portal Locally
```bash
# Start local HTTP server
python -m http.server 8000
# Open http://localhost:8000 in your browser
```

### 2. Run Data Collection Pipeline
```bash
# Execute end-to-end scraper, normalizer, and deduplication pipeline
python run_pipeline.py
```

### 3. Run Automated Tests
```bash
# Run all unit tests and interactive UI browser tests (159 tests)
python run_tests.py
```

### 4. Run Visual Screenshot Testing Suite
```bash
# Run screenshot tests comparing against golden baselines (11 scenarios)
python run_screenshot_tests.py

# Update golden baselines after intentional layout/design modifications
python run_screenshot_tests.py --update-baselines

# View HTML visual diff report
# Open test_output/screenshots/report.html
```

---

## 📂 Repository File Layout

```text
kittyalshimeowik.github.io/
├── index.html                   # Single-page web application entry point
├── style.css                    # Design system, glassmorphism, responsive grid
├── script.js                    # In-memory filter engine, scroll observers, UI controller
├── translations.js              # Bilingual dictionary (English & Armenian)
├── run_pipeline.py              # Master data ingestion pipeline orchestrator
├── run_tests.py                 # Master test runner discovering all __tests__
├── run_screenshot_tests.py      # Automated visual regression testing CLI
├── docs/                        # Complete technical documentation and wiki
│   ├── README.md                # Wiki table of contents & index
│   ├── ARCHITECTURE.md          # Architecture & data flow diagrams
│   ├── SCRAPERS_AND_PIPELINE.md # In-depth scraper and normalization guide
│   ├── FRONTEND_AND_UI.md       # Frontend UI, CSS design system, and state engine
│   └── TESTING_AND_VISUAL_REGRESSION.md # Screenshot testing and QA verification
├── scrapers/                    # Scraping engine and data processors
│   ├── base_scraper.py          # Abstract base scraper interface
│   ├── facebook/                # Facebook Group real estate scrapers
│   ├── listam/                  # List.am classifieds scrapers
│   ├── processors/              # Normalizers, deduplicators, master JSON generators
│   └── utilities/               # Phone, price, time, and Armenian text parsers
└── screenshot_tests/            # Playwright visual regression suite
    ├── server.py                # Ephemeral local HTTP server for testing
    ├── scenarios.py             # Viewports, responsive scenarios, and user flows
    ├── runner.py                # Playwright execution engine
    ├── comparator.py            # Per-pixel diff math and PIL image highlighting
    ├── reporter.py              # Self-contained interactive HTML reporting
    ├── baselines/               # Golden baseline reference screenshots
    └── __tests__/               # Unit tests for test infrastructure & interactive UI
```

---

## 📜 License & Acknowledgments

Built for transparent and accessible real estate discovery in Armenia. Powered by open-source tooling, Playwright, Python, and modern web standards.