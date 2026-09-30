# scrapers/listam/utilities/listam_utils.py

import os
import re
import json
import time
import random
import builtins
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.utilities.housing_parser import extract_housing_details


def get_category_file_path(output_dir, cat_id):
    """Returns the standardized JSON file path for a List.am category."""
    return os.path.join(output_dir, f"list_am_category_{cat_id}.json")


def load_dataset_for_category(output_dir, cat_id):
    """Loads existing records and URL set for a given category."""
    file_path = get_category_file_path(output_dir, cat_id)
    if not os.path.exists(file_path):
        return [], set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        urls = set(item.get("url", "") for item in data if item.get("url"))
        return data, urls
    except Exception:
        return [], set()


def save_record_to_disk(output_dir, cat_id, records):
    """Saves records for a List.am category with clean formatting."""
    file_path = get_category_file_path(output_dir, cat_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)


def extract_listing_dates(item_soup):
    """Extracts Posted and Renewed dates from the bottom footer of the listing page."""
    text = item_soup.get_text(" ", strip=True)
    
    posted_date = None
    renewed_date = None
    
    posted_match = re.search(r'Posted\s+(\d{2}\.\d{2}\.\d{4})', text, re.IGNORECASE)
    if posted_match:
        try:
            dt = datetime.strptime(posted_match.group(1), "%d.%m.%Y")
            posted_date = dt.isoformat()
        except Exception:
            pass
            
    renewed_match = re.search(r'Renewed\s+(\d{2}\.\d{2}\.\d{4})(?:,\s*(\d{2}:\d{2}))?', text, re.IGNORECASE)
    if renewed_match:
        try:
            date_str, time_str = renewed_match.groups()
            full_str = f"{date_str} {time_str}" if time_str else date_str
            fmt = "%d.%m.%Y %H:%M" if time_str else "%d.%m.%Y"
            dt = datetime.strptime(full_str, fmt)
            renewed_date = dt.isoformat()
        except Exception:
            pass
            
    if not posted_date and not renewed_date:
        dates = re.findall(r'\b(\d{2}\.\d{2}\.\d{4})\b', text)
        if dates:
            try:
                dt = datetime.strptime(dates[0], "%d.%m.%Y")
                posted_date = dt.isoformat()
            except Exception:
                pass
                
    return posted_date or renewed_date


def human_scroll(driver, is_category_page=False):
    """Simulates natural human scrolling down a page with customizable intensity."""
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        current_position = 0
        
        if is_category_page:
            target_scroll_limit = total_height * random.uniform(0.25, 0.45)
        else:
            target_scroll_limit = total_height * random.uniform(0.5, 0.75)
        
        while current_position < target_scroll_limit:
            scroll_step = random.randint(350, 700)
            current_position += scroll_step
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            
            time.sleep(random.uniform(0.15, 0.35) if is_category_page else random.uniform(0.3, 0.6))
            
            back_probability = 0.05 if is_category_page else 0.15
            if random.random() < back_probability:
                back_step = random.randint(100, 200)
                current_position = max(0, current_position - back_step)
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(random.uniform(0.2, 0.4))
    except Exception:
        pass


def simulate_random_tab_activity(driver):
    """Occasionally opens a blank tab, dwells briefly, and closes it simulating user multitasking."""
    if random.random() < 0.20:
        main_window = driver.current_window_handle
        try:
            driver.execute_script("window.open('about:blank', '_blank');")
            time.sleep(random.uniform(0.4, 0.9))
            
            all_windows = driver.window_handles
            if len(all_windows) > 1:
                new_window = [w for w in all_windows if w != main_window][0]
                driver.switch_to.window(new_window)
                time.sleep(random.uniform(1.0, 2.5))
                if random.random() < 0.90:
                    driver.close()
        except Exception:
            pass
        finally:
            if main_window in driver.window_handles:
                driver.switch_to.window(main_window)


class SafeFloatContext:
    """Safely intercepts float() calls locally during parsing to handle regional numeric formats."""
    def __enter__(self):
        self.original_float = builtins.float
        def safe_float(x):
            if isinstance(x, str):
                x = x.strip()
                if x.count('.') > 1:
                    parts = x.split('.')
                    x = "".join(parts[:-1]) + "." + parts[-1]
                elif ',' in x and '.' in x:
                    if x.rfind(',') > x.rfind('.'):
                        x = x.replace('.', '').replace(',', '.')
                    else:
                        x = x.replace(',', '')
                elif ',' in x:
                    x = x.replace(',', '')
            try:
                return self.original_float(x)
            except Exception:
                return 0.0
        builtins.float = safe_float
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        builtins.float = self.original_float


def safe_extract_housing_details(card_text):
    """Safely executes the external housing parser inside a protected float conversion context."""
    with SafeFloatContext():
        return extract_housing_details(card_text)
