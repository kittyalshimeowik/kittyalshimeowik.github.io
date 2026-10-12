# Agent Operational Guidelines & Repository Rules

Welcome to the **Armenia Real Estate Hub** repository. When working on this codebase, all AI agents and automated tools must strictly follow the standards below:

---

## 🛡️ External Website Testing & Anti-Bot Protection (CRITICAL)

When testing scrapers, visiting links, or verifying listings from **List.am** or **Facebook**:
1. **Act Like a Real Human User**: External platforms enforce aggressive anti-bot protections (Cloudflare Turnstile, browser fingerprinting, rate limiting, and account checkpoints).
2. **Never Use Raw HTTP Clients**: Do not use `curl`, `requests`, `urllib`, or raw `fetch` against List.am or Facebook. These result in immediate HTTP 403 blocks and IP flagging.
3. **Use Codebase Reference Humanizers**:
   - [`scrapers/utilities/browser_humanizer.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/utilities/browser_humanizer.py): Bézier curve mouse movements (`move_mouse_bezier`), smooth incremental scrolling with jitter (`smooth_scroll`), randomized action chains, and periodic human rest breaks (`check_global_break`).
   - [`scrapers/listam/utilities/listam_utils.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/listam/utilities/listam_utils.py): Human scrolling (`human_scroll`), tab multitasking simulation (`simulate_random_tab_activity`), and Cloudflare challenge waiting (`handle_cloudflare_loop`).
   - [`scrapers/facebook/utilities/fb_utils.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/facebook/utilities/fb_utils.py): Session detection (`is_facebook_logged_in`), manual login waiting (`wait_for_facebook_login`), and persistent user profiles.
4. **Prioritize Local Offline Data**: Whenever testing classifications or reviewing listing attributes, inspect the local SQLite database ([`scrapers/data/listings.db`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/data/listings.db)) and raw JSON dumps first, rather than triggering unnecessary live requests.

See the complete specification in: [`.agents/rules/safe_scraping_and_browser_guidelines.md`](file:///d:/Projects/kittyalshimeowik.github.io/.agents/rules/safe_scraping_and_browser_guidelines.md).

---

## 🧪 Testing & Verification Protocols

1. **Unit Testing**:
   - Run: `.venv\Scripts\python.exe run_tests.py`
   - Must maintain 100% pass rate across all 191+ unit tests.
2. **Visual Regression & Screenshot Testing**:
   - Run: `.venv\Scripts\python.exe run_screenshot_tests.py`
   - Tests 14 desktop, tablet, and mobile scenarios against baseline images.
   - Only update baselines via `--update-baselines` when intentional layout or dataset changes occur.
3. **Data Classification Integrity**:
   - Pricing must never capture per-m² rates ($55–$170) as total sale prices.
   - Locations must resolve Armenian inflected forms (`-ում`, `-ի`) and match bilingual translations in [`translations.js`](file:///d:/Projects/kittyalshimeowik.github.io/translations.js).
   - Re-running classification must sync both SQLite ([`scrapers/data/listings.db`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/data/listings.db)) and public feeds ([`scrapers/processors/master_listings_json/`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/processors/master_listings_json/)).
