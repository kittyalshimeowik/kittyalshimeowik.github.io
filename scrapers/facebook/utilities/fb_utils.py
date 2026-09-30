# scrapers/facebook/utilities/fb_utils.py

import os
import re
import time
import base64
from scrapers.utilities.time_utils import parse_creation_time


def extract_canonical_post_id(url, post_id=None):
    if post_id:
        return str(post_id)
        
    if not url:
        return None

    path_match = re.search(r'/(?:posts|permalink|multi_permalink|story\.php)/(\d+)', url)
    if path_match:
        return path_match.group(1)

    query_match = re.search(r'(?:story_fbid|fbid)=(\d+)', url)
    if query_match:
        return query_match.group(1)

    return None


def normalize_url(url):
    if not url: return ""
    if url.startswith("/"): url = "https://www.facebook.com" + url
    clean_url = url.split("?")[0].split("&")[0].rstrip("/")
    clean_url = clean_url.replace("/permalink/", "/posts/")
    return clean_url


def extract_post_id(url):
    match = re.search(r'/(?:posts|permalink)/(\d+)', url)
    return match.group(1) if match else url


def decode_facebook_id(raw_id):
    if not raw_id: return None
    raw_id_str = str(raw_id)
    if raw_id_str.isdigit(): return raw_id_str
    try:
        padded = raw_id_str + "=" * ((4 - len(raw_id_str) % 4) % 4)
        decoded_bytes = base64.b64decode(padded)
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
        if ":" in decoded_str:
            parts = decoded_str.split(":")
            for part in reversed(parts):
                if part.isdigit(): return part
    except Exception:
        pass
    return raw_id_str


def extract_posts_from_graphql_payload(obj, group_id):
    """Recursively traverses Facebook GraphQL response objects to yield post records."""
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


def is_facebook_logged_in(browser_context, page=None):
    """Returns True if user has an active session cookie or logged-in indicators."""
    try:
        if page and not page.is_closed():
            current_url = page.url.lower()
            if "/login" in current_url or "checkpoint" in current_url:
                return False
            if page.locator("input[name='email'], input#email, input[name='pass'], input#pass, input[name='approvals_code']").count() > 0:
                return False
    except Exception:
        pass

    try:
        cookies = browser_context.cookies(["https://www.facebook.com", "https://facebook.com"])
        for c in cookies:
            if c.get("name") == "c_user" and c.get("value"):
                return True
    except Exception:
        pass

    return False


def wait_for_facebook_login(browser_context, page):
    """Checks if logged into Facebook; if not, pauses and waits for user to log in."""
    print("🔍 Checking Facebook authentication status...")
    if is_facebook_logged_in(browser_context, page):
        print("✅ Active Facebook session detected.")
        return

    print("🌐 Navigating to Facebook to verify login state...")
    try:
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        time.sleep(2.5)
    except Exception as e:
        print(f"⚠️ Notice while loading Facebook: {e}")

    if is_facebook_logged_in(browser_context, page):
        print("✅ Active Facebook session verified.")
        return

    print("\n" + "=" * 65)
    print("🔑 FACEBOOK LOGIN REQUIRED")
    print("👉 Please log into your Facebook account in the open browser window.")
    print("👉 Enter your credentials, complete 2FA if prompted, and stay on Facebook.")
    print("⏳ The scraper will automatically detect your login and proceed...")
    print("=" * 65 + "\n")

    try:
        page.bring_to_front()
    except Exception:
        pass

    wait_start = time.time()
    last_prompt = time.time()

    while True:
        try:
            if page.is_closed():
                pages = browser_context.pages
                page = pages[0] if pages else browser_context.new_page()

            if is_facebook_logged_in(browser_context, page):
                print("\n🎉 Facebook login successfully detected!")
                print("💾 Waiting 4 seconds for session tokens to persist...")
                time.sleep(4.0)
                break
        except Exception:
            pass

        time.sleep(1.5)
        if time.time() - last_prompt >= 15:
            elapsed = int(time.time() - wait_start)
            print(f"⏳ Waiting for Facebook login in browser window... ({elapsed}s elapsed)")
            last_prompt = time.time()