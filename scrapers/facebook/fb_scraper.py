import os
import sys
import io
import platform

CURRENT_OS = platform.system().lower()

if CURRENT_OS == "windows":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.environ["TZ"] = "UTC"

import time
import json
import random
import argparse
from datetime import datetime
from playwright.sync_api import sync_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "housing_posts_data")
METADATA_DIR = os.path.join(SCRIPT_DIR, "groups_metadata") 
GROUPS_CONFIG_FILE = os.path.join(SCRIPT_DIR, "groups_config.json")
BASE_SESSION_DIR = os.path.expanduser("~/Desktop/fb-scraper-project")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(BASE_SESSION_DIR, exist_ok=True)

if CURRENT_OS == "windows":
    USER_DATA_DIR = os.path.join(BASE_SESSION_DIR, "fb_session_windows")
else:
    MACHINE_HOSTNAME = platform.node() or "unknown_machine"
    USER_DATA_DIR = os.path.join(BASE_SESSION_DIR, f"fb_session_{MACHINE_HOSTNAME}")
    MACHINE_MARKER_FILE = os.path.join(BASE_SESSION_DIR, "active_machine_marker.txt")

    if os.path.exists(MACHINE_MARKER_FILE):
        try:
            with open(MACHINE_MARKER_FILE, "r", encoding="utf-8") as f:
                last_machine = f.read().strip()
            if last_machine != MACHINE_HOSTNAME:
                print(f"🔄 New machine/hostname detected. Cleaning up old session profile...")
                import shutil
                if os.path.exists(USER_DATA_DIR):
                    shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
        except Exception:
            pass

    with open(MACHINE_MARKER_FILE, "w", encoding="utf-8") as f:
        f.write(MACHINE_HOSTNAME)

# --- Modular Imports ---
from scrapers.facebook.utilities.fb_utils import extract_canonical_post_id, decode_facebook_id
from scrapers.utilities.time_utils import format_elapsed_time, parse_relative_time, find_relative_string_in_dict, parse_creation_time
from scrapers.utilities.housing_parser import extract_housing_details
from scrapers.utilities.browser_humanizer import perform_human_action_chain, check_global_break, extract_timestamp_from_dom, smooth_scroll
from scrapers.facebook.utilities.fb_metadata_storage import (
    load_target_groups, update_group_config_status, calculate_dynamic_runtime,
    load_dataset_for_group, save_post_to_memory_and_disk, update_group_metadata
)


def extract_posts_from_graphql_payload(obj, group_id):
    if isinstance(obj, dict):
        if "comet_sections" in obj or "message" in obj:
            try:
                story = obj.get("comet_sections", {}).get("content", {}).get("story", {}) or obj
                
                raw_post_id = story.get("post_id") or story.get("id")
                raw_url = story.get("url")

                if raw_url:
                    final_url = "https://www.facebook.com" + raw_url if raw_url.startswith("/") else raw_url
                elif raw_post_id:
                    real_id = decode_facebook_id(raw_post_id)
                    final_url = f"https://www.facebook.com/groups/{group_id}/posts/{real_id}"
                else:
                    final_url = None

                canonical_id = extract_canonical_post_id(final_url, raw_post_id)

                if final_url and f"/groups/{group_id}" in final_url:
                    message_dict = story.get("message", {})
                    text = message_dict.get("text") if isinstance(message_dict, dict) else ""

                    attachment_texts = []
                    attachments = story.get("attachments", [])
                    for att in attachments:
                        media_node = att.get("media", {})
                        accessibility_caption = media_node.get("accessibility_caption")
                        if accessibility_caption:
                            attachment_texts.append(accessibility_caption)
                        
                        for subatt in media_node.get("all_subattachments", {}).get("nodes", []):
                            sub_cap = subatt.get("media", {}).get("accessibility_caption")
                            if sub_cap:
                                attachment_texts.append(sub_cap)

                    combined_text = text if text else ""
                    if attachment_texts:
                        combined_text += "\n" + "\n".join(attachment_texts)

                    is_media_only = not bool(text and text.strip()) and bool(attachments)
                    time_data = parse_creation_time(obj)
                    actors = story.get("actors", [])
                    author_name = actors[0].get("name") if actors and isinstance(actors[0], dict) else None

                    yield {
                        "url": final_url,
                        "canonical_id": canonical_id,
                        "text": combined_text,
                        "is_media_only": is_media_only,
                        "creation_timestamp": time_data["timestamp"],
                        "created_at": time_data["formatted"],
                        "author": author_name,
                        "raw_node": obj
                    }
                    return 
            except Exception:
                pass

        for value in obj.values():
            yield from extract_posts_from_graphql_payload(value, group_id)

    elif isinstance(obj, list):
        for item in obj:
            yield from extract_posts_from_graphql_payload(item, group_id)


def run_facebook_housing_scraper():
    target_groups = load_target_groups(GROUPS_CONFIG_FILE, METADATA_DIR)
    if not target_groups:
        print("❌ No target groups found in groups_config.json.")
        return

    parser = argparse.ArgumentParser(description="Facebook Housing Posts Scraper")
    parser.add_argument("positional_time", nargs="?", type=float, default=None, help="Time limit in minutes per group (positional)")
    parser.add_argument("-t", "--time-limit", type=float, default=None, help="Time limit in minutes per group (flag)")
    
    parsed_args, _ = parser.parse_known_args()
    cli_runtime_min = parsed_args.time_limit if parsed_args.time_limit is not None else parsed_args.positional_time

    cli_runtime_sec = None
    if cli_runtime_min is not None:
        try:
            cli_runtime_sec = float(cli_runtime_min) * 60.0
            print(f"⏱️ CLI Override active: Forcing runtime to {cli_runtime_min} minutes per group.")
        except ValueError:
            print("⚠️ Invalid argument for runtime provided. Falling back to dynamic metadata calculation.")

    mouse_pos = {"x": 680, "y": 400}
    global_timer_state = {"next_break_due": time.time() + random.randint(480, 720)}

    with sync_playwright() as p:
        context_args = {
            "user_data_dir": USER_DATA_DIR,
            "headless": False,
            "viewport": {"width": 1366, "height": 768},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }

        if CURRENT_OS == "windows":
            context_args["ignore_default_args"] = ["--enable-automation"]
            context_args["args"] = ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars"]
        else:
            context_args["args"] = ["--disable-blink-features=AutomationControlled"]

        browser_context = p.chromium.launch_persistent_context(**context_args)
        open_tabs = list(browser_context.pages)
        initial_blank_page = open_tabs[0] if open_tabs else None

        current_active_group_id = {"id": None}
        current_session_posts = []
        group_posts_cache = []
        group_urls_cache = set()

        def handle_response(response):
            if "api/graphql" in response.url and response.status == 200:
                target_group_id = current_active_group_id["id"]
                if not target_group_id:
                    return
                try:
                    raw_text = response.text()
                    for line in raw_text.split("\n"):
                        line = line.strip()
                        if not line: continue
                        try:
                            payload = json.loads(line)
                            for post in extract_posts_from_graphql_payload(payload, target_group_id):
                                url = post["url"]
                                canonical_id = post.get("canonical_id")
                                if f"/groups/{target_group_id}" in url:
                                    active_page = browser_context.pages[0] if browser_context.pages else None
                                    details = extract_housing_details(post["text"], is_media_only=post["is_media_only"])
                                    time_formatted = post["created_at"]
                                    time_epoch = post["creation_timestamp"]

                                    if not time_formatted:
                                        rel_data = find_relative_string_in_dict(post["raw_node"])
                                        if rel_data:
                                            time_formatted = rel_data["formatted"]
                                            time_epoch = rel_data["timestamp"]

                                    if not time_formatted and active_page:
                                        dom_time_str = extract_timestamp_from_dom(active_page, url)
                                        if dom_time_str:
                                            rel_data = parse_relative_time(dom_time_str)
                                            if rel_data:
                                                time_formatted = rel_data["formatted"]
                                                time_epoch = rel_data["timestamp"]

                                    record = {
                                        "url": url,
                                        "canonical_id": canonical_id,
                                        "group_id": target_group_id,
                                        "extracted_at": datetime.now().isoformat(),
                                        "created_at": time_formatted,
                                        "creation_timestamp": time_epoch,
                                        "author": post["author"],
                                        "has_text": details["has_text"],
                                        "is_media_only": details["is_media_only"],
                                        "property_category": details["property_category"],
                                        "listing_type": details["listing_type"],
                                        "is_negotiable": details["is_negotiable"],
                                        "floor_info": details["floor_info"],
                                        "prices": details["prices"],
                                        "sizes_sqm": details["sizes_sqm"],
                                        "rooms": details["rooms"],
                                        "locations": details["locations"],
                                        "phone_numbers": details["phone_numbers"],
                                        "full_text": post["text"],
                                    }

                                    current_session_posts.append(record)
                                    save_post_to_memory_and_disk(OUTPUT_DIR, target_group_id, group_posts_cache, group_urls_cache, record)
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    pass

        browser_context.on("response", handle_response)

        remaining_groups = list(target_groups)
        visited_groups_count = 0
        previous_page = None

        while remaining_groups:
            group = random.choice(remaining_groups)
            remaining_groups.remove(group)
            visited_groups_count += 1

            group_id = str(group["id"])
            group_name = group["name"]
            group_url = f"https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL"
            
            group_posts_cache, group_urls_cache = load_dataset_for_group(OUTPUT_DIR, group_id)

            if cli_runtime_sec is not None:
                calculated_runtime = cli_runtime_sec
                target_days = 3
            else:
                calculated_runtime, target_days = calculate_dynamic_runtime(METADATA_DIR, group_id)

            print(f"\n==============================================")
            print(f"🎯 Group [{visited_groups_count}/{len(target_groups)}]: {group_name} ({group_id})")
            print(f"📁 Posts File: {OUTPUT_DIR}/extracted_housing_posts_{group_id}.json")
            print(f"📁 Metadata File: {METADATA_DIR}/groups_metadata_{group_id}.json")
            print(f"🧠 Strategy: ~{target_days}-day window | Allotted Time: {format_elapsed_time(calculated_runtime)}")
            print(f"==============================================")

            current_session_posts.clear()
            current_active_group_id["id"] = group_id

            if visited_groups_count == 1 and initial_blank_page and not initial_blank_page.is_closed() and initial_blank_page.url == "about:blank":
                page = initial_blank_page
            else:
                page = browser_context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

            if previous_page and previous_page != page and not previous_page.is_closed():
                if random.choice([True, False]):
                    print(f"🧹 [Tab Manager] Closing previous group tab...")
                    try:
                        previous_page.close()
                    except Exception:
                        pass
                else:
                    print(f"📌 [Tab Manager] Keeping previous tab open in background.")

            previous_page = page
            session_start_time = time.time()
            group_end_time = session_start_time + calculated_runtime

            print(f"Navigating to {group_url}...")
            page.goto(group_url)
            time.sleep(random.uniform(4.0, 6.0))

            last_scroll_height = page.evaluate("document.body.scrollHeight")
            stagnant_counter = 0
            last_post_count = len(current_session_posts)

            while time.time() < group_end_time:
                check_global_break(global_timer_state, page, mouse_pos, CURRENT_OS)
                perform_human_action_chain(page, mouse_pos, CURRENT_OS)
                
                current_height = page.evaluate("document.body.scrollHeight")
                current_post_count = len(current_session_posts)

                if current_height <= last_scroll_height and current_post_count == last_post_count:
                    stagnant_counter += 1
                else:
                    stagnant_counter = 0
                    last_scroll_height = max(last_scroll_height, current_height)
                    last_post_count = current_post_count

                if stagnant_counter >= 6:
                    print(f"⚠️ [{group_name}] Feed paused. Nudging scroll...")
                    smooth_scroll(page, direction="up", pixels=300)
                    time.sleep(1.5)
                    smooth_scroll(page, direction="down", pixels=700)
                    time.sleep(3.0)
                    
                    new_height = page.evaluate("document.body.scrollHeight")
                    current_post_count = len(current_session_posts)
                    
                    if new_height <= last_scroll_height and current_post_count == last_post_count:
                        print(f"🛑 [{group_name}] Page fully stuck or end of feed reached.")
                        break
                    else:
                        print(f"✅ [{group_name}] Feed un-stuck successfully!")
                        stagnant_counter = 0
                        last_scroll_height = new_height
                        last_post_count = current_post_count

                if len(current_session_posts) >= 25:
                    now_ts = datetime.now().timestamp()
                    post_ages = []
                    for p in current_session_posts:
                        ts = p.get("creation_timestamp")
                        if ts and ts <= now_ts:
                            age_d = (now_ts - ts) / (3600.0 * 24.0)
                            post_ages.append(age_d if 0 <= age_d <= 365 else None)
                        else:
                            post_ages.append(None)

                    evaluated_ages = post_ages[5:] if len(post_ages) > 5 else []
                    consecutive_old_streak = 0
                    max_streak = 0
                    for age in evaluated_ages:
                        if age is not None and age > 30.0:
                            consecutive_old_streak += 1
                            if consecutive_old_streak > max_streak:
                                max_streak = consecutive_old_streak
                        else:
                            consecutive_old_streak = 0

                    if max_streak >= 10:
                        print(f"🛑 Reached consecutive streak of {max_streak} posts older than 30 days. Stopping scan early.")
                        break

                elapsed_sec = time.time() - session_start_time
                print(f"⏳ [{group_name}] Elapsed: {format_elapsed_time(elapsed_sec)} / {format_elapsed_time(calculated_runtime)} | Captured: {len(current_session_posts)}")

            session_duration = time.time() - session_start_time
            update_group_metadata(METADATA_DIR, group_id, group_name, current_session_posts, session_duration)
            update_group_config_status(METADATA_DIR, group_id, len(current_session_posts))
            print(f"📊 Updated isolated metadata for: {group_name}")

        browser_context.close()
        print(f"\nAll groups scanned. Data stored in '{OUTPUT_DIR}/' and '{METADATA_DIR}/'.")

if __name__ == "__main__":
    run_facebook_housing_scraper()