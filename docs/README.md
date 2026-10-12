# 📚 Armenia Real Estate Hub — Documentation & Wiki

Welcome to the comprehensive technical documentation and wiki for the **Armenia Real Estate Hub**. This repository contains a production-ready real estate aggregation and discovery platform for Armenia, including automated scrapers, data normalization pipelines, a responsive client-side web application, and a visual regression screenshot testing suite.

---

## 🧭 Documentation Map

| Guide | Description | Key Topics |
| :--- | :--- | :--- |
| **[System Architecture](file:///d:/Projects/kittyalshimeowik.github.io/docs/ARCHITECTURE.md)** | End-to-end system design & data flow | Pipeline diagram, data lifecycle, JSON schemas, component roles |
| **[Scrapers & Data Pipeline](file:///d:/Projects/kittyalshimeowik.github.io/docs/SCRAPERS_AND_PIPELINE.md)** | Data collection and ingestion engine | Facebook & List.am scrapers, deduplication, housing parser, normalization |
| **[Frontend & Web Application](file:///d:/Projects/kittyalshimeowik.github.io/docs/FRONTEND_AND_UI.md)** | Interactive web portal architecture | DOM structure, CSS design tokens, filtering engine, i18n, smooth scrolling |
| **[Testing & Visual Regression](file:///d:/Projects/kittyalshimeowik.github.io/docs/TESTING_AND_VISUAL_REGRESSION.md)** | Automated testing and screenshot suite | Playwright headless runner, pixel diff comparator, HTML reports, unit tests |

---

## ⚡ Quick Reference

### Running the Web Application
```bash
# Serve locally via Python
python -m http.server 8000
# Then open http://localhost:8000 in your browser
```

### Running the Data Aggregation Pipeline
```bash
# Execute end-to-end scraping and normalization pipeline
python run_pipeline.py
```

### Running the Test Suites
```bash
# Run all unit and interactive UI tests (159+ tests)
python run_tests.py

# Run visual regression screenshot testing suite (11 viewports/scenarios)
python run_screenshot_tests.py

# Update golden screenshot baselines
python run_screenshot_tests.py --update-baselines
```

---

## 📂 Repository Directory Layout

```text
d:/Projects/kittyalshimeowik.github.io/
├── index.html                   # Main single-page application entry point
├── style.css                    # Modern design tokens, glassmorphism, responsive grid
├── script.js                    # Client-side filtering, sorting, infinite scroll, DOM engine
├── translations.js              # Localization dictionary (English & Armenian)
├── run_pipeline.py              # Master data ingestion pipeline orchestrator
├── run_tests.py                 # Master test runner discovering all __tests__
├── run_screenshot_tests.py      # CLI for automated visual regression screenshot testing
├── docs/                        # Complete technical documentation and wiki
│   ├── README.md                # Wiki table of contents & index
│   ├── ARCHITECTURE.md          # System architecture and data flow diagrams
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
