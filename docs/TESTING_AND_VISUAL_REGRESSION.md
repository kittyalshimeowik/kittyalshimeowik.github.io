# 📸 Testing & Visual Regression Architecture

This document describes the quality assurance framework for the **Armenia Real Estate Hub**, covering unit testing, interactive Playwright browser tests, and the pixel-diff visual screenshot regression testing suite.

---

## 🎯 Testing Overview

The repository features a multi-layer testing strategy:

1. **Unit Test Suite (153 tests)**: Tests regex extraction, price parsing, Armenian location matching, time parsing, image comparator math, and ephemeral test server lifecycle.
2. **Interactive UI E2E Tests (6 tests)**: Automated Playwright tests verifying scrolling functionality, Back-to-Top button lifecycle, filter collapse, language switching, reset filters, and share link toast notifications.
3. **Visual Screenshot Regression Suite (11 scenarios)**: Captures pixel-accurate screenshots across desktop, tablet, and mobile viewports, comparing them against golden baselines with pixel mismatch reporting.

---

## 🔬 Visual Screenshot Regression Suite (`screenshot_tests/`)

### Architecture & Components

```text
screenshot_tests/
├── server.py        # Ephemeral Local HTTP Server on dynamic port
├── scenarios.py     # Master registry of test scenarios and user interactions
├── runner.py        # Playwright headless browser execution engine
├── comparator.py    # Per-pixel color-tolerance comparison using PIL
├── reporter.py      # Standalone interactive HTML report generator
├── baselines/       # Golden reference images (PNG)
└── __tests__/       # Automated unit & interactive UI test suites
```

### 1. Ephemeral Server (`server.py`)
Spawns a clean `http.server.SimpleHTTPRequestHandler` in a background daemon thread on port `0` (OS-assigned ephemeral port). Eliminates port collisions and allows testing without external web servers or CORS restrictions.

### 2. Test Scenarios Registry (`scenarios.py`)
Defines viewports and setup interactions across 14 critical user journeys:

| Scenario ID | Title | Viewport | Type / Interaction |
| :--- | :--- | :--- | :--- |
| `desktop_home` | Desktop Home & Catalogs | 1440x900 | Default desktop catalog view |
| `desktop_full_page` | Desktop Full Page Layout | 1440x900 | Full-page vertical layout |
| `desktop_armenian_lang` | Desktop Armenian Localization | 1440x900 | Switch to Armenian language & AMD |
| `desktop_filters_collapsed` | Desktop Filters Collapsed | 1440x900 | Collapse sidebar to 56px |
| `desktop_keyword_search` | Desktop Keyword Search Filter | 1440x900 | Search for *"Kentron"* |
| `desktop_filters_applied` | Desktop Multi-Facet Filter | 1440x900 | Select *Rent* and *Apartment* |
| `desktop_currency_amd` | Desktop AMD Currency View | 1440x900 | Convert currency to AMD (֏) |
| `tablet_view` | Tablet Responsive Layout | 768x1024 | iPad tablet viewport |
| `mobile_view` | Mobile Portrait View | 375x812 | iPhone mobile viewport |
| `mobile_filters_collapsed` | Mobile Filters Collapsed | 375x812 | Mobile view with filter drawer closed |
| `component_card_detail` | Single Property Card Component | 1440x900 | High-res element capture (`.property-card`) |
| `component_card_photo` | Single Property Card with Photography | 1440x900 | High-res element capture with real photos & badge |
| `header_branding_logo` | Header Branding & Logo Component | 1440x900 | High-res element capture (`header`) |
| `mobile_compact_360` | Compact Mobile Screen (360x640) | 360x640 | Android compact viewport verification |

### 3. Image Comparator & Diff Math (`comparator.py`)
Computes pixel differences between current screenshots and golden baselines:
- **Per-Channel Tolerance (`tolerance=10`)**: Tolerates subpixel font rendering anti-aliasing noise across different OS graphics drivers.
- **Mismatch Threshold (`threshold=0.1%`)**: Fails test only if noticeable visual regressions exceed the threshold.
- **Diff Image Generation**: Creates visual diff images highlighting altered pixels in magenta (`#ff00ff`) for fast diagnostic triage.

### 4. Interactive HTML Reporter (`reporter.py`)
Outputs an interactive report to `test_output/screenshots/report.html`:
- Visual pass/fail summary and execution timings.
- Side-by-side baseline, current, and diff image comparisons.
- Interactive opacity/split slider for visual inspection.

---

## 🏃 Running the Tests

### 1. Run All Unit & Interactive Tests
```bash
python run_tests.py
```
Discovers and runs all 159 tests across all `__tests__` directories in under 10 seconds.

### 2. Run Visual Screenshot Testing Suite
```bash
python run_screenshot_tests.py
```

### 3. Update Golden Baselines
When you intentionally modify the visual design or layouts:
```bash
python run_screenshot_tests.py --update-baselines
```

### 4. Run Specific Scenarios
```bash
python run_screenshot_tests.py --scenarios desktop_home,mobile_view
```
