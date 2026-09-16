# scrapers/facebook/fb_utils.py

import re
import base64

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