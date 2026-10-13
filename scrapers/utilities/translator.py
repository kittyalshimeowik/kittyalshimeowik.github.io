"""
Automated translation and caching module for Armenia Real Estate Hub.
Translates Armenian and Russian property descriptions into English for bilingual support.
Maintains a persistent disk cache to avoid redundant API requests.
"""

import hashlib
import json
import os
import re
import sys
import time
import random
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.env_utils import ensure_utf8_output
ensure_utf8_output()

DATA_DIR = os.path.join(PROJECT_ROOT, "scrapers", "data")
DEFAULT_CACHE_PATH = os.path.join(DATA_DIR, "translations_cache.json")

# Delimiter used when grouping multiple texts into a single translation request
BATCH_DELIMITER = "\n===__DELIM__===\n"

# Regex patterns to detect Armenian and Cyrillic scripts
ARMENIAN_REGEX = re.compile(r'[\u0530-\u058F]')
CYRILLIC_REGEX = re.compile(r'[\u0400-\u04FF]')


def text_hash(text: str) -> str:
    """Computes a normalized MD5 hash for a text string."""
    norm = (text or "").strip()
    return hashlib.md5(norm.encode("utf-8")).hexdigest()


def is_already_english(text: str) -> bool:
    """Checks if text is primarily English/Latin without Armenian or Cyrillic."""
    if not text or not text.strip():
        return True
    # If text has Armenian or Russian characters, it is not purely English
    if ARMENIAN_REGEX.search(text) or CYRILLIC_REGEX.search(text):
        return False
    # Check latin alpha ratio
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    ascii_letters = [c for c in letters if c.isascii()]
    return (len(ascii_letters) / len(letters)) >= 0.85


class TranslationCache:
    """Thread-safe persistent JSON cache for translated texts."""

    def __init__(self, cache_path: Optional[str] = None):
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
        self._cache: Dict[str, str] = {}
        self._dirty = False
        self.load()

    def load(self):
        """Loads cached translations from disk."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                print(f"[WARNING] Could not load translation cache: {e}", file=sys.stderr)
                self._cache = {}
        else:
            self._cache = {}
        self._dirty = False

    def save(self):
        """Saves cached translations to disk if modified."""
        if not self._dirty:
            return
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
            self._dirty = False
        except Exception as e:
            print(f"[WARNING] Could not save translation cache: {e}", file=sys.stderr)

    def get(self, text: str) -> Optional[str]:
        """Gets translated text by content hash if present."""
        if not text:
            return ""
        return self._cache.get(text_hash(text))

    def set(self, text: str, translated: str):
        """Stores translated text by content hash."""
        if not text:
            return
        h = text_hash(text)
        if self._cache.get(h) != translated:
            self._cache[h] = translated
            self._dirty = True

    def __len__(self):
        return len(self._cache)

    def __bool__(self):
        return True


_LAST_RATE_LIMIT_TIMESTAMP = 0.0


def _check_rate_limit_cooldown(min_cooldown: float = 3.5):
    """Enforces a global cooling-off pause if a rate limit was recently triggered."""
    global _LAST_RATE_LIMIT_TIMESTAMP
    elapsed = time.time() - _LAST_RATE_LIMIT_TIMESTAMP
    if elapsed < min_cooldown:
        time.sleep(min_cooldown - elapsed)


def _request_google_translate(query_text: str, target_lang: str = "en", max_retries: int = 3) -> Optional[str]:
    """Sends a single translation request to the Google Translate web endpoint via POST with adaptive backoff."""
    if not query_text or not query_text.strip():
        return ""

    _check_rate_limit_cooldown()

    url = "https://translate.googleapis.com/translate_a/single"
    post_data = urllib.parse.urlencode({
        "client": "gtx",
        "sl": "auto",
        "tl": target_lang,
        "dt": "t",
        "q": query_text
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=post_data,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data and isinstance(data, list) and isinstance(data[0], list):
                    translated_parts = [part[0] for part in data[0] if part and part[0]]
                    return "".join(translated_parts)
                return None
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                global _LAST_RATE_LIMIT_TIMESTAMP
                _LAST_RATE_LIMIT_TIMESTAMP = time.time()
                backoff_sec = (2.0 ** attempt) * 4.0 + random.uniform(1.0, 3.0)
                print(f"⚠️ [Google Translate Rate Limit (HTTP {e.code})] Backing off for {backoff_sec:.1f}s (retry {attempt + 1}/{max_retries})...", file=sys.stderr)
                time.sleep(backoff_sec)
            else:
                return None
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1.5)
            else:
                return None

    return None


def translate_single_text(text: str, target_lang: str = "en", cache: Optional[TranslationCache] = None) -> str:
    """Translates a single text into the target language with cache lookup."""
    norm = (text or "").strip()
    if not norm:
        return ""

    if is_already_english(norm):
        return norm

    if cache is not None:
        cached = cache.get(norm)
        if cached:
            return cached

    # Attempt translation via API
    result = _request_google_translate(norm, target_lang=target_lang)
    if result and result.strip():
        cleaned = result.strip()
        if cache is not None:
            cache.set(norm, cleaned)
        return cleaned

    # Fallback to original text if translation failed
    return norm


def batch_translate_texts(
    texts: List[str],
    target_lang: str = "en",
    batch_size: int = 5,
    cache: Optional[TranslationCache] = None,
    progress_callback: Optional[callable] = None
) -> List[str]:
    """
    Translates a list of texts into the target language efficiently.
    Uses persistent cache for instant lookups and batches uncached texts.
    """
    if not texts:
        return []

    local_cache = cache if cache is not None else TranslationCache()
    results = [None] * len(texts)
    uncached_indices = []

    # First pass: resolve from English detection or cache
    for idx, text in enumerate(texts):
        norm = (text or "").strip()
        if not norm:
            results[idx] = ""
        elif is_already_english(norm):
            results[idx] = norm
        else:
            cached = local_cache.get(norm)
            if cached:
                results[idx] = cached
            else:
                uncached_indices.append(idx)

    # If all items were cached or already English, we're done
    if not uncached_indices:
        return results

    total_uncached = len(uncached_indices)
    processed = 0

    # Process uncached in small batches to reduce HTTP requests
    for i in range(0, total_uncached, batch_size):
        chunk_indices = uncached_indices[i:i + batch_size]
        chunk_texts = [texts[idx].strip()[:450] for idx in chunk_indices]

        # Translate multiple descriptions as a single batch
        if len(chunk_texts) > 1:
            joined = BATCH_DELIMITER.join(chunk_texts)
            translated_joined = _request_google_translate(joined, target_lang=target_lang)

            if translated_joined:
                parts = re.split(r'\s*===.*?===\s*', translated_joined)
                if len(parts) == len(chunk_texts):
                    for idx, part, orig in zip(chunk_indices, parts, chunk_texts):
                        clean_part = part.strip().lstrip(":").strip()
                        results[idx] = clean_part
                        local_cache.set(orig, clean_part)
                    processed += len(chunk_indices)
                    if progress_callback:
                        progress_callback(processed, total_uncached)
                    if processed % 50 == 0:
                        local_cache.save()
                    time.sleep(random.uniform(0.4, 0.7))  # Polite pause between batch requests
                    continue

        # If batching didn't succeed or chunk is large, pause briefly and translate individually
        time.sleep(random.uniform(1.2, 2.5))
        for idx in chunk_indices:
            orig = texts[idx].strip()
            translated = _request_google_translate(orig, target_lang=target_lang)
            final_text = translated.strip() if translated else orig
            results[idx] = final_text
            if translated:
                local_cache.set(orig, final_text)
            processed += 1
            if progress_callback:
                progress_callback(processed, total_uncached)
            time.sleep(random.uniform(0.25, 0.45))

        if processed % 50 == 0:
            local_cache.save()

    local_cache.save()
    return results


def enrich_listings_with_translations(
    listings: List[dict],
    cache: Optional[TranslationCache] = None,
    batch_size: int = 5,
    show_progress: bool = True
) -> List[dict]:
    """
    Enriches a list of listing dictionaries with 'full_text_en' translations.
    Leaves existing or already-English listings untouched and caches all new translations.
    """
    if not listings:
        return listings

    translation_cache = cache or TranslationCache()

    # Identify listings that need translation
    to_translate_indices = []
    texts_to_translate = []

    for i, item in enumerate(listings):
        # If full_text_en already exists and is non-empty, keep it
        if item.get("full_text_en"):
            continue

        raw_text = (item.get("full_text") or "").strip()
        if not raw_text:
            item["full_text_en"] = ""
            continue

        if is_already_english(raw_text):
            item["full_text_en"] = raw_text
            continue

        cached = translation_cache.get(raw_text)
        if cached:
            item["full_text_en"] = cached
        else:
            to_translate_indices.append(i)
            texts_to_translate.append(raw_text)

    if texts_to_translate:
        if show_progress:
            print(f"[INFO] Translating {len(texts_to_translate)} new listings to English...")

        def _print_prog(curr, tot):
            if show_progress and tot > 0:
                pct = int(100 * curr / tot)
                sys.stdout.write(f"\r  |- Translation Progress: {curr}/{tot} ({pct}%)")
                sys.stdout.flush()

        translated_texts = batch_translate_texts(
            texts_to_translate,
            target_lang="en",
            batch_size=batch_size,
            cache=translation_cache,
            progress_callback=_print_prog if show_progress else None
        )

        if show_progress and texts_to_translate:
            sys.stdout.write("\n")

        for idx, trans_text in zip(to_translate_indices, translated_texts):
            listings[idx]["full_text_en"] = trans_text

    translation_cache.save()
    return listings
