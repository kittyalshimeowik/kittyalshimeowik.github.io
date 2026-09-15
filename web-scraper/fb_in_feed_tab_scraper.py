import os
import sys
import io
import platform

CURRENT_OS = platform.system().lower()

# Force UTF-8 encoding and apply line buffering specifically for Windows to fix command-line echoing
if CURRENT_OS == "windows":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.environ["TZ"] = "UTC" # Ensure stable time calculations

import re
import time
import json
import random
import base64
import argparse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# --- File Paths & Directories ---
OUTPUT_DIR = "housing_posts_data"
METADATA_DIR = "groups_metadata"
GROUPS_CONFIG_FILE = "groups_config.json"

BASE_SESSION_DIR = os.path.expanduser("~/Desktop/fb-scraper-project")

# Ensure required base directories exist first
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(BASE_SESSION_DIR, exist_ok=True)

# OS-conditional session handling: Keep Mac 100% untouched, fix Windows session permanence
if CURRENT_OS == "windows":
    USER_DATA_DIR = os.path.join(BASE_SESSION_DIR, "fb_session_windows")
else:
    MACHINE_HOSTNAME = platform.node() or "unknown_machine"
    USER_DATA_DIR = os.path.join(BASE_SESSION_DIR, f"fb_session_{MACHINE_HOSTNAME}")
    MACHINE_MARKER_FILE = os.path.join(BASE_SESSION_DIR, "active_machine_marker.txt")

    # Intelligent wipe check: if the specific machine hostname changes, clear old session data (Mac only)
    if os.path.exists(MACHINE_MARKER_FILE):
        try:
            with open(MACHINE_MARKER_FILE, "r", encoding="utf-8") as f:
                last_machine = f.read().strip()
            if last_machine != MACHINE_HOSTNAME:
                print(f"🔄 New machine/hostname detected (from '{last_machine}' to '{MACHINE_HOSTNAME}'). Cleaning up old session profile to prevent conflicts...")
                import shutil
                if os.path.exists(USER_DATA_DIR):
                    shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
        except Exception:
            pass

    # Update marker file with current machine hostname
    with open(MACHINE_MARKER_FILE, "w", encoding="utf-8") as f:
        f.write(MACHINE_HOSTNAME)

# --- Optimized & Multilingual Regular Expression Patterns ---
PHONE_NUMBER_PATTERN = re.compile(
    r'(?:'
    r'\+\d{1,3}[\s\./\-\u2010-\u2015\u2212\u00ad]*\(?\d{1,4}\)?[\s\./\-\u2010-\u2015\u2212\u00ad]*\d{2,4}[\s\./\-\u2010-\u2015\u2212\u00ad]*\d{2,4}[\s\./\-\u2010-\u2015\u2212\u00ad]*\d{2,4}'
    r'|'
    r'(?:\+?374[\s\./\-\u2010-\u2015\u2212\u00ad֊]*|0)(?:10|11|12|33|41|43|44|55|77|91|93|94|95|96|97|98|99)'
    r'(?:[\s\./\-\u2010-\u2015\u2212\u00ad֊]*\(?(?:0|\+?374)?(?:10|11|12|33|41|43|44|55|77|91|93|94|95|96|97|98|99)\)?)?'
    r'(?:[\s\./\-\u2010-\u2015\u2212\u00ad֊]*\d){6}\b'
    r')'
)

SIZE_PATTERN = re.compile(
    r'(?:(?P<size1>\d{2,4}(?:[.,]\d+)?)\s*[-֊:]*\s*(?:քմ|ք\.մ\.|ք․մ․|ք\.\s*մ|քառակուսի\s+մետր|քառ\.\s*մ\.|sq\s*m|sq\.m\.|sqm|m2|m²|ք/մ|qm|q\.m\.|м²|кв\.?\s*м\.?))'
    r'|'
    r'(?:(?:քմ|ք\.մ\.|ք․մ․|ք\.\s*մ|քառակուսի\s+մետր|քառ\.\s*մ\.|sq\s*m|sq\.m\.|sqm|m2|m²|ք/մ|qm|q\.m\.|м²|кв\.?\s*м\.?)\s*[-֊:]*\s*(?P<size2>\d{2,4}(?:[.,]\d+)?))',
    re.IGNORECASE
)

ROOM_PATTERN = re.compile(
    r'(?:(?P<rooms1>\d{1,2})\s*[-֊:]*\s*(?:սենյակ|սենյականոց|սեն\.|room|rooms|bed|bd|bedrooms|комн(?:\.|аты|ат)?))'
    r'|'
    r'(?:(?:սենյակ|սենյականոց|սեն\.|room|rooms|bed|bd|bedrooms|комн(?:\.|аты|ат)?)\s*[-֊:]*\s*(?P<rooms2>\d{1,2}))',
    re.IGNORECASE
)

FLOOR_PATTERN = re.compile(
    r'\b(?P<floor>\d{1,2})\s*/\s*(?P<total_floors>\d{1,2})\s*(?:հարկ|этаж|этажа)\b',
    re.IGNORECASE
)

DIMENSION_PATTERN = re.compile(r'\d+(?:[.,]\d+)?\s*(?:մ|մետր|կմ|սմ|м|метр|км|см)\b', re.IGNORECASE)
COUNT_ITEM_PATTERN = re.compile(r'\d+\s*(?:հարկ|հարկանի|տարի|սենյակ|բնակարան|этаж|комната|квартира)\b', re.IGNORECASE)
TREE_COUNT_PATTERN = re.compile(r'\b\d+\s+(?:[\wԱ-Ֆա-ֆА-Яа-я]+[\s\-]+){0,4}(?:ծառ|ծառեր|տնկի|տնկիներ|дерево|деревьев)\b', re.IGNORECASE)
PROPERTY_CODE_PATTERN = re.compile(r'(?:[A-Z]{1,4}\d*[_\\-]*)?(?:կոդ|id|լոտ|համար|код)[\s\./\-—–_,:;՝’\']*\d{3,7}\b|\b[A-Z]{2,4}\d+[_\\-]\d+\b', re.IGNORECASE)
PERCENT_PATTERN = re.compile(r'\d+(?:[.,]\d+)?\s*%', re.IGNORECASE)

PRICE_CURRENCY_PATTERN = re.compile(
    r'(?P<pre_curr>\$|֏|€|USD|AMD|EUR|dram|դրամ|դոլար|dollar|տոլար|հհ\s*դրամ|руб|рублей)?\s*'
    r'(?P<amount>[1-9]\d{0,2}(?:[,\s\.]\d{3})+|[1-9]\d{2,5})\s*'
    r'(?P<post_curr>\$|֏|€|USD|AMD|EUR|dram|դրամ|դոլար|dollar|տոլար|հհ\s*դրամ|руб|рублей)?',
    re.IGNORECASE
)

RELATIVE_TIME_PATTERN = re.compile(r'(\d+)\s*(min|mins|minute|minutes|hr|hrs|hour|hours|d|day|days|ր|րոպե|ժամ|օր)', re.IGNORECASE)

CURRENCY_MAP = {
    '$': 'USD', 'usd': 'USD', 'dollar': 'USD', 'դոլար': 'USD', 'տոլար': 'USD',
    '֏': 'AMD', 'amd': 'AMD', 'dram': 'AMD', 'դրամ': 'AMD', 'հհ դրամ': 'AMD', 'հհդրամ': 'AMD',
    '€': 'EUR', 'eur': 'EUR', 'euro': 'EUR',
    'руб': 'RUB', 'рублей': 'RUB'
}

LOCATION_DICTIONARY = {
    "Kentron / Center": ["կենտրոն", "կենտրոնում", "kentron", "center", "centr", "downtown", "центр", "центральный", "каскад", "cascade", "հանրապետության", "hanrapetutyan", "ամիրյան", "amiryan"],
    "Arabkir": ["արաբկիր", "արաբկիրում", "arabkir", "арабкир", "комитас", "կոմիտաս", "կոմիտասում", "komitas", "барекамутюн", "բարեկամություն", "barekamutyun"],
    "Davtashen": ["դավթաշեն", "դավթաշենում", "դավթաշենի", "davtashen", "davitashen", "давиташен"],
    "Zeytun / Kanaker": ["զեյթուն", "զեյթունում", "zeitun", "zeytun", "зейтун", "канакер", "канакер-зейтун", "քանաքեռ", "kanaker", "паруйра севака", "ераз"],
    "Nor Nork / Massiv": ["նոր նորք", "нор норк", "норк", "նորքի", "մասիվ", "մասիվի", "մասիվում", "massiv", "nor nork", "массив"],
    "Avan": ["ավան", "аван", "ավանում", "ավանի", "avan"],
    "Malatia-Sebastia": ["մալաթիա", "малатия", "себастия", "սեբաստիա", "մալաթիայում", "malatia", "sebastia", "бангладеш", "բանգլադեշ"],
    "Shengavit": ["շենգավիթ", "шенгавит", "շենգավիթում", "shengavit", "чарбах", "չարբախ", "charbakh", "гарегин нжде", "գարեգին նժդեհ"],
    "Ajapnyak": ["աջափնյակ", "ачапняк", "աջափնյակում", "ajapnyak", "16-րդ", "16rd", "назарбекян", "նազարբեկյան"],
    "Erebuni": ["էրեբունի", "эребуни", "էրեբունիում", "erebuni"],
    "Nork-Marash": ["նորք-մարաշ", "норк-мараш", "նորք մարաշ", "nork marash"]
}

CATEGORY_TRANSLATION_MAP = {
    "Apartment": "Apartment",
    "House": "House",
    "Land": "Land",
    "Media-Only": "Media-Only",
    "General / Unclassified": "General"
}

LISTING_TRANSLATION_MAP = {
    "Rent": "Rent",
    "Sale": "Sale",
    "Unknown": "General"
}

TIMESTAMP_KEYS = {"creation_time", "publish_time", "created_time", "post_timestamp", "timestamp", "story_creation_time", "system_creation_time", "time"}


def format_elapsed_time(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def get_group_metadata_file_path(group_id):
    return os.path.join(METADATA_DIR, f"groups_metadata_{group_id}.json")


def load_target_groups():
    if not os.path.exists(GROUPS_CONFIG_FILE):
        default_groups = ["445452547795422"]
        with open(GROUPS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_groups, f, indent=4)
    
    group_ids = []
    try:
        with open(GROUPS_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                group_ids = [str(item) for item in data]
    except Exception:
        group_ids = ["445452547795422"]

    structured_groups = []
    for g_id in group_ids:
        meta_path = get_group_metadata_file_path(g_id)
        g_meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    g_meta = json.load(f)
            except Exception:
                pass

        structured_groups.append({
            "id": g_id,
            "name": g_meta.get("name", f"Group {g_id}"),
            "last_scraped": g_meta.get("last_scraped", None),
            "total_collected": g_meta.get("total_collected", 0)
        })
    return structured_groups


def update_group_config_status(group_id, new_posts_count):
    meta_path = get_group_metadata_file_path(group_id)
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    metadata["last_scraped"] = datetime.now().isoformat()
    metadata["total_collected"] = metadata.get("total_collected", 0) + new_posts_count

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)


def calculate_dynamic_runtime(group_id):
    max_group_limit_sec = float(random.randint(720, 900))
    default_fallback_sec = min(180.0, max_group_limit_sec)
    
    meta_path = get_group_metadata_file_path(group_id)
    if not os.path.exists(meta_path):
        return default_fallback_sec, 3

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            group_meta = json.load(f)
            
        benchmarks = group_meta.get("scroll_benchmarks", {})
        if not benchmarks:
            return default_fallback_sec, 3

        sorted_dates = sorted(benchmarks.keys())
        last_date_str = sorted_dates[-1] if sorted_dates else None
        
        target_days = 3
        if last_date_str:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            days_diff = (datetime.now().date() - last_date).days
            if days_diff <= 1:
                target_days = 1

        if target_days == 1 and "avg_scroll_time_1_day_sec" in group_meta:
            calculated_time = max(group_meta["avg_scroll_time_1_day_sec"], 45.0)
            return min(calculated_time, max_group_limit_sec), target_days

        matching_durations = [
            b.get("scroll_duration_seconds", 0) 
            for b in benchmarks.values() 
            if b.get("oldest_post_age_hours", 0) >= (target_days * 24 * 0.7)
        ]
        if matching_durations:
            avg_duration = sum(matching_durations) / len(matching_durations)
            calculated_time = max(avg_duration, 45.0)
            return min(calculated_time, max_group_limit_sec), target_days

        return default_fallback_sec, 3
    except Exception:
        return default_fallback_sec, 3


def is_valid_unix_timestamp(val):
    try:
        ts = int(val)
        if ts > 1000000000000:
            ts = ts // 1000
        if 1577836800 <= ts <= 1893456000:
            return ts
    except (ValueError, TypeError):
        pass
    return None


def find_timestamp_in_dict(obj):
    if isinstance(obj, dict):
        for key in TIMESTAMP_KEYS:
            if key in obj:
                ts = is_valid_unix_timestamp(obj[key])
                if ts: return ts
                if isinstance(obj[key], (dict, list)):
                    res = find_timestamp_in_dict(obj[key])
                    if res: return res
        if "metadata" in obj and isinstance(obj["metadata"], list):
            for meta_item in obj["metadata"]:
                res = find_timestamp_in_dict(meta_item)
                if res: return res
        for v in obj.values():
            res = find_timestamp_in_dict(v)
            if res: return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_timestamp_in_dict(item)
            if res: return res
    return None


def parse_relative_time(text, reference_dt=None):
    if not text: return None
    ref = reference_dt or datetime.now()
    match = RELATIVE_TIME_PATTERN.search(str(text))
    if not match: return None
    val = int(match.group(1))
    unit = match.group(2).lower()
    
    if unit in ['min', 'mins', 'minute', 'minutes', 'ր', 'րոպե']: dt = ref - timedelta(minutes=val)
    elif unit in ['hr', 'hrs', 'hour', 'hours', 'ժամ']: dt = ref - timedelta(hours=val)
    elif unit in ['d', 'day', 'days', 'օր']: dt = ref - timedelta(days=val)
    else: return None
        
    return {"timestamp": int(dt.timestamp()), "formatted": dt.strftime("%Y-%m-%d %H:%M:%S")}


def find_relative_string_in_dict(obj):
    if isinstance(obj, dict):
        for k in ["text", "accessibility_caption", "aria_label"]:
            if k in obj and isinstance(obj[k], str):
                parsed = parse_relative_time(obj[k])
                if parsed: return parsed
        for v in obj.values():
            res = find_relative_string_in_dict(v)
            if res: return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_relative_string_in_dict(item)
            if res: return res
    return None


def extract_timestamp_from_dom(page, post_url):
    try:
        time_text = page.evaluate("""
            (targetUrl) => {
                const links = Array.from(document.querySelectorAll('a[href*="/posts/"], a[href*="permalink"]'));
                const match = links.find(a => a.href.includes(targetUrl) || targetUrl.includes(a.href.split('?')[0]));
                if (match) {
                    const container = match.closest('div[role="feed"] > div') || match.parentElement;
                    const timeEl = container ? container.querySelector('span[aria-label], abbr, [id*="stamp"]') : null;
                    if (timeEl) {
                        return timeEl.getAttribute('aria-label') || timeEl.textContent || null;
                    }
                    return match.textContent || null;
                }
                return null;
            }
        """, post_url)
        return time_text
    except Exception:
        return None


def parse_creation_time(node):
    timestamp = find_timestamp_in_dict(node)
    if timestamp:
        try:
            dt = datetime.fromtimestamp(timestamp)
            return {"timestamp": timestamp, "formatted": dt.strftime("%Y-%m-%d %H:%M:%S")}
        except (ValueError, TypeError, OverflowError):
            pass
    return {"timestamp": None, "formatted": None}


def normalize_price_amount(raw_str):
    cleaned = re.sub(r'[,\s\.]', '', raw_str)
    try: return int(cleaned)
    except ValueError: return None


def normalize_phone_number(raw_phone):
    if not raw_phone: return ""
    raw_stripped = raw_phone.strip()
    has_plus = raw_stripped.startswith('+')
    digits = re.sub(r'\D', '', raw_stripped)
    
    if not digits: return raw_stripped
        
    if digits.startswith('374') and len(digits) == 11:
        d = digits[3:]
        return f"+374 {d[:2]} {d[2:5]} {d[5:]}"
    elif digits.startswith('0') and len(digits) == 9:
        d = digits[1:]
        return f"+374 {d[:2]} {d[2:5]} {d[5:]}"
    elif len(digits) == 8:
        return f"+374 {digits[:2]} {digits[2:5]} {digits[5:]}"

    if has_plus or len(digits) > 10:
        if digits.startswith(('1', '7')) and len(digits) == 11:
            cc = digits[0]
            rest = digits[1:]
            if cc == '1':
                return f"+1 ({rest[:3]}) {rest[3:6]}-{rest[6:]}"
            return f"+{cc} {rest[:3]} {rest[3:6]}-{rest[6:]}"
            
        for cc_len in [3, 2, 1]:
            if len(digits) > cc_len + 6:
                cc = digits[:cc_len]
                rest = digits[cc_len:]
                chunks = []
                while rest:
                    chunk_size = 3 if len(rest) > 4 else 2
                    chunks.append(rest[:chunk_size])
                    rest = rest[chunk_size:]
                return f"+{cc} " + " ".join(chunks)

    return f"+{digits}" if has_plus else raw_stripped


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


def extract_property_category(text, is_media_only=False):
    if not text:
        return "Media-Only" if is_media_only else "General / Unclassified"
    text_lower = text.lower()
    if any(w in text_lower for w in ["հող", "հողատարածք", "հողամաս", "tnamerd", "hox", "land", "plot", "տանամերձ", "участок", "земля", "земли"]):
        return "Land"
    if any(w in text_lower for w in ["առանձնատուն", "տուն", "arandznatun", "tun", "house", "villa", "ամառանոց", "дом", "дача", "коттедж", "особняк"]):
        return "House"
    if any(w in text_lower for w in ["բնակարան", "nakaran", "apartment", "flat", "ստուդիո", "studio", "квартира", "квартиру", "студия"]):
        return "Apartment"
    return "Media-Only" if is_media_only else "General / Unclassified"


def extract_negotiation_status(text):
    if not text:
        return "Unknown"
    text_lower = text.lower()
    if any(w in text_lower for w in ["սակարկելի չէ", "սակարկման ենթակա չէ", "վերջնական գին", "not negotiable", "без торга", "торга нет"]):
        return False
    if any(w in text_lower for w in ["սակարկելի", "negotiable", "սակարկման ենթակա", "торг", "торгуемо"]):
        return True
    return "Unknown"


def extract_housing_details(text, is_media_only=False):
    has_text = bool(text and text.strip())
    if not has_text:
        return {
            "has_text": False,
            "is_media_only": is_media_only,
            "property_category": "Media-Only" if is_media_only else "General / Unclassified",
            "listing_type": "Unknown",
            "is_negotiable": "Unknown",
            "floor_info": None,
            "prices": [],
            "locations": [],
            "phone_numbers": [],
            "sizes_sqm": [],
            "rooms": []
        }

    sanitized_text = text
    text_lower = text.lower()

    property_category = extract_property_category(text, is_media_only=is_media_only)

    listing_type = "Unknown"
    if any(w in text_lower for w in ["վարձով", "օրավարձով", "vardsov", "rent", "vardzov", "аренду", "сдам", "сдается", "аренда", "посуточно"]):
        listing_type = "Sale" if any(w in text_lower for w in ["վաճառք", "վաճառվում", "продажа", "продается"]) else "Rent"
    elif any(w in text_lower for w in ["վաճառվում է", "vacharvum e", "sale", "nakavachark", "վաճառք", "продается", "продам", "продажа"]):
        listing_type = "Sale"

    is_negotiable = extract_negotiation_status(text)

    floor_info = None
    floor_match = FLOOR_PATTERN.search(text)
    if floor_match:
        floor_info = {
            "floor": int(floor_match.group("floor")),
            "total_floors": int(floor_match.group("total_floors"))
        }

    phone_matches = list(PHONE_NUMBER_PATTERN.finditer(sanitized_text))
    found_phones = []
    for match in reversed(phone_matches):
        raw_phone = match.group(0)
        found_phones.append(normalize_phone_number(raw_phone))
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [PHONE_REMOVED] " + sanitized_text[end:]
    found_phones.reverse()

    size_matches = list(SIZE_PATTERN.finditer(sanitized_text))
    found_sizes = []
    for match in reversed(size_matches):
        size_str = match.group('size1') or match.group('size2')
        size_val = size_str.replace(',', '.')
        size_num = float(size_val)
        if size_num.is_integer(): size_num = int(size_num)
        found_sizes.append(size_num)
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [SIZE_REMOVED] " + sanitized_text[end:]
    found_sizes.reverse()

    room_matches = list(ROOM_PATTERN.finditer(sanitized_text))
    found_rooms = []
    for match in reversed(room_matches):
        try: 
            rooms_str = match.group('rooms1') or match.group('rooms2')
            found_rooms.append(int(rooms_str))
        except ValueError: pass
        start, end = match.span()
        sanitized_text = sanitized_text[:start] + " [ROOM_REMOVED] " + sanitized_text[end:]
    found_rooms.reverse()

    sanitized_text = TREE_COUNT_PATTERN.sub(" [TREE_COUNT_REMOVED] ", sanitized_text)
    sanitized_text = DIMENSION_PATTERN.sub(" [DIMENSION_REMOVED] ", sanitized_text)
    sanitized_text = COUNT_ITEM_PATTERN.sub(" [COUNT_REMOVED] ", sanitized_text)
    sanitized_text = PROPERTY_CODE_PATTERN.sub(" [CODE_REMOVED] ", sanitized_text)
    sanitized_text = PERCENT_PATTERN.sub(" [PERCENT_REMOVED] ", sanitized_text)

    parsed_prices = []
    for match in PRICE_CURRENCY_PATTERN.finditer(sanitized_text):
        amount_raw = match.group('amount')
        pre_curr = match.group('pre_curr')
        post_curr = match.group('post_curr')
        amount = normalize_price_amount(amount_raw)
        
        if not amount:
            continue
            
        if 2020 <= amount <= 2030 and not pre_curr and not post_curr:
            parsed_prices.append({"amount": amount, "currency": "Possible Year / Unspecified", "raw_text": match.group(0).strip()})
            continue
            
        symbol = (pre_curr or post_curr or '').strip().lower()
        symbol_clean = re.sub(r'\s+', ' ', symbol)
        currency = CURRENCY_MAP.get(symbol_clean)
        
        if not currency:
            if amount >= 10000:
                currency = 'AMD' if amount >= 50000 else 'USD'
            else:
                currency = 'Unspecified Currency'
                
        parsed_prices.append({"amount": amount, "currency": currency, "raw_text": match.group(0).strip()})

    found_locations = set()
    for canonical_name, aliases in LOCATION_DICTIONARY.items():
        for alias in aliases:
            if alias in text_lower:
                found_locations.add(canonical_name)
                break

    return {
        "has_text": True,
        "is_media_only": is_media_only,
        "property_category": property_category,
        "listing_type": listing_type,
        "is_negotiable": is_negotiable,
        "floor_info": floor_info,
        "prices": parsed_prices,
        "locations": list(found_locations),
        "phone_numbers": list(dict.fromkeys(found_phones)),
        "sizes_sqm": list(dict.fromkeys(found_sizes)),
        "rooms": list(dict.fromkeys(found_rooms))
    }


def normalize_url(url):
    if not url: return ""
    if url.startswith("/"): url = "https://www.facebook.com" + url
    clean_url = url.split("?")[0].split("&")[0].rstrip("/")
    clean_url = clean_url.replace("/permalink/", "/posts/")
    return clean_url


def extract_post_id(url):
    match = re.search(r'/(?:posts|permalink)/(\d+)', url)
    return match.group(1) if match else url


def score_post_data(post):
    score = 0
    if post.get("created_at"): score += 10
    if post.get("creation_timestamp"): score += 10
    score += len(post.get("prices", [])) * 5
    score += len(post.get("sizes_sqm", [])) * 5
    score += len(post.get("rooms", [])) * 5
    score += len(post.get("locations", [])) * 5
    score += len(post.get("phone_numbers", [])) * 5
    if post.get("property_category") in ["Apartment", "House", "Land"]:
        score += 15
    score += len(post.get("full_text", "")) / 100 
    return score


def get_group_file_path(group_id):
    return os.path.join(OUTPUT_DIR, f"extracted_housing_posts_{group_id}.json")


def load_dataset_for_group(group_id):
    file_path = get_group_file_path(group_id)
    if not os.path.exists(file_path):
        return [], set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        posts_by_id = {}
        for post in data:
            post["url"] = normalize_url(post.get("url", ""))
            post_id = extract_post_id(post["url"])
            if post_id not in posts_by_id:
                posts_by_id[post_id] = []
            posts_by_id[post_id].append(post)

        unique_by_id = []
        for post_id, post_group in posts_by_id.items():
            post_group.sort(key=score_post_data, reverse=True)
            unique_by_id.append(post_group[0])

        urls = set(item["url"] for item in unique_by_id)
        return unique_by_id, urls
    except Exception:
        return [], set()


def update_group_metadata(group_id, group_name, session_posts, session_duration_sec):
    meta_path = get_group_metadata_file_path(group_id)
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    metadata = loaded
        except Exception:
            pass

    metadata["name"] = group_name
    metadata.pop("categories", None)
    metadata.pop("listing_types", None)
    
    if "summary_title" not in metadata:
        metadata["summary_title"] = f"Group {group_id}"
    if "primary_focus" not in metadata:
        metadata["primary_focus"] = {"listing_type": "Unknown", "property_category": "General", "percentage": 0.0}
    if "avg_scroll_time_1_day_sec" not in metadata:
        metadata["avg_scroll_time_1_day_sec"] = 180.0

    distributions = metadata.get("distributions", {})

    for post in session_posts:
        cat = post.get("property_category", "General / Unclassified")
        l_type = post.get("listing_type", "Unknown")
        combo_key = f"{l_type} - {cat}"
        distributions[combo_key] = distributions.get(combo_key, 0) + 1

    metadata["distributions"] = distributions

    total_posts_counted = sum(distributions.values())
    if total_posts_counted > 0:
        sorted_combos = sorted(distributions.items(), key=lambda x: x[1], reverse=True)
        top_combo_name, top_count = sorted_combos[0]
        
        for combo_name, count in sorted_combos:
            if "General / Unclassified" not in combo_name and "Media-Only" not in combo_name and "Unknown" not in combo_name:
                top_combo_name = combo_name
                top_count = count
                break

        pct = round((top_count / total_posts_counted) * 100, 1)
        
        parts = top_combo_name.split(" - ")
        raw_l_type = parts[0] if len(parts) > 0 else "Unknown"
        raw_cat = parts[1] if len(parts) > 1 else "General"
        
        l_type_val = LISTING_TRANSLATION_MAP.get(raw_l_type, raw_l_type)
        cat_val = CATEGORY_TRANSLATION_MAP.get(raw_cat, raw_cat)

        metadata["primary_focus"] = {
            "listing_type": l_type_val,
            "property_category": cat_val,
            "percentage": pct
        }
        
        if l_type_val != "General" and cat_val != "General" and cat_val != "Media-Only":
            metadata["summary_title"] = f"{cat_val}s for {l_type_val}" if not cat_val.endswith("s") else f"{cat_val} for {l_type_val}"
        else:
            metadata["summary_title"] = f"Group {group_id} Activity"

    today_str = datetime.now().strftime("%Y-%m-%d")
    benchmarks = metadata.get("scroll_benchmarks", {})
    
    now_ts = datetime.now().timestamp()
    valid_ages_hours = []
    for p in session_posts:
        ts = p.get("creation_timestamp")
        if ts and ts <= now_ts:
            age_hrs = (now_ts - ts) / 3600.0
            if 0 <= age_hrs <= 720:
                valid_ages_hours.append(age_hrs)

    if valid_ages_hours:
        valid_ages_hours.sort(reverse=True)
        idx = int(len(valid_ages_hours) * 0.10) if len(valid_ages_hours) >= 10 else 0
        effective_oldest_age = valid_ages_hours[idx]

        benchmarks[today_str] = {
            "scroll_duration_seconds": session_duration_sec,
            "oldest_post_age_hours": round(effective_oldest_age, 2),
            "posts_scanned": len(session_posts)
        }

    if len(benchmarks) > 3:
        sorted_dates = sorted(benchmarks.keys())
        while len(sorted_dates) > 3:
            oldest_key = sorted_dates.pop(0)
            benchmarks.pop(oldest_key, None)

    metadata["scroll_benchmarks"] = benchmarks

    calculated_1_day_times = []
    for b in benchmarks.values():
        duration = b.get("scroll_duration_seconds", 0)
        age_hrs = b.get("oldest_post_age_hours", 0)
        if age_hrs > 0:
            one_day_normalized = (duration / age_hrs) * 24
            calculated_1_day_times.append(one_day_normalized)

    if calculated_1_day_times:
        metadata["avg_scroll_time_1_day_sec"] = round(sum(calculated_1_day_times) / len(calculated_1_day_times), 1)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)


def save_post_to_memory_and_disk(group_id, all_posts, processed_urls, post_record):
    norm_url = normalize_url(post_record["url"])
    post_record["url"] = norm_url
    
    existing_idx = None
    for i, p in enumerate(all_posts):
        if p["url"] == norm_url:
            existing_idx = i
            break
    
    file_path = get_group_file_path(group_id)
    if existing_idx is None:
        processed_urls.add(norm_url)
        all_posts.append(post_record)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=4)
        return "new"
    else:
        if score_post_data(post_record) > score_post_data(all_posts[existing_idx]):
            all_posts[existing_idx] = post_record
            processed_urls.add(norm_url)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(all_posts, f, ensure_ascii=False, indent=4)
            return "updated"
    return None


def extract_posts_from_graphql_payload(obj, group_id):
    if isinstance(obj, dict):
        if "comet_sections" in obj or "message" in obj:
            try:
                story = obj.get("comet_sections", {}).get("content", {}).get("story", {}) or obj
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

                post_id = story.get("post_id") or story.get("id")
                url = story.get("url")

                if not url and post_id:
                    real_id = decode_facebook_id(post_id)
                    url = f"https://www.facebook.com/groups/{group_id}/posts/{real_id}"

                time_data = parse_creation_time(obj)
                actors = story.get("actors", [])
                author_name = actors[0].get("name") if actors and isinstance(actors[0], dict) else None

                if url:
                    clean_url = normalize_url(url)
                    yield {
                        "url": clean_url,
                        "text": combined_text,
                        "is_media_only": is_media_only,
                        "creation_timestamp": time_data["timestamp"],
                        "created_at": time_data["formatted"],
                        "author": author_name,
                        "raw_node": obj
                    }
            except Exception:
                pass

        for value in obj.values():
            yield from extract_posts_from_graphql_payload(value, group_id)

    elif isinstance(obj, list):
        for item in obj:
            yield from extract_posts_from_graphql_payload(item, group_id)


def move_mouse_bezier(page, start_x, start_y, end_x, end_y, steps=25):
    control_x = (start_x + end_x) / 2 + random.randint(-80, 80)
    control_y = (start_y + end_y) / 2 + random.randint(-80, 80)
    for i in range(1, steps + 1):
        t = i / steps
        t_eased = t * t * (3 - 2 * t)
        x = (1 - t_eased)**2 * start_x + 2 * (1 - t_eased) * t_eased * control_x + t_eased**2 * end_x
        y = (1 - t_eased)**2 * start_y + 2 * (1 - t_eased) * t_eased * control_y + t_eased**2 * end_y
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.01, 0.025))


def try_click_see_more(page, viewport, mouse_pos):
    try:
        rects = page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('div[role="button"]'))
                    .filter(b => b.textContent.trim() === 'See more' && b.offsetWidth > 0 && b.offsetHeight > 0);
                return btns.map(b => {
                    const r = b.getBoundingClientRect();
                    return { x: r.x, y: r.y, width: r.width, height: r.height };
                }).filter(r => r.y >= 0 && r.y <= (window.innerHeight - r.height) && r.x >= 0 && r.x <= (window.innerWidth - r.width));
            }
        """)

        if rects:
            box = random.choice(rects[:3])
            target_x = box["x"] + (box["width"] * random.uniform(0.2, 0.8))
            target_y = box["y"] + (box["height"] * random.uniform(0.2, 0.8))
            move_mouse_bezier(page, mouse_pos["x"], mouse_pos["y"], target_x, target_y, steps=random.randint(20, 30))
            mouse_pos["x"], mouse_pos["y"] = target_x, target_y
            time.sleep(random.uniform(0.2, 0.5))
            page.mouse.click(target_x, target_y)
            return True
    except Exception:
        pass
    return False


def smooth_scroll(page, direction="down"):
    distance = random.randint(500, 900) if direction == "down" else -random.randint(300, 500)
    steps = random.randint(10, 15)
    step_delay = random.randint(12, 20)

    page.evaluate(f"""async () => {{
        const distance = {distance};
        const steps = {steps};
        const stepDistance = distance / steps;
        for (let i = 0; i < steps; i++) {{
            window.scrollBy({{ top: stepDistance, behavior: 'instant' }});
            await new Promise(resolve => setTimeout(resolve, {step_delay}));
        }}
    }}""")


def perform_human_action_chain(page, mouse_pos):
    if CURRENT_OS == "windows":
        action_type = random.choices(["scroll_down", "scroll_up"], weights=[0.90, 0.10], k=1)[0]
    else:
        action_type = random.choices(["scroll_down", "scroll_up", "see_more"], weights=[0.80, 0.05, 0.15], k=1)[0]
    
    if action_type == "scroll_down":
        smooth_scroll(page, direction="down")
    elif action_type == "scroll_up":
        smooth_scroll(page, direction="up")
    elif action_type == "see_more":
        viewport = page.viewport_size or {"width": 1366, "height": 768}
        try_click_see_more(page, viewport, mouse_pos)
        
    time.sleep(random.uniform(1.5, 3.5))


def check_global_break(global_timer_state, page, mouse_pos):
    now = time.time()
    if now >= global_timer_state["next_break_due"]:
        pause_duration = random.randint(30, 180)
        print(f"\n☕ [Global Break] Taking a natural human break for {format_elapsed_time(pause_duration)}...")
        
        break_end = time.time() + pause_duration
        viewport = page.viewport_size or {"width": 1366, "height": 768}
        
        while time.time() < break_end:
            if CURRENT_OS != "windows" and random.random() < 0.15: 
                target_x = random.randint(200, viewport["width"] - 200)
                target_y = random.randint(200, viewport["height"] - 200)
                move_mouse_bezier(page, mouse_pos["x"], mouse_pos["y"], target_x, target_y, steps=random.randint(15, 25))
                mouse_pos["x"], mouse_pos["y"] = target_x, target_y
            time.sleep(random.uniform(8.0, 20.0))
            
        global_timer_state["next_break_due"] = time.time() + random.randint(480, 720)
        print(f"▶️ [Global Break] Resuming scraping workflow.")


def manage_tabs_and_cleanup(browser_context, open_tabs, current_page, mouse_pos):
    if CURRENT_OS != "windows" and len(open_tabs) > 2 and random.random() < 0.3:
        candidates = [t for t in open_tabs if t != current_page and not t.is_closed()]
        if candidates:
            tab_to_close = random.choice(candidates)
            print(f"🧹 [Tab Manager] Closing an old background tab...")
            
            viewport = current_page.viewport_size or {"width": 1366, "height": 768}
            top_target_x = random.randint(100, viewport["width"] - 100)
            top_target_y = random.randint(2, 12)
            move_mouse_bezier(current_page, mouse_pos["x"], mouse_pos["y"], top_target_x, top_target_y, steps=random.randint(15, 22))
            mouse_pos["x"], mouse_pos["y"] = top_target_x, top_target_y
            time.sleep(random.uniform(0.5, 1.0))
            
            try:
                tab_to_close.close()
                open_tabs.remove(tab_to_close)
                print(f"✅ [Tab Manager] Background tab successfully closed.")
            except Exception:
                pass


def run_facebook_housing_scraper():
    target_groups = load_target_groups()
    if not target_groups:
        print("❌ No target groups found in groups_config.json.")
        return

    # --- Robust Argument Parsing (supports positional style AND flag style) ---
    parser = argparse.ArgumentParser(description="Facebook Housing Posts Scraper")
    parser.add_argument("positional_time", nargs="?", type=float, default=None, help="Time limit in minutes per group (positional)")
    parser.add_argument("-t", "--time-limit", type=float, default=None, help="Time limit in minutes per group (flag)")
    
    parsed_args, unknown = parser.parse_known_args()
    cli_runtime_min = parsed_args.time_limit if parsed_args.time_limit is not None else parsed_args.positional_time

    cli_runtime_sec = None
    if cli_runtime_min is not None:
        try:
            cli_runtime_sec = float(cli_runtime_min) * 60.0
            print(f"⏱️ CLI Override active: Forcing runtime to {cli_runtime_min} minutes per group.")
        except ValueError:
            print("⚠️ Invalid argument for runtime provided. Falling back to dynamic metadata calculation.")

    mouse_pos = {"x": 680, "y": 400}
    
    global_timer_state = {
        "next_break_due": time.time() + random.randint(480, 720)
    }

    with sync_playwright() as p:
        context_args = {
            "user_data_dir": USER_DATA_DIR,
            "headless": False,
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
        else:
            context_args["args"] = [
                "--disable-blink-features=AutomationControlled"
            ]

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
                                    save_post_to_memory_and_disk(target_group_id, group_posts_cache, group_urls_cache, record)
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    pass

        browser_context.on("response", handle_response)

        for idx, group in enumerate(target_groups):
            group_id = str(group["id"])
            group_name = group["name"]
            group_url = f"https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL"
            
            group_posts_cache, group_urls_cache = load_dataset_for_group(group_id)

            if cli_runtime_sec is not None:
                calculated_runtime = cli_runtime_sec
                target_days = 3
            else:
                calculated_runtime, target_days = calculate_dynamic_runtime(group_id)

            print(f"\n==============================================")
            print(f"🎯 Group: {group_name} ({group_id})")
            print(f"📁 Posts File: {OUTPUT_DIR}/extracted_housing_posts_{group_id}.json")
            print(f"📁 Metadata File: {METADATA_DIR}/groups_metadata_{group_id}.json")
            print(f"🧠 Strategy: ~{target_days}-day window | Allotted Time: {format_elapsed_time(calculated_runtime)}")
            print(f"==============================================")

            current_session_posts.clear()
            current_active_group_id["id"] = group_id

            if idx == 0 and initial_blank_page and not initial_blank_page.is_closed() and initial_blank_page.url == "about:blank":
                page = initial_blank_page
                open_tabs = [page]
            else:
                page = browser_context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
                open_tabs = list(browser_context.pages)
                manage_tabs_and_cleanup(browser_context, open_tabs, page, mouse_pos)

            session_start_time = time.time()
            group_end_time = session_start_time + calculated_runtime

            print(f"Navigating to {group_url}...")
            page.goto(group_url)
            time.sleep(random.uniform(4.0, 6.0))

            while time.time() < group_end_time:
                check_global_break(global_timer_state, page, mouse_pos)
                perform_human_action_chain(page, mouse_pos)
                
                if current_session_posts:
                    now_ts = datetime.now().timestamp()
                    valid_ages_days = []
                    for p in current_session_posts:
                        ts = p.get("creation_timestamp")
                        if ts and ts <= now_ts:
                            age_d = (now_ts - ts) / (3600.0 * 24.0)
                            if 0 <= age_d <= 365:
                                valid_ages_days.append(age_d)
                    
                    if len(valid_ages_days) >= 15:
                        valid_ages_days.sort(reverse=True)
                        check_idx = int(len(valid_ages_days) * 0.05)
                        robust_oldest_age = valid_ages_days[check_idx]
                        if robust_oldest_age >= 30.0:
                            print(f"🛑 Reached consistent posts older than 30 days ({round(robust_oldest_age, 1)} days old at threshold). Stopping scan early for this group.")
                            break

                elapsed_sec = time.time() - session_start_time
                elapsed_formatted = format_elapsed_time(elapsed_sec)
                print(f"⏳ [{group_name}] Elapsed: {elapsed_formatted} / {format_elapsed_time(calculated_runtime)} | Captured: {len(current_session_posts)}")

            session_duration = time.time() - session_start_time
            update_group_metadata(group_id, group_name, current_session_posts, session_duration)
            update_group_config_status(group_id, len(current_session_posts))
            print(f"📊 Updated isolated metadata and analytics for: {group_name}")

        browser_context.close()
        print(f"\nAll groups scanned. Posts and metadata cleanly isolated into '{OUTPUT_DIR}/' and '{METADATA_DIR}/' folders.")

if __name__ == "__main__":
    run_facebook_housing_scraper()