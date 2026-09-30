# -*- coding: utf-8 -*-
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output, ensure_virtualenv
ensure_utf8_output()

import time
import json
import random
import argparse
import platform
import re
from datetime import datetime, timezone

try:
    import setuptools
except ImportError:
    pass
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

def ignore_winerror_6(unraisable):
    if unraisable.exc_value and getattr(unraisable.exc_value, "winerror", None) == 6:
        return
    sys.__unraisablehook__(unraisable)

sys.unraisablehook = ignore_winerror_6

CURRENT_OS = platform.system().lower()
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "housing_posts_data")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "listam_config.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

from scrapers.base_scraper import BaseScraper
from scrapers.utilities.housing_parser import extract_housing_details
from scrapers.utilities.time_utils import format_elapsed_time

# --- Modular List.am Utilities (Re-exported for backward compatibility) ---
from scrapers.listam.utilities.listam_utils import (
    get_category_file_path,
    load_dataset_for_category,
    save_record_to_disk,
    extract_listing_dates,
    human_scroll,
    simulate_random_tab_activity,
    SafeFloatContext,
    safe_extract_housing_details
)


class DirectBrowserListAmScraper(BaseScraper):
    def __init__(self):
        super().__init__(output_subdir="listam")
        self.categories = self.load_categories()
        self.driver = None

    def load_categories(self):
        if not os.path.exists(CONFIG_FILE):
            return []
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def init_driver(self):
        if self.driver is not None:
            return self.driver

        print("🚀 Initializing Undetected ChromeDriver (Fast Mode - Images Disabled)...")
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1366,768")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.experimental_options["prefs"] = prefs

        self.driver = uc.Chrome(options=options, use_subprocess=True)
        
        try:
            self.driver.__del__ = lambda: None
        except Exception:
            pass

        return self.driver

    def handle_cloudflare_loop(self):
        try:
            title = self.driver.title.lower()
            page_src = self.driver.page_source.lower()

            if "just a moment" in title or "verify you are human" in page_src:
                print("\n🛡️ Cloudflare Challenge detected in browser!")
                print("👉 Please solve the checkbox challenge manually in the open window.")
                print("⏳ Waiting for clearance...")

                for _ in range(60):
                    time.sleep(1.5)
                    current_title = self.driver.title.lower()
                    if "just a moment" not in current_title and "verify you are human" not in self.driver.page_source.lower():
                        print("✅ Verification accepted!\n")
                        time.sleep(2)
                        return True
        except Exception:
            pass
        return False

    def run(self, time_limit_min=None, target_category=None):
        categories_to_run = self.categories
        if target_category:
            categories_to_run = [c for c in self.categories if str(c["id"]) == str(target_category)]

        if not categories_to_run:
            print("❌ No matching categories found.")
            return

        cat_time_limit_sec = float(time_limit_min) * 60.0 if time_limit_min is not None else None
        driver = self.init_driver()

        total_categories = len(categories_to_run)

        try:
            for index, cat_item in enumerate(categories_to_run):
                cat_id = str(cat_item["id"])
                cat_name = cat_item.get("name", cat_id)
                default_prop_cat = cat_item.get("property_category", "General / Unclassified")
                default_list_type = cat_item.get("listing_type", "Sale")

                categories_left = total_categories - index - 1

                category_records, seen_urls = load_dataset_for_category(OUTPUT_DIR, cat_id)

                print(f"\n==============================================")
                print(f"🎯 Category: {cat_name} (ID: {cat_id})")
                print(f"📊 Progress: Category {index + 1} of {total_categories} | Remaining Categories: {categories_left}")
                print(f"📁 File: {OUTPUT_DIR}/list_am_category_{cat_id}.json")
                if cat_time_limit_sec:
                    print(f"⏱️ Time Limit per Category: {format_elapsed_time(cat_time_limit_sec)}")
                print(f"==============================================")

                cat_start_time = time.time()
                cat_end_time = (cat_start_time + cat_time_limit_sec) if cat_time_limit_sec else float('inf')

                page_num = 1
                empty_streak = 0
                no_new_streak = 0

                while time.time() < cat_end_time:
                    if time.time() >= cat_end_time:
                        print(f"⏱️ Time limit reached for category {cat_name}. Stopping.")
                        break

                    elapsed_sec = time.time() - cat_start_time
                    time_left_sec = max(0, cat_end_time - time.time()) if cat_time_limit_sec else None

                    if cat_time_limit_sec is not None:
                        time_str = f"Elapsed: {format_elapsed_time(elapsed_sec)} / {format_elapsed_time(cat_time_limit_sec)} (Left: {format_elapsed_time(time_left_sec)})"
                    else:
                        time_str = f"Elapsed: {format_elapsed_time(elapsed_sec)}"

                    if page_num == 1:
                        target_url = f"https://www.list.am/category/{cat_id}?srt=3"
                    else:
                        target_url = f"https://www.list.am/category/{cat_id}/{page_num}?srt=3"

                    print(f"\n📍 Requesting Page {page_num}: {target_url} | {time_str}")
                    time.sleep(random.uniform(1.5, 3.0))

                    try:
                        driver.get(target_url)
                        self.handle_cloudflare_loop()
                        
                        # 🧠 Inject light human behavior on category pages
                        human_scroll(driver, is_category_page=True)
                        simulate_random_tab_activity(driver)
                        
                        html_content = driver.page_source
                    except Exception as e:
                        print(f"⚠️ Error loading page: {e}")
                        break

                    soup = BeautifulSoup(html_content, "html.parser")
                    cards = soup.select("a[href*='/item/']")
                    page_items = []

                    for card in cards:
                        href = card.get("href")
                        if not href:
                            continue

                        full_url = href if href.startswith("http") else f"https://www.list.am{href}"
                        if full_url in seen_urls:
                            continue

                        card_text = card.get_text(separator=" ", strip=True)
                        page_items.append({"url": full_url, "text": card_text})

                    unique_page_items = []
                    seen_page_urls = set()
                    for item in page_items:
                        if item["url"] not in seen_page_urls:
                            seen_page_urls.add(item["url"])
                            unique_page_items.append(item)

                    if not unique_page_items:
                        empty_streak += 1
                        no_new_streak += 1
                        print(f"⚠️ No new listings on page {page_num} (streak: {empty_streak})")
                        if empty_streak >= 2 or no_new_streak >= 3:
                            print(f"🛑 Reached end of category or no new pages left. Moving to next category.")
                            break
                    else:
                        empty_streak = 0
                        no_new_streak = 0
                        print(f"📦 Captured {len(unique_page_items)} new listing links on page {page_num}. Visiting item pages for full details...")

                        for item in unique_page_items:
                            if time.time() >= cat_end_time:
                                print(f"⏱️ Time limit reached during item processing. Stopping category.")
                                break

                            url = item["url"]
                            if url in seen_urls:
                                continue
                            seen_urls.add(url)
                            item_id = url.split("/item/")[-1].split("?")[0]

                            try:
                                driver.get(url)
                                self.handle_cloudflare_loop()
                                
                               # 🧠 Deeper scroll for item details page
                                human_scroll(driver, is_category_page=False)
                                
                                item_soup = BeautifulSoup(driver.page_source, "html.parser")

                                title_elem = item_soup.find("h1")
                                title = title_elem.get_text(strip=True) if title_elem else item["text"]

                                body_div = item_soup.find("div", {"id": "pbody"}) or item_soup.find("div", {"class": "body"})
                                body_text = body_div.get_text("\n", strip=True) if body_div else item["text"]

                                price_elem = item_soup.find("span", {"class": "price"}) or item_soup.find("span", {"itemprop": "price"})
                                price_text = price_elem.get_text(strip=True) if price_elem else ""

                                loc_elem = item_soup.find("div", {"class": "loc"}) or item_soup.find("span", {"itemprop": "name"})
                                loc_text = loc_elem.get_text(strip=True) if loc_elem else ""

                                attr_div = item_soup.find("div", {"id": "attr"}) or item_soup.find("div", {"class": "attr"})
                                attr_text = attr_div.get_text(" ", strip=True) if attr_div else ""

                                created_at = extract_listing_dates(item_soup)

                                full_text = f"{title}\nPrice: {price_text}\nLocation: {loc_text}\nAttributes: {attr_text}\n{body_text}".strip()
                            except Exception as e:
                                print(f"⚠️ Error loading item page {url}: {e}")
                                full_text = item["text"]
                                created_at = None

                            parsed = safe_extract_housing_details(full_text)

                            parsed_list_type = parsed.get("listing_type")
                            listing_type = (
                                parsed_list_type 
                                if parsed_list_type and parsed_list_type.lower() != "unknown" 
                                else default_list_type
                            )

                            creation_ts = None
                            if created_at:
                                try:
                                    dt = datetime.fromisoformat(created_at)
                                    creation_ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
                                except Exception:
                                    pass
                            if not creation_ts:
                                creation_ts = int(datetime.now(timezone.utc).timestamp())

                            record = {
                                "url": url,
                                "canonical_id": f"list_am_{item_id}",
                                "source": "List.am",
                                "category_id": cat_id,
                                "extracted_at": datetime.now(timezone.utc).isoformat(),
                                "created_at": created_at,
                                "creation_timestamp": creation_ts,
                                "has_text": bool(full_text),
                                "property_category": parsed.get("property_category") or default_prop_cat,
                                "listing_type": listing_type,
                                "prices": parsed.get("prices", []),
                                "sizes_sqm": parsed.get("sizes_sqm", []),
                                "rooms": parsed.get("rooms", []),
                                "locations": parsed.get("locations", []),
                                "phone_numbers": parsed.get("phone_numbers", []),
                                "full_text": full_text,
                            }
                            category_records.append(record)
                            time.sleep(random.uniform(0.1, 0.3))

                        save_record_to_disk(OUTPUT_DIR, cat_id, category_records)
                        print(f"⏳ Total Captured: {len(category_records)} | {time_str}")

                    if time.time() >= cat_end_time:
                        print(f"⏱️ Time limit reached. Ending category run.")
                        break

                    page_num += 1

                print(f"✅ Finished category {cat_name}. Categories remaining: {categories_left}")

        finally:
            if self.driver:
                print("\n🔒 Closing browser window and cleaning up driver session...")
                try:
                    self.driver.close()
                except Exception:
                    pass

                try:
                    old_stderr = sys.stderr
                    sys.stderr = open(os.devnull, 'w', encoding='utf-8')
                    
                    self.driver.__del__ = lambda: None
                    if hasattr(self.driver, 'quit'):
                        self.driver.quit()
                        
                    sys.stderr.close()
                    sys.stderr = old_stderr
                except Exception:
                    pass
                
                self.driver = None
                print("✅ Browser successfully closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct Browser List.am Scraper")
    parser.add_argument("positional_time", nargs="?", type=float, default=None)
    parser.add_argument("-t", "--time-limit", type=float, default=None)
    parser.add_argument("-c", "--category", type=str, default=None)
    args = parser.parse_args()

    t_limit = args.time_limit if args.time_limit is not None else args.positional_time
    scraper = DirectBrowserListAmScraper()
    scraper.run(time_limit_min=t_limit, target_category=args.category)