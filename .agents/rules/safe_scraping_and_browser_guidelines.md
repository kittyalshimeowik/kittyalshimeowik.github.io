# Safe Web Scraping, Testing, and Anti-Bot Guidelines

When interacting with external platforms (especially **List.am** and **Facebook**), all testing, scraping, link verification, and browser automation MUST emulate real human behavior to prevent IP bans, Cloudflare blocks, and account checkpoints.

Reference implementations in this codebase:
- [`scrapers/utilities/browser_humanizer.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/utilities/browser_humanizer.py)
- [`scrapers/facebook/utilities/fb_utils.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/facebook/utilities/fb_utils.py) & [`scrapers/facebook/fb_scraper.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/facebook/fb_scraper.py)
- [`scrapers/listam/utilities/listam_utils.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/listam/utilities/listam_utils.py) & [`scrapers/listam/list_am_scraper.py`](file:///d:/Projects/kittyalshimeowik.github.io/scrapers/listam/list_am_scraper.py)

---

## 1. Browser Stealth & Anti-Detection Architecture

1. **Undetected ChromeDriver / Stealth Options**:
   - For List.am, always utilize `undetected_chromedriver` matching the installed Chrome major version (`get_installed_chrome_major_version()`).
   - Run in subprocess mode (`use_subprocess=True`).
   - Strip automated flags:
     - Remove `--enable-automation`
     - Add `--disable-blink-features=AutomationControlled`
     - Use realistic desktop window size (`1366x768`)
     - Disable GPU acceleration (`--disable-gpu`), use `--no-sandbox`
   - For Playwright sessions, run with persistent contexts and standard desktop user agents (`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36`).

2. **Persistent User Data Profiles**:
   - Store sessions in persistent profile directories (`USER_DATA_DIR` in `~/Desktop/fb-scraper-project/...`).
   - Avoid ephemeral/incognito fresh sessions for logged-in services; persistent profiles retain verified cookies (`c_user`, Cloudflare `cf_clearance`).

3. **No Raw HTTP Fetching Against Protected Endpoints**:
   - **Never** query List.am or Facebook using raw, non-browser HTTP clients (`curl`, `urllib`, `requests`, `fetch`) — Cloudflare and Facebook bot-shields will flag the IP and respond with HTTP 403 or captcha challenges.
   - When verifying listing data, prioritize existing rich raw text already preserved in `scrapers/data/listings.db` before navigating out to live sites.

---

## 2. Human Behavior Emulation

1. **Bézier Curve Mouse Movements**:
   - Use non-linear polynomial/Bézier curves with randomized control points and ease-in/ease-out acceleration (`move_mouse_bezier()`).
   - Divide movement into 20–30 incremental steps with 10–25ms micro-delays.
   - Avoid instantaneous `mouse.click(x, y)` from (0, 0). Click with randomized coordinate offsets inside element bounding boxes (20% to 80% width/height).

2. **Natural Smooth Scrolling**:
   - Do NOT jump directly to page bottoms using `window.scrollTo(0, document.body.scrollHeight)`.
   - Scroll incrementally in chunks of 350–700 px (`human_scroll()`, `smooth_scroll()`) with 12–20ms step delays.
   - Inject natural backward scroll-backs (5%–15% probability of scrolling up 100–200 px) to simulate reader pause.

3. **Pacing and Jitter Delays**:
   - Always apply randomized pauses between navigations:
     - Category pages: `random.uniform(1.5, 3.0)` seconds
     - Item detail pages: `random.uniform(1.5, 3.5)` seconds
     - Interaction actions (e.g. clicking "See more"): `random.uniform(0.2, 0.5)` seconds

4. **Multitasking & Tab Switching**:
   - Occasionally simulate multitasking (`simulate_random_tab_activity()`): 20% chance to open an empty tab, dwell for 1.0–2.5 seconds, and switch back.

5. **Natural Global Breaks**:
   - For long-running scraping sessions, enforce natural breaks (`check_global_break()`): 30–180 second pauses every 8–12 minutes.

---

## 3. Challenge & Login Safeguards

1. **Cloudflare Challenges**:
   - When "Just a moment..." or "Verify you are human" appears, NEVER attempt automated rapid clicks.
   - Use `handle_cloudflare_loop()` to detect the challenge and wait patiently for manual clearance or resolution.

2. **Facebook Authentication**:
   - Verify `c_user` cookie via `is_facebook_logged_in()`.
   - If unauthenticated, notify the user to log in manually via `wait_for_facebook_login()`. Never automate password entry or attempt to bypass 2FA checkpoints.
