# scrapers/processors/dedup_utils.py

import re
import hashlib
import unicodedata
from datetime import datetime

DEFAULT_EXCHANGE_RATE_AMD_PER_USD = 364.18


def is_ghost_record(item):
    """Returns True if the record has no meaningful text (< 15 chars) and no extracted attributes."""
    if not isinstance(item, dict):
        return True
    text = (item.get("full_text") or item.get("text") or "").strip()
    has_attributes = bool(
        item.get("prices") or 
        item.get("sizes_sqm") or 
        item.get("rooms") or 
        item.get("phone_numbers") or 
        item.get("phone")
    )
    return len(text) < 15 and not has_attributes


def is_valid_display_listing(item):
    """Checks whether a listing is non-ghost and has a classified, displayable category."""
    if is_ghost_record(item):
        return False
    cat = item.get("property_category")
    if not cat or cat in ["General / Unclassified", "Media-Only"]:
        return False
    return True


def normalize_listing_text(text):
    """Sanitizes text for exact and fuzzy deduplication comparisons."""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"https?://\S+|www\.\S+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def listing_completeness_score(post):
    """Scores listings by field count (0 to 7) to prioritize richer records during deduplication."""
    if not isinstance(post, dict):
        return 0
    return sum([
        bool(post.get("full_text")),
        bool(post.get("prices")),
        bool(post.get("sizes_sqm")),
        bool(post.get("rooms")),
        bool(post.get("locations")),
        bool(post.get("phone_numbers")),
        bool(post.get("creation_timestamp"))
    ])


def compute_record_score(post):
    """Weighted completeness score used for master listings post-processing."""
    if not isinstance(post, dict):
        return 0.0
    score = 0.0
    if post.get("prices"): score += 3.0
    if post.get("sizes_sqm"): score += 2.0
    if post.get("rooms"): score += 2.0
    if post.get("locations"): score += 2.0
    if post.get("phone_numbers") or post.get("phone"): score += 3.0
    full_text = post.get("full_text") or ""
    score += len(full_text) / 100.0
    return score


def get_phone_spec_signature(post):
    """Creates a deterministic signature based on phone numbers and property specifications."""
    if not isinstance(post, dict):
        return None
    phones = sorted(list(set(post.get("phone_numbers") or post.get("phone") or [])))
    if isinstance(phones, str):
        phones = [phones]

    prices = tuple(sorted([str(p.get("amount_amd")) for p in post.get("prices", []) if isinstance(p, dict) and p.get("amount_amd")]))
    sizes = tuple(sorted([str(s) for s in (post.get("sizes_sqm") or [])]))
    rooms = tuple(sorted([str(r) for r in (post.get("rooms") or [])]))
    locs = tuple(sorted([str(l) for l in (post.get("locations") or [])]))

    if phones and (prices or sizes or rooms):
        return f"phone_spec:{phones}|{prices}|{sizes}|{rooms}|{locs}"

    text_key = normalize_listing_text(post.get("full_text", ""))
    if text_key and len(text_key) > 20:
        return f"text:{text_key}"

    return None

# Backward-compatibility alias
get_content_signature = get_phone_spec_signature


def listing_content_key(post):
    """Creates a composite content key for exact deduplication."""
    text = normalize_listing_text(post.get("full_text", ""))
    if len(text) < 80:
        return None
    return "|".join([
        text,
        str(post.get("property_category") or ""),
        str(post.get("listing_type") or "")
    ])


def compute_listing_hash(post):
    """Creates a deterministic MD5 signature for state caching."""
    raw = f"{post.get('full_text', '')}|{post.get('property_category')}|{post.get('listing_type')}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def extract_canonical_post_id(url, post_id=None):
    """Extracts the numeric canonical identifier from Facebook or List.am URLs."""
    if post_id:
        return str(post_id)
    if not url:
        return None

    path_match = re.search(r'/(?:posts|permalink|multi_permalink|story\.php|item)/(\d+)', url)
    if path_match:
        return path_match.group(1)

    query_match = re.search(r'(?:story_fbid|fbid)=(\d+)', url)
    if query_match:
        return query_match.group(1)

    return None


def sanitize_filename(text):
    """Produces clean alphanumeric string suitable for safe filesystem paths."""
    if not text:
        return "unknown"
    cleaned = "".join([c for c in text if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_").lower()
    return re.sub(r'_+', '_', cleaned)


def normalize_timestamp(post):
    """Guarantees a valid UTC integer epoch timestamp for sorting across all sources."""
    ts = post.get("creation_timestamp")
    if isinstance(ts, (int, float)) and ts > 0:
        return int(ts)

    created_at_str = post.get("created_at")
    if created_at_str:
        try:
            clean_str = str(created_at_str).replace("Z", "+00:00")
            if "T" in clean_str:
                dt = datetime.fromisoformat(clean_str)
            else:
                dt = datetime.strptime(clean_str[:19], "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp())
        except Exception:
            try:
                dt = datetime.strptime(str(created_at_str)[:10], "%d.%m.%Y")
                return int(dt.timestamp())
            except Exception:
                pass

    ext_str = post.get("extracted_at")
    if ext_str:
        try:
            clean_ext = str(ext_str).replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ext)
            return int(dt.timestamp())
        except Exception:
            pass

    return 0


def normalize_and_convert_prices(prices, exchange_rate=DEFAULT_EXCHANGE_RATE_AMD_PER_USD):
    """Normalizes price dictionaries and converts bidirectionally between AMD and USD."""
    converted_prices = []
    if not prices or not isinstance(prices, list):
        return converted_prices
    
    for p in prices:
        if not isinstance(p, dict):
            continue
        amount = p.get("amount", 0)
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            continue

        curr = str(p.get("currency", "AMD")).upper()
        if curr == "USD":
            amt_usd = amount
            amt_amd = round(amount * exchange_rate)
        else:
            amt_amd = amount
            amt_usd = round(amount / exchange_rate, 2)
            
        converted_prices.append({
            "original_amount": amount,
            "original_currency": curr,
            "amount_amd": amt_amd,
            "amount_usd": amt_usd,
            "raw_text": p.get("raw_text", str(amount))
        })
    return converted_prices
