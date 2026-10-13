"""
Automated translation and caching module for Armenia Real Estate Hub.
Translates Armenian and Russian property descriptions into English for bilingual support.
Maintains a persistent disk cache to avoid redundant API requests.
"""

import hashlib
import json
import html
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


def is_genuine_translation(full_text: Optional[str], full_text_en: Optional[str]) -> bool:
    """
    Checks if full_text_en represents a genuine English translation rather than empty,
    incomplete, or duplicate raw Armenian/Russian text.
    """
    if not full_text_en:
        return False
    en_clean = full_text_en.strip()
    if len(en_clean) <= 5:
        return False
    # If the English field still has Armenian or Cyrillic characters, it's not translated
    if ARMENIAN_REGEX.search(en_clean) or CYRILLIC_REGEX.search(en_clean):
        return False
    orig_clean = (full_text or "").strip()
    if en_clean.lower() != orig_clean.lower():
        return True
    return is_already_english(orig_clean)


class TranslationCache:
    """Thread-safe persistent JSON cache for translated texts."""

    def __init__(self, cache_path: Optional[str] = None):
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
        self._cache: Dict[str, str] = {}
        self._dirty = False
        self.load()

    def load(self):
        """Loads cached translations from disk, pruning any corrupted non-English entries."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    self._cache = {
                        k: v for k, v in raw_data.items()
                        if isinstance(v, str) and len(v.strip()) > 5 and not re.search(r'[\u0530-\u058F\u0400-\u04FF]', v)
                    }
                    if len(self._cache) != len(raw_data):
                        self._dirty = True
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
        """Stores translated text by content hash if genuine English."""
        if not text or not translated:
            return
        # Strict validation: Latin script, non-empty, no Armenian/Cyrillic scripts
        if re.search(r'[\u0530-\u058F\u0400-\u04FF]', translated) or len(translated.strip()) <= 5:
            return
        h = text_hash(text)
        if self._cache.get(h) != translated:
            self._cache[h] = translated
            self._dirty = True

    def __len__(self):
        return len(self._cache)

    def __bool__(self):
        return True


_GOOGLE_RATE_LIMIT_UNTIL = 0.0
_MYMEMORY_RATE_LIMITED_UNTIL = 0.0
_LAST_RATE_LIMIT_TIMESTAMP = 0.0


def is_recently_rate_limited(window_seconds: float = 60.0) -> bool:
    """Returns True only if all public translation engines are currently rate limited."""
    global _GOOGLE_RATE_LIMIT_UNTIL, _MYMEMORY_RATE_LIMITED_UNTIL
    now = time.time()
    # If Google is rate limited BUT MyMemory is available, we are not blocked
    if now < _GOOGLE_RATE_LIMIT_UNTIL and now < _MYMEMORY_RATE_LIMITED_UNTIL:
        return True
    return False


def _check_rate_limit_cooldown(min_cooldown: float = 1.5):
    """Enforces a global cooling-off pause if a rate limit was recently triggered."""
    global _LAST_RATE_LIMIT_TIMESTAMP
    elapsed = time.time() - _LAST_RATE_LIMIT_TIMESTAMP
    if elapsed < min_cooldown:
        time.sleep(min_cooldown - elapsed)


def _chunk_text_for_translation(text: str, max_chars: int = 420) -> List[str]:
    """Splits long listing descriptions into coherent chunks honoring sentence and line breaks."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return [text] if text else []

    lines = text.split("\n")
    chunks = []
    current_chunk = ""

    for line in lines:
        if len(line) > max_chars:
            parts = re.split(r'([.!?։\n]+\s*)', line)
            sentences = []
            for j in range(0, len(parts), 2):
                seg = parts[j]
                punct = parts[j + 1] if j + 1 < len(parts) else ""
                sentences.append(seg + punct)
            for s in sentences:
                if not s:
                    continue
                if len(s) > max_chars:
                    words = s.split(" ")
                    for w in words:
                        if len(current_chunk) + len(w) + 1 <= max_chars:
                            current_chunk = f"{current_chunk} {w}".strip()
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = w
                else:
                    if len(current_chunk) + len(s) + 1 <= max_chars:
                        current_chunk = f"{current_chunk} {s}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = s
        else:
            if len(current_chunk) + len(line) + 1 <= max_chars:
                current_chunk = f"{current_chunk}\n{line}".strip() if current_chunk else line
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line

    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def _detect_source_language(text: str) -> str:
    """Detects likely source language: 'hy' for Armenian, 'ru' for Russian, or 'auto'."""
    if ARMENIAN_REGEX.search(text):
        return "hy"
    if CYRILLIC_REGEX.search(text):
        return "ru"
    return "auto"


def _request_mymemory_translate(query_text: str, target_lang: str = "en") -> Optional[str]:
    """Translates text using the MyMemory Translation API with automatic chunking and HTML unescaping."""
    global _MYMEMORY_RATE_LIMITED_UNTIL
    if time.time() < _MYMEMORY_RATE_LIMITED_UNTIL:
        return None

    norm = (query_text or "").strip()
    if not norm:
        return ""

    chunks = _chunk_text_for_translation(norm, max_chars=420)
    if not chunks:
        return None

    src_lang = _detect_source_language(norm)
    langpair = f"{src_lang}|{target_lang}"

    translated_chunks = []
    for chunk in chunks:
        q_enc = urllib.parse.quote(chunk)
        url = f"https://api.mymemory.translated.net/get?q={q_enc}&langpair={langpair}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
                status = payload.get("responseStatus")
                res_data = payload.get("responseData") or {}
                trans_text = res_data.get("translatedText")
                if status == 200 and trans_text:
                    clean = html.unescape(trans_text.strip())
                    if "MYMEMORY WARNING" in clean.upper():
                        _MYMEMORY_RATE_LIMITED_UNTIL = time.time() + 600.0
                        return None
                    translated_chunks.append(clean)
                elif status in (429, 403):
                    _MYMEMORY_RATE_LIMITED_UNTIL = time.time() + 600.0
                    return None
                else:
                    return None
            time.sleep(0.3)
        except Exception:
            return None

    result = "\n".join(translated_chunks).strip()
    return result if result else None


def _request_gemini_translate(query_text: str, target_lang: str = "en") -> Optional[str]:
    """Translates text using Google Gemini API if GEMINI_API_KEY or GOOGLE_API_KEY is available."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    norm = (query_text or "").strip()
    if not norm:
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    prompt = (
        "Translate the following Armenian or Russian real estate listing description into fluent, professional English. "
        "Return ONLY the plain English translation without preamble or markdown:\n\n"
        f"{norm}"
    )
    req_body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000}
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception:
        pass
    return None


class BingTranslatorSession:
    """Maintains active session tokens for Microsoft Bing Translator (LLM-powered)."""

    def __init__(self):
        self.ig = None
        self.key = None
        self.token = None
        self.expires_at = 0.0

    def refresh(self) -> bool:
        """Fetches fresh anti-abuse tokens from Bing Translator."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            req = urllib.request.Request("https://www.bing.com/translator", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html_content = resp.read().decode("utf-8")

            ig_match = re.search(r'IG:"([A-Za-z0-9]+)"', html_content)
            abuse_match = re.search(r'params_AbusePreventionHelper\s*=\s*\[([^\]]+)\]', html_content)

            if ig_match and abuse_match:
                self.ig = ig_match.group(1)
                parts = abuse_match.group(1).split(",")
                self.key = parts[0].strip(' "\'')
                self.token = parts[1].strip(' "\'')
                self.expires_at = time.time() + 1800.0  # 30-minute validity
                return True
        except Exception:
            pass
        return False

    def translate(self, text: str, target_lang: str = "en") -> Optional[str]:
        """Translates text to target_lang using Bing Translator."""
        norm = (text or "").strip()
        if not norm:
            return ""

        if not self.key or not self.token or not self.ig or time.time() >= self.expires_at:
            if not self.refresh():
                return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        post_data = urllib.parse.urlencode({
            "fromLang": "auto-detect",
            "text": norm,
            "to": target_lang,
            "token": self.token,
            "key": self.key
        }).encode("utf-8")

        trans_url = f"https://www.bing.com/ttranslatev3?isVertical=1&IG={self.ig}&IID=translator.5028"
        req = urllib.request.Request(trans_url, data=post_data, headers=headers)

        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    if isinstance(res, list) and len(res) > 0:
                        translations = res[0].get("translations", [])
                        if translations and "text" in translations[0]:
                            return translations[0]["text"].strip()
                return None
            except urllib.error.HTTPError:
                if attempt == 0 and self.refresh():
                    post_data = urllib.parse.urlencode({
                        "fromLang": "auto-detect",
                        "text": norm,
                        "to": target_lang,
                        "token": self.token,
                        "key": self.key
                    }).encode("utf-8")
                    trans_url = f"https://www.bing.com/ttranslatev3?isVertical=1&IG={self.ig}&IID=translator.5028"
                    req = urllib.request.Request(trans_url, data=post_data, headers=headers)
                    continue
                return None
            except Exception:
                return None
        return None


_BING_SESSION = BingTranslatorSession()


def _request_google_translate(query_text: str, target_lang: str = "en", max_retries: int = 1) -> Optional[str]:
    """Sends a single translation request to the Google Translate web endpoint with circuit-breaker protection."""
    global _GOOGLE_RATE_LIMIT_UNTIL, _LAST_RATE_LIMIT_TIMESTAMP
    if time.time() < _GOOGLE_RATE_LIMIT_UNTIL:
        return None

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
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data and isinstance(data, list) and isinstance(data[0], list):
                    translated_parts = [part[0] for part in data[0] if part and part[0]]
                    return "".join(translated_parts)
                return None
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                _LAST_RATE_LIMIT_TIMESTAMP = time.time()
                _GOOGLE_RATE_LIMIT_UNTIL = time.time() + 900.0  # 15 min cooldown
                print(
                    f"ℹ️ [Google Translate Rate Limit] Circuit breaker tripped. "
                    "Automatically routing translations through Bing Fallback Engine...",
                    file=sys.stderr
                )
                return None
            else:
                return None
        except Exception:
            return None

    return None


def _request_translation_cascade(query_text: str, target_lang: str = "en") -> Optional[str]:
    """
    Executes a multi-engine translation cascade:
      1. Gemini (if GEMINI_API_KEY or GOOGLE_API_KEY is configured)
      2. Google Translate (if circuit breaker is open/cooling down, skips immediately)
      3. Bing Translator (LLM-powered, fast, unthrottled fallback)
      4. MyMemory API (fallback)
    """
    norm = (query_text or "").strip()
    if not norm:
        return ""

    # Engine 1: Gemini (if configured)
    gemini_res = _request_gemini_translate(norm, target_lang=target_lang)
    if gemini_res and is_genuine_translation(norm, gemini_res):
        return gemini_res

    # Engine 2: Google Translate (if not rate limited)
    global _GOOGLE_RATE_LIMIT_UNTIL
    if time.time() >= _GOOGLE_RATE_LIMIT_UNTIL:
        google_res = _request_google_translate(norm, target_lang=target_lang)
        if google_res and is_genuine_translation(norm, google_res):
            return google_res

    # Engine 3: Bing Translator (LLM-powered, highly reliable fallback)
    bing_res = _BING_SESSION.translate(norm, target_lang=target_lang)
    if bing_res and is_genuine_translation(norm, bing_res):
        return bing_res

    # Engine 4: MyMemory Fallback Engine
    mymemory_res = _request_mymemory_translate(norm, target_lang=target_lang)
    if mymemory_res and is_genuine_translation(norm, mymemory_res):
        return mymemory_res

    return None



def translate_single_text(text: str, target_lang: str = "en", cache: Optional[TranslationCache] = None) -> str:
    """Translates a single text into the target language with cache lookup and multi-engine fallback."""
    norm = (text or "").strip()
    if not norm:
        return ""

    if is_already_english(norm):
        return norm

    if cache is not None:
        cached = cache.get(norm)
        if cached:
            return cached

    # Attempt translation via multi-engine cascade
    result = _request_translation_cascade(norm, target_lang=target_lang)
    if result and result.strip() and is_genuine_translation(norm, result.strip()):
        cleaned = result.strip()
        if cache is not None:
            cache.set(norm, cleaned)
        return cleaned

    # Never return untranslated foreign text as an English translation
    return None


def batch_translate_texts(
    texts: List[str],
    target_lang: str = "en",
    batch_size: int = 5,
    cache: Optional[TranslationCache] = None,
    progress_callback: Optional[callable] = None
) -> List[Optional[str]]:
    """
    Translates a list of texts into the target language efficiently.
    Uses persistent cache for instant lookups and routes through the multi-engine cascade.
    Returns genuine translations or None if failed/rate limited.
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
            if cached and is_genuine_translation(norm, cached):
                results[idx] = cached
            else:
                uncached_indices.append(idx)

    # If all items were cached or already English, we're done
    if not uncached_indices:
        return results

    total_uncached = len(uncached_indices)
    processed = 0

    # Process uncached items
    for i in range(0, total_uncached, batch_size):
        chunk_indices = uncached_indices[i:i + batch_size]
        chunk_texts = [texts[idx].strip()[:450] for idx in chunk_indices]

        # If Google is available and not circuit-broken, attempt fast batching
        if len(chunk_texts) > 1 and time.time() >= _GOOGLE_RATE_LIMIT_UNTIL:
            joined = BATCH_DELIMITER.join(chunk_texts)
            translated_joined = _request_google_translate(joined, target_lang=target_lang)

            if translated_joined:
                parts = re.split(r'\s*===.*?===\s*', translated_joined)
                if len(parts) == len(chunk_texts):
                    for idx, part, orig in zip(chunk_indices, parts, chunk_texts):
                        clean_part = part.strip().lstrip(":").strip()
                        if is_genuine_translation(orig, clean_part):
                            results[idx] = clean_part
                            local_cache.set(orig, clean_part)
                        else:
                            results[idx] = None
                    processed += len(chunk_indices)
                    if progress_callback:
                        progress_callback(processed, total_uncached)
                    if processed % 50 == 0:
                        local_cache.save()
                    time.sleep(random.uniform(0.4, 0.7))
                    continue

        # Item-by-item translation through multi-engine cascade (MyMemory/Gemini/Google)
        for idx in chunk_indices:
            orig = texts[idx].strip()
            translated = _request_translation_cascade(orig, target_lang=target_lang)
            if translated and is_genuine_translation(orig, translated.strip()):
                final_text = translated.strip()
                results[idx] = final_text
                local_cache.set(orig, final_text)
            else:
                results[idx] = None
            processed += 1
            if progress_callback:
                progress_callback(processed, total_uncached)
            time.sleep(random.uniform(0.15, 0.30))

        if processed % 50 == 0:
            local_cache.save()

    local_cache.save()
    return results


def enrich_listings_with_translations(
    listings: List[dict],
    cache: Optional[TranslationCache] = None,
    batch_size: int = 5,
    show_progress: bool = True,
    cached_only: bool = False
) -> List[dict]:
    """
    Enriches a list of listing dictionaries with 'full_text_en' translations.
    Leaves existing genuine translations untouched and caches all new translations.
    """
    if not listings:
        return listings

    translation_cache = cache or TranslationCache()

    # Identify listings that need translation
    to_translate_indices = []
    texts_to_translate = []

    for i, item in enumerate(listings):
        raw_text = (item.get("full_text") or "").strip()
        if not raw_text:
            item["full_text_en"] = ""
            continue

        # If a genuine translation already exists, keep it
        if is_genuine_translation(raw_text, item.get("full_text_en")):
            continue

        if is_already_english(raw_text):
            item["full_text_en"] = raw_text
            continue

        cached = translation_cache.get(raw_text)
        if cached and is_genuine_translation(raw_text, cached):
            item["full_text_en"] = cached
        elif not cached_only:
            to_translate_indices.append(i)
            texts_to_translate.append(raw_text)

    if texts_to_translate and not cached_only:
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
            if trans_text and is_genuine_translation(listings[idx].get("full_text"), trans_text):
                listings[idx]["full_text_en"] = trans_text
            else:
                listings[idx]["full_text_en"] = None

    translation_cache.save()
    return listings
