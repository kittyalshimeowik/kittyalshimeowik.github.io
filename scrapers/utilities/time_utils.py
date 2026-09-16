# scrapers/facebook/time_utils.py

import re
from datetime import datetime, timedelta

RELATIVE_TIME_PATTERN = re.compile(r'(\d+)\s*(min|mins|minute|minutes|hr|hrs|hour|hours|d|day|days|ր|րոպե|ժամ|օր)', re.IGNORECASE)
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


def parse_creation_time(node):
    timestamp = find_timestamp_in_dict(node)
    if timestamp:
        try:
            dt = datetime.fromtimestamp(timestamp)
            return {"timestamp": timestamp, "formatted": dt.strftime("%Y-%m-%d %H:%M:%S")}
        except (ValueError, TypeError, OverflowError):
            pass
    return {"timestamp": None, "formatted": None}