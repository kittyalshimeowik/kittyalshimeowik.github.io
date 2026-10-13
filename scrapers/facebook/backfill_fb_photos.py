# scrapers/facebook/backfill_fb_photos.py

import os
import sys
import json
import time
import random
import platform
import argparse
from datetime import datetime

# Resolve Project Root so 'scrapers' imports work cleanly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output
ensure_utf8_output()

from scrapers.utilities.storage import ListingsStorage
from scrapers.utilities.browser_humanizer import smooth_scroll, check_global_break
from scrapers.facebook.utilities.fb_utils import (
    extract_canonical_post_id,
    is_facebook_logged_in,
    wait_for_facebook_login
)

CURRENT_OS = platform.system().lower()
BASE_SESSION_DIR = os.path.expanduser("~/Desktop/fb-scraper-project")

if CURRENT_OS == "windows":
    USER_DATA_DIR = os.path.join(BASE_SESSION_DIR, "fb_session_windows")
else:
    MACHINE_HOSTNAME = platform.node() or "unknown_machine"
    USER_DATA_DIR = os.path.join(BASE_SESSION_DIR, f"fb_session_{MACHINE_HOSTNAME}")


def find_chrome_executable():
    """Detects standard Chrome installation path on host."""
    chrome_appdata = os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    chrome_progfiles = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    chrome_progfiles86 = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    if os.path.exists(chrome_appdata):
        return chrome_appdata
    elif os.path.exists(chrome_progfiles):
        return chrome_progfiles
    elif os.path.exists(chrome_progfiles86):
        return chrome_progfiles86
    return None


def extract_post_photos_from_page(page, canonical_id, max_photos=5):
    """
    Extracts high-resolution post photos from Facebook post page DOM.
    Strictly isolated to the specific post container. Filters out avatars,
    external link previews (OpenGraph thumbnails), comments, video reels, and unrelated feed posts.
    """
    try:
        photos = page.evaluate("""({postId, maxCount}) => {
            const results = [];
            const seen = new Set();

            function isValidPhotoUrl(url) {
                if (!url || typeof url !== 'string') return false;
                if (!url.includes('scontent') && !url.includes('fbcdn.net')) return false;
                // Exclude static assets, emojis, scripts
                if (url.includes('emoji.php') || url.includes('static.xx.fbcdn.net') || url.includes('rsrc.php')) return false;
                // Exclude external OpenGraph link previews (news article scrape cache)
                if (url.includes('/t39.99422-') || url.includes('safe_image.php') || url.includes('external.xx')) return false;
                // Exclude avatars (-1/) and reels/video thumbnails (-10/, t39.25447)
                if (url.includes('/t39.30808-1/') || url.includes('/t1.30497-1/') || url.includes('/t15.5256-10/') || url.includes('/t39.25447-')) return false;
                return true;
            }

            function addPhoto(src, priority) {
                if (!isValidPhotoUrl(src)) return;
                const baseKey = src.split('?')[0];
                if (seen.has(baseKey)) return;
                seen.add(baseKey);
                results.push({ src, priority });
            }

            // --- STEP 1: Strict Post Container Isolation ---
            // Only search within the container of THIS specific post. Never search outside it.
            let postContainer = null;

            // Strategy A: Find permalink/timestamp anchor matching this exact postId
            const permalinkLinks = Array.from(document.querySelectorAll(`a[href*="/posts/${postId}"], a[href*="story_fbid=${postId}"]`));
            for (const a of permalinkLinks) {
                const article = a.closest('div[role="article"]') 
                    || a.closest('div[data-pagelet^="FeedUnit"]')
                    || a.closest('div[data-pagelet*="GroupFeed"]')
                    || a.closest('div[class*="x1yztbdb"]');
                if (article) {
                    postContainer = article;
                    break;
                }
            }

            // Strategy B: On a dedicated post URL, target the primary article inside main feed
            if (!postContainer) {
                const mainArea = document.querySelector('div[role="main"]');
                if (mainArea) {
                    const articles = Array.from(mainArea.querySelectorAll('div[role="article"]'));
                    if (articles.length > 0) {
                        postContainer = articles[0];
                    }
                }
            }

            // If we cannot uniquely locate the target post container, ABORT to avoid scraping unrelated content
            if (!postContainer) {
                return [];
            }

            // --- STEP 2: Filter out comment sections and external link cards ---
            const commentContainers = Array.from(postContainer.querySelectorAll('div[aria-label*="Comment" i], div[role="complementary"], form, ul'));
            const isInsideComments = (el) => commentContainers.some(c => c.contains(el));

            const isInsideExternalLinkCard = (el) => {
                const link = el.closest('a');
                if (!link) return false;
                const href = link.getAttribute('href') || '';
                return href.includes('l.facebook.com/l.php') || (href.startsWith('http') && !href.includes('facebook.com'));
            };

            // --- STEP 3: Targeted Photo Extraction strictly within postContainer ---
            // 3a. Direct Photo Viewer Links
            const postPhotoLinks = Array.from(postContainer.querySelectorAll('a[href*="/photo"]'));
            postPhotoLinks.forEach(a => {
                if (isInsideComments(a) || isInsideExternalLinkCard(a)) return;

                const href = a.getAttribute('href') || '';
                const img = a.querySelector('img');
                if (!img || !img.src) return;
                const w = img.naturalWidth || img.width || 0;
                const h = img.naturalHeight || img.height || 0;

                if (href.includes(postId)) {
                    if (w >= 100 && h >= 100) {
                        addPhoto(img.src, 1);
                    }
                } else if (w >= 200 && h >= 200) {
                    addPhoto(img.src, 2);
                }
            });

            // 3b. Dedicated media viewer/grid within postContainer
            if (results.length === 0) {
                const mediaImages = Array.from(postContainer.querySelectorAll('div[data-pagelet*="MediaViewer"] img, div[data-visualcompletion="media-vc-image"] img, img[data-visualcompletion="media-vc-image"]'));
                mediaImages.forEach(img => {
                    if (isInsideComments(img) || isInsideExternalLinkCard(img)) return;
                    const w = img.naturalWidth || img.width || 0;
                    const h = img.naturalHeight || img.height || 0;
                    if (w >= 200 && h >= 200) {
                        addPhoto(img.src, 3);
                    }
                });
            }

            // Never fall back to page body or unrelated posts.
            results.sort((a, b) => a.priority - b.priority);
            return results.slice(0, maxCount).map(r => r.src);
        }""", {"postId": str(canonical_id), "maxCount": max_photos})

        return photos or []
    except Exception as e:
        print(f"    [WARN] DOM extraction error for {canonical_id}: {e}")
        return []


def get_fb_posts_to_backfill(storage, active_only=True, limit=None):
    """Retrieves Facebook listings that have no images and have not been checked before."""
    cur = storage.conn.cursor()
    query = """
        SELECT canonical_id, url, property_category, listing_type, created_at, is_active
        FROM listings
        WHERE source = 'Facebook'
          AND (images_json IS NULL OR images_json = '[]' OR length(images_json) <= 2)
          AND photos_checked_at IS NULL
    """
    if active_only:
        query += " AND is_active = 1"

    query += " ORDER BY is_active DESC, creation_timestamp DESC"

    if limit is not None and limit > 0:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    rows = cur.fetchall()
    return [
        {
            "canonical_id": r["canonical_id"],
            "url": r["url"],
            "property_category": r["property_category"],
            "listing_type": r["listing_type"],
            "created_at": r["created_at"],
            "is_active": r["is_active"]
        }
        for r in rows
    ]


def check_facebook_rate_limit_or_block(page):
    """Detects Facebook action blocks, rate limit throttles, or security checkpoints."""
    try:
        url = (page.url or "").lower()
        if "checkpoint" in url or "login_challenge" in url:
            return {"blocked": True, "reason": "checkpoint", "message": "Facebook security checkpoint / verification"}
        content = page.evaluate("() => (document.body ? document.body.innerText.slice(0, 3000) : '')")
        low = content.lower()
        if "temporarily blocked" in low or "you’re temporarily blocked" in low or "you're temporarily blocked" in low:
            return {"blocked": True, "reason": "action_blocked", "message": "Facebook temporary action block"}
        if "we limit how often" in low or ("try again later" in low and "block" in low):
            return {"blocked": True, "reason": "rate_limited", "message": "Facebook rate limit cooldown"}
    except Exception:
        pass
    return {"blocked": False, "reason": None, "message": ""}


def run_fb_photos_backfill(
    limit=None,
    headless=True,
    active_only=True,
    delay_min=2.5,
    delay_max=4.0,
    regenerate_site_data=True
):
    print("=" * 65)
    print("Facebook Listings Photo Backfill Utility")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    run_start = datetime.now()

    with ListingsStorage() as storage:
        posts_to_process = get_fb_posts_to_backfill(storage, active_only=active_only, limit=limit)
        total_targets = len(posts_to_process)

        if total_targets == 0:
            print("✅ All Facebook listings already have photos backfilled!")
            return {"processed": 0, "photos_found": 0, "updated": 0, "remaining_in_db": 0}

        print(f"📋 Found {total_targets} Facebook listings requiring photo backfill.")

        from playwright.sync_api import sync_playwright

        chrome_exec = find_chrome_executable()
        context_args = {
            "user_data_dir": USER_DATA_DIR,
            "headless": headless,
            "viewport": {"width": 1366, "height": 768},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }

        if CURRENT_OS == "windows":
            context_args["ignore_default_args"] = ["--enable-automation"]
            context_args["args"] = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
            if chrome_exec:
                context_args["executable_path"] = chrome_exec
        else:
            context_args["args"] = ["--disable-blink-features=AutomationControlled"]

        processed_count = 0
        photos_found_count = 0
        posts_with_photos = 0
        blocked_count = 0

        with sync_playwright() as p:
            browser_context = p.chromium.launch_persistent_context(**context_args)
            pages = browser_context.pages
            page = pages[0] if pages else browser_context.new_page()

            # Ensure authenticated session
            wait_for_facebook_login(browser_context, page)

            print(f"🚀 Commencing photo backfill for {total_targets} listings...\n")

            for idx, post in enumerate(posts_to_process):
                cid = post["canonical_id"]
                url = post["url"]
                cat = post["property_category"]
                p_type = post["listing_type"]

                remaining_in_run = total_targets - (idx + 1)
                pct = ((idx + 1) / total_targets) * 100.0
                elapsed_sec = (datetime.now() - run_start).total_seconds()
                rate = (idx + 1) / elapsed_sec if elapsed_sec > 0 else 0
                eta_sec = remaining_in_run / rate if rate > 0 else 0

                print(f"[{idx + 1}/{total_targets}] ({pct:5.1f}%) Processing {cid} ({cat} - {p_type}):")
                print(f"  URL: {url}")

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    time.sleep(random.uniform(delay_min, delay_max))

                    # Check for rate limiting / checkpoints before extracting
                    block_info = check_facebook_rate_limit_or_block(page)
                    if block_info["blocked"]:
                        blocked_count += 1
                        print(f"  ⚠️ Facebook rate limit / action block: {block_info['message']}")
                        print("  ⏳ Skipping post WITHOUT marking as checked, cooling down for 45s...")
                        time.sleep(45.0)
                        continue

                    try:
                        page.mouse.wheel(0, random.randint(120, 280))
                        time.sleep(0.4)
                    except Exception:
                        pass

                    photos = extract_post_photos_from_page(page, cid)

                    if photos:
                        storage.update_listing_images(cid, photos)
                        photos_found_count += len(photos)
                        posts_with_photos += 1
                        print(f"  📸 Found {len(photos)} photos -> Stored in database.")
                    else:
                        storage.update_listing_images(cid, [])
                        print("  ℹ️ No post photos found (text-only or media unavailable).")

                    processed_count += 1
                    print(f"  📊 Run stats: Photos found: {photos_found_count} | Posts with photos: {posts_with_photos} | Remaining: {remaining_in_run} | Elapsed: {elapsed_sec:.1f}s (ETA: {eta_sec:.0f}s)")

                except Exception as ex:
                    print(f"  ❌ Error fetching {url}: {ex}")

                # Human rest pause every 25 posts
                if (idx + 1) % 25 == 0 and (idx + 1) < total_targets:
                    rest_sec = random.uniform(15.0, 25.0)
                    print(f"\n☕ Emulating natural user rest break ({rest_sec:.1f}s)...")
                    time.sleep(rest_sec)
                    print("▶️ Resuming backfill...\n")

            browser_context.close()

        # Check remaining in DB
        pending_remaining = storage.conn.cursor().execute("""
            SELECT COUNT(*) FROM listings
            WHERE source = 'Facebook'
              AND (images_json IS NULL OR images_json = '[]' OR length(images_json) <= 2)
              AND photos_checked_at IS NULL
              AND is_active = 1
        """).fetchone()[0]

    total_elapsed = (datetime.now() - run_start).total_seconds()
    print("\n" + "=" * 65)
    print("Facebook Photo Backfill Run Summary")
    print(f"Processed Listings:   {processed_count}/{total_targets}")
    print(f"Posts with Photos:    {posts_with_photos}")
    print(f"Total Photos Saved:   {photos_found_count}")
    print(f"Rate-Limited/Blocked: {blocked_count}")
    print(f"Remaining in DB:      {pending_remaining}")
    print(f"Execution Time:       {total_elapsed:.1f}s")
    print("=" * 65 + "\n")

    if regenerate_site_data:
        print("[INFO] Regenerating website public feeds via generate_site_data()...")
        from scrapers.processors.generate_site_data import generate_site_data as run_generator
        run_generator()
        print("✅ Website JSON feeds successfully updated with backfilled photos!")

    return {
        "processed": processed_count,
        "posts_with_photos": posts_with_photos,
        "photos_found": photos_found_count,
        "blocked_count": blocked_count,
        "remaining_in_db": pending_remaining,
        "elapsed_seconds": total_elapsed
    }


def main():
    parser = argparse.ArgumentParser(description="Backfill photos for Facebook real estate listings")
    parser.add_argument("-n", "--limit", type=int, default=None, help="Maximum number of listings to backfill")
    parser.add_argument("--all", action="store_true", help="Backfill all Facebook listings, including inactive")
    parser.add_argument("--visible", action="store_true", help="Launch browser visibly (not headless)")
    parser.add_argument("--skip-site-gen", action="store_true", help="Skip regenerating master JSON feeds")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Minimum pause in seconds between posts")
    parser.add_argument("--delay-max", type=float, default=3.5, help="Maximum pause in seconds between posts")

    args = parser.parse_args()

    run_fb_photos_backfill(
        limit=args.limit,
        headless=not args.visible,
        active_only=not args.all,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        regenerate_site_data=not args.skip_site_gen
    )


if __name__ == "__main__":
    main()
