# scrapers/utilities/storage.py
import os
import sys
import json
import sqlite3
import time
from datetime import datetime, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.translator import is_genuine_translation

DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, "scrapers", "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, "listings.db")


def compute_record_completeness(record):
    """Calculates a completeness score for a listing record."""
    score = 0.0
    if record.get("created_at"):
        score += 10.0
    if record.get("creation_timestamp"):
        score += 10.0
    score += len(record.get("prices") or []) * 5.0
    score += len(record.get("sizes_sqm") or []) * 5.0
    score += len(record.get("rooms") or []) * 5.0
    score += len(record.get("locations") or []) * 5.0
    score += len(record.get("phone_numbers") or []) * 5.0
    if record.get("images"):
        score += 10.0
    cat = record.get("property_category")
    if cat in ["Apartment", "House", "Land"]:
        score += 15.0
    score += min(len(record.get("full_text") or "") / 100.0, 10.0)
    return score


def detect_source_from_record(record):
    """Accurately classifies listing source from explicit field, URL, or platform registry."""
    source = record.get("source")
    if source and source not in ["Unknown", "unknown", "None", ""]:
        return source
    url = str(record.get("url") or "").lower()
    if "facebook.com" in url or "fb.com" in url:
        return "Facebook"
    if "list.am" in url:
        return "List.am"
    try:
        from scrapers.platforms.registry import get_platform_for_url
        plat = get_platform_for_url(record.get("url") or "")
        if plat:
            return plat.display_name
    except Exception:
        pass
    return source or "Unknown"


class ListingsStorage:
    """SQLite-backed transactional storage for raw real estate listings."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    canonical_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category_id TEXT,
                    property_category TEXT,
                    listing_type TEXT,
                    full_text TEXT,
                    full_text_en TEXT,
                    created_at TEXT,
                    creation_timestamp INTEGER,
                    extracted_at TEXT,
                    prices_json TEXT,
                    sizes_json TEXT,
                    rooms_json TEXT,
                    locations_json TEXT,
                    phones_json TEXT,
                    zoning_json TEXT,
                    images_json TEXT,
                    completeness_score REAL DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    first_seen_at TEXT,
                    last_seen_at TEXT,
                    photos_checked_at TEXT,
                    photo_status TEXT DEFAULT 'PENDING',
                    translation_status TEXT DEFAULT 'PENDING',
                    translations_checked_at TEXT
                );
            """)
            # Migration check: Ensure images_json, full_text_en, photos_checked_at, and status columns exist in tables
            cur = self.conn.cursor()
            cols = [col[1] for col in cur.execute("PRAGMA table_info(listings)").fetchall()]
            if "images_json" not in cols:
                cur.execute("ALTER TABLE listings ADD COLUMN images_json TEXT;")
            if "full_text_en" not in cols:
                cur.execute("ALTER TABLE listings ADD COLUMN full_text_en TEXT;")
            if "photos_checked_at" not in cols:
                cur.execute("ALTER TABLE listings ADD COLUMN photos_checked_at TEXT;")
            if "photo_status" not in cols:
                cur.execute("ALTER TABLE listings ADD COLUMN photo_status TEXT DEFAULT 'PENDING';")
            if "translation_status" not in cols:
                cur.execute("ALTER TABLE listings ADD COLUMN translation_status TEXT DEFAULT 'PENDING';")
            if "translations_checked_at" not in cols:
                cur.execute("ALTER TABLE listings ADD COLUMN translations_checked_at TEXT;")

            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_active_ts 
                ON listings(is_active, creation_timestamp);
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_source 
                ON listings(source);
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_cat_type 
                ON listings(property_category, listing_type);
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_photos_checked 
                ON listings(photos_checked_at);
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_photo_status 
                ON listings(photo_status);
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_trans_status 
                ON listings(translation_status);
            """)
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA synchronous = NORMAL;")
        
        # Self-healing: normalize any legacy or unclassified records and sanitize data
        self.normalize_unclassified_sources()
        self.sanitize_database_records()

    def normalize_unclassified_sources(self):
        """Normalizes and heals any unclassified or 'Unknown' sources using URL inspection."""
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute("""
                    UPDATE listings 
                    SET source = 'Facebook' 
                    WHERE (source IS NULL OR source = '' OR source = 'Unknown') 
                      AND (url LIKE '%facebook.com%' OR url LIKE '%fb.com%');
                """)
                cur.execute("""
                    UPDATE listings 
                    SET source = 'List.am' 
                    WHERE (source IS NULL OR source = '' OR source = 'Unknown') 
                      AND (url LIKE '%list.am%');
                """)
                return cur.rowcount
        except Exception:
            return 0

    def sanitize_database_records(self):
        """
        Sanitizes existing database records to maintain data hygiene:
        1. Nullifies non-genuine translations in full_text_en (untranslated Armenian/Russian text).
        2. Sets explicit translation_status: SUCCESS, NOT_NEEDED, RATE_LIMITED, ERROR, PENDING.
        3. Sets explicit photo_status: SUCCESS, NO_PHOTO, RATE_LIMITED, ERROR, PENDING.
        """
        try:
            from scrapers.utilities.translator import is_genuine_translation, is_already_english
            with self.conn:
                cur = self.conn.cursor()
                cur.execute("SELECT canonical_id, full_text, full_text_en, images_json, photos_checked_at, photo_status, translation_status FROM listings")
                rows = cur.fetchall()

                for r in rows:
                    cid = r["canonical_id"]
                    ft = r["full_text"] or ""
                    fte = r["full_text_en"]
                    img_j = r["images_json"]
                    p_chk = r["photos_checked_at"]
                    curr_p_stat = r["photo_status"] or "PENDING"
                    curr_t_stat = r["translation_status"] or "PENDING"

                    # 1. Translation Sanitization
                    new_fte = fte
                    new_t_stat = curr_t_stat

                    if fte and is_genuine_translation(ft, fte):
                        new_t_stat = "SUCCESS"
                    elif ft and is_already_english(ft):
                        new_fte = ft
                        new_t_stat = "NOT_NEEDED"
                    else:
                        new_fte = None
                        if curr_t_stat not in ["RATE_LIMITED", "ERROR"]:
                            new_t_stat = "PENDING"

                    # 2. Photo Sanitization
                    new_p_stat = curr_p_stat
                    has_photos = False
                    if img_j:
                        try:
                            imgs = json.loads(img_j)
                            has_photos = bool(imgs and len(imgs) > 0 and isinstance(imgs[0], str) and imgs[0].strip())
                        except Exception:
                            has_photos = False

                    if has_photos:
                        new_p_stat = "SUCCESS"
                    elif p_chk:
                        if curr_p_stat not in ["RATE_LIMITED", "ERROR"]:
                            new_p_stat = "NO_PHOTO"
                    else:
                        if curr_p_stat not in ["RATE_LIMITED", "ERROR"]:
                            new_p_stat = "PENDING"

                    if new_fte != fte or new_t_stat != curr_t_stat or new_p_stat != curr_p_stat:
                        cur.execute("""
                            UPDATE listings 
                            SET full_text_en = ?, translation_status = ?, photo_status = ?
                            WHERE canonical_id = ?
                        """, (new_fte, new_t_stat, new_p_stat, cid))
        except Exception as e:
            print(f"[WARNING] Database sanitization skipped: {e}", file=sys.stderr)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _serialize_record(self, record):
        now_iso = datetime.now(timezone.utc).isoformat()
        canonical_id = record.get("canonical_id") or record.get("id") or record.get("url")
        if not canonical_id:
            return None

        images = record.get("images") or []
        valid_images = [img for img in images if isinstance(img, str) and img.strip().startswith("http")] if isinstance(images, list) else []
        photos_checked_at = now_iso if valid_images else record.get("photos_checked_at")

        photo_status = record.get("photo_status")
        if not photo_status:
            if valid_images:
                photo_status = "SUCCESS"
            elif photos_checked_at:
                photo_status = "NO_PHOTO"
            else:
                photo_status = "PENDING"

        raw_text = record.get("full_text") or ""
        fte = record.get("full_text_en")
        trans_status = record.get("translation_status")
        trans_checked_at = record.get("translations_checked_at")
        clean_fte = fte if (fte and is_genuine_translation(raw_text, fte)) else None

        if not trans_status:
            if clean_fte:
                trans_status = "SUCCESS"
                if not trans_checked_at:
                    trans_checked_at = now_iso
            elif not raw_text.strip():
                trans_status = "NOT_NEEDED"
            else:
                trans_status = "PENDING"

        score = compute_record_completeness(record)
        detected_source = detect_source_from_record(record)
        return (
            str(canonical_id),
            detected_source,
            record.get("url") or "",
            str(record.get("category_id") or ""),
            record.get("property_category") or "General / Unclassified",
            record.get("listing_type") or "Unknown",
            record.get("full_text") or "",
            clean_fte,
            record.get("created_at"),
            int(record.get("creation_timestamp") or 0),
            record.get("extracted_at") or now_iso,
            json.dumps(record.get("prices") or [], ensure_ascii=False),
            json.dumps(record.get("sizes_sqm") or [], ensure_ascii=False),
            json.dumps(record.get("rooms") or [], ensure_ascii=False),
            json.dumps(record.get("locations") or [], ensure_ascii=False),
            json.dumps(record.get("phone_numbers") or [], ensure_ascii=False),
            json.dumps(record.get("zoning") or [], ensure_ascii=False),
            json.dumps(valid_images, ensure_ascii=False),
            score,
            1, # is_active
            now_iso, # first_seen_at
            now_iso, # last_seen_at
            photos_checked_at,
            photo_status,
            trans_status,
            trans_checked_at
        )

    def upsert_listing(self, record):
        """Inserts or updates a listing based on completeness and timestamps."""
        row_data = self._serialize_record(record)
        if not row_data:
            return None

        canonical_id = row_data[0]
        cur = self.conn.cursor()
        cur.execute("SELECT completeness_score FROM listings WHERE canonical_id = ?", (canonical_id,))
        existing = cur.fetchone()

        now_iso = datetime.now(timezone.utc).isoformat()
        with self.conn:
            if existing is None:
                cur.execute("""
                    INSERT INTO listings (
                        canonical_id, source, url, category_id, property_category, listing_type,
                        full_text, full_text_en, created_at, creation_timestamp, extracted_at,
                        prices_json, sizes_json, rooms_json, locations_json, phones_json, zoning_json, images_json,
                        completeness_score, is_active, first_seen_at, last_seen_at,
                        photos_checked_at, photo_status, translation_status, translations_checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row_data)
                return "inserted"
            else:
                existing_score = existing["completeness_score"]
                new_score = row_data[18]
                if new_score >= existing_score:
                    # Update all details, last_seen_at, and photos_checked_at
                    cur.execute("""
                        UPDATE listings SET
                            source = ?, url = ?, category_id = ?, property_category = ?, listing_type = ?,
                            full_text = ?, full_text_en = COALESCE(?, full_text_en), created_at = ?, creation_timestamp = ?, extracted_at = ?,
                            prices_json = ?, sizes_json = ?, rooms_json = ?, locations_json = ?, phones_json = ?, zoning_json = ?, images_json = ?,
                            completeness_score = ?, is_active = 1, last_seen_at = ?,
                            photos_checked_at = COALESCE(photos_checked_at, ?),
                            photo_status = CASE 
                                WHEN ? = 'SUCCESS' THEN 'SUCCESS'
                                WHEN photo_status = 'SUCCESS' THEN 'SUCCESS'
                                ELSE ?
                            END,
                            translation_status = CASE
                                WHEN ? = 'SUCCESS' THEN 'SUCCESS'
                                WHEN translation_status = 'SUCCESS' THEN 'SUCCESS'
                                ELSE ?
                            END,
                            translations_checked_at = COALESCE(translations_checked_at, ?)
                        WHERE canonical_id = ?
                    """, (
                        row_data[1], row_data[2], row_data[3], row_data[4], row_data[5],
                        row_data[6], row_data[7], row_data[8], row_data[9], row_data[10],
                        row_data[11], row_data[12], row_data[13], row_data[14], row_data[15], row_data[16], row_data[17],
                        row_data[18], now_iso,
                        row_data[22],
                        row_data[23], row_data[23],
                        row_data[24], row_data[24],
                        row_data[25],
                        canonical_id
                    ))
                    return "updated"
                else:
                    # Keep existing richer details, just update last_seen_at
                    cur.execute("UPDATE listings SET last_seen_at = ?, is_active = 1 WHERE canonical_id = ?", (now_iso, canonical_id))
                    return "touched"

    def batch_upsert_listings(self, records):
        """Batch inserts or updates records within a single transaction."""
        inserted, updated, touched = 0, 0, 0
        now_iso = datetime.now(timezone.utc).isoformat()
        
        with self.conn:
            cur = self.conn.cursor()
            for record in records:
                row_data = self._serialize_record(record)
                if not row_data:
                    continue
                canonical_id = row_data[0]
                cur.execute("SELECT completeness_score FROM listings WHERE canonical_id = ?", (canonical_id,))
                existing = cur.fetchone()
                if existing is None:
                    cur.execute("""
                        INSERT INTO listings (
                            canonical_id, source, url, category_id, property_category, listing_type,
                            full_text, full_text_en, created_at, creation_timestamp, extracted_at,
                            prices_json, sizes_json, rooms_json, locations_json, phones_json, zoning_json, images_json,
                            completeness_score, is_active, first_seen_at, last_seen_at,
                            photos_checked_at, photo_status, translation_status, translations_checked_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, row_data)
                    inserted += 1
                else:
                    existing_score = existing["completeness_score"]
                    new_score = row_data[18]
                    if new_score >= existing_score:
                        cur.execute("""
                            UPDATE listings SET
                                source = ?, url = ?, category_id = ?, property_category = ?, listing_type = ?,
                                full_text = ?, full_text_en = COALESCE(?, full_text_en), created_at = ?, creation_timestamp = ?, extracted_at = ?,
                                prices_json = ?, sizes_json = ?, rooms_json = ?, locations_json = ?, phones_json = ?, zoning_json = ?, images_json = ?,
                                completeness_score = ?, is_active = 1, last_seen_at = ?,
                                photos_checked_at = COALESCE(photos_checked_at, ?),
                                photo_status = CASE 
                                    WHEN ? = 'SUCCESS' THEN 'SUCCESS'
                                    WHEN photo_status = 'SUCCESS' THEN 'SUCCESS'
                                    ELSE ?
                                END,
                                translation_status = CASE
                                    WHEN ? = 'SUCCESS' THEN 'SUCCESS'
                                    WHEN translation_status = 'SUCCESS' THEN 'SUCCESS'
                                    ELSE ?
                                END,
                                translations_checked_at = COALESCE(translations_checked_at, ?)
                            WHERE canonical_id = ?
                        """, (
                            row_data[1], row_data[2], row_data[3], row_data[4], row_data[5],
                            row_data[6], row_data[7], row_data[8], row_data[9], row_data[10],
                            row_data[11], row_data[12], row_data[13], row_data[14], row_data[15], row_data[16], row_data[17],
                            row_data[18], now_iso,
                            row_data[22],
                            row_data[23], row_data[23],
                            row_data[24], row_data[24],
                            row_data[25],
                            canonical_id
                        ))
                        updated += 1
                    else:
                        cur.execute("UPDATE listings SET last_seen_at = ?, is_active = 1 WHERE canonical_id = ?", (now_iso, canonical_id))
                        touched += 1
        return {"inserted": inserted, "updated": updated, "touched": touched}

    def batch_update_classifications(self, records):
        """Batch updates classifications and extracted fields for listings."""
        updated = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.cursor()
            for record in records:
                row_data = self._serialize_record(record)
                if not row_data:
                    continue
                canonical_id = row_data[0]
                cur.execute("""
                    UPDATE listings SET
                        source = ?, category_id = ?, property_category = ?, listing_type = ?,
                        full_text_en = ?,
                        prices_json = ?, sizes_json = ?, rooms_json = ?, locations_json = ?, phones_json = ?, zoning_json = ?, images_json = ?,
                        completeness_score = ?, last_seen_at = ?
                    WHERE canonical_id = ?
                """, (
                    row_data[1], row_data[3], row_data[4], row_data[5],
                    row_data[7],
                    row_data[11], row_data[12], row_data[13], row_data[14], row_data[15], row_data[16], row_data[17],
                    row_data[18], now_iso, canonical_id
                ))
                updated += 1
        return updated

    def update_listing_images(self, canonical_id, images, status=None, checked=True):
        """Updates images_json, photo_status, photos_checked_at, and recomputes completeness score for a listing."""
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM listings WHERE canonical_id = ?", (str(canonical_id),))
            row = cur.fetchone()
            if not row:
                return False
            rec = self._row_to_dict(row)
            rec["images"] = images or []
            score = compute_record_completeness(rec)
            now_iso = datetime.now(timezone.utc).isoformat()
            row_keys = row.keys()
            checked_at = now_iso if checked else (row["photos_checked_at"] if "photos_checked_at" in row_keys else None)
            
            p_status = status
            if p_status is None:
                p_status = "SUCCESS" if (images and len(images) > 0) else "NO_PHOTO"

            cur.execute("""
                UPDATE listings 
                SET images_json = ?, completeness_score = ?, last_seen_at = ?, photos_checked_at = ?, photo_status = ? 
                WHERE canonical_id = ?
            """, (json.dumps(images or [], ensure_ascii=False), score, now_iso, checked_at, p_status, str(canonical_id)))
            return True

    def update_photo_status(self, canonical_id, status):
        """Updates photo_status (e.g. RATE_LIMITED, ERROR, NO_PHOTO, SUCCESS)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE listings 
                SET photo_status = ?, last_seen_at = ? 
                WHERE canonical_id = ?
            """, (status, now_iso, str(canonical_id)))
            return True

    def update_listing_translation(self, canonical_id, full_text_en, status="SUCCESS"):
        """Updates full_text_en, translation_status, translations_checked_at, and recomputes completeness score."""
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM listings WHERE canonical_id = ?", (str(canonical_id),))
            row = cur.fetchone()
            if not row:
                return False
            rec = self._row_to_dict(row)
            rec["full_text_en"] = full_text_en
            score = compute_record_completeness(rec)
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute("""
                UPDATE listings 
                SET full_text_en = ?, completeness_score = ?, last_seen_at = ?, translation_status = ?, translations_checked_at = ? 
                WHERE canonical_id = ?
            """, (full_text_en, score, now_iso, status, now_iso, str(canonical_id)))
            return True

    def update_translation_status(self, canonical_id, status):
        """Updates translation_status (e.g. RATE_LIMITED, ERROR, PENDING, NOT_NEEDED)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE listings 
                SET translation_status = ?, last_seen_at = ? 
                WHERE canonical_id = ?
            """, (status, now_iso, str(canonical_id)))
            return True

    def mark_photos_checked(self, canonical_id):
        """Marks that photos have been checked for this listing without modifying images."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE listings 
                SET photos_checked_at = ?, photo_status = 'NO_PHOTO', last_seen_at = ? 
                WHERE canonical_id = ?
            """, (now_iso, now_iso, str(canonical_id)))
            return True

    def _row_to_dict(self, row):
        row_keys = row.keys()
        images = []
        if "images_json" in row_keys and row["images_json"]:
            try:
                images = json.loads(row["images_json"])
            except Exception:
                images = []

        return {
            "canonical_id": row["canonical_id"],
            "source": row["source"],
            "url": row["url"],
            "category_id": row["category_id"],
            "property_category": row["property_category"],
            "listing_type": row["listing_type"],
            "full_text": row["full_text"],
            "full_text_en": row["full_text_en"] if "full_text_en" in row_keys else None,
            "created_at": row["created_at"],
            "creation_timestamp": row["creation_timestamp"],
            "extracted_at": row["extracted_at"],
            "prices": json.loads(row["prices_json"] or "[]"),
            "sizes_sqm": json.loads(row["sizes_json"] or "[]"),
            "rooms": json.loads(row["rooms_json"] or "[]"),
            "locations": json.loads(row["locations_json"] or "[]"),
            "phone_numbers": json.loads(row["phones_json"] or "[]"),
            "zoning": json.loads(row["zoning_json"] or "[]"),
            "images": images,
            "completeness_score": row["completeness_score"],
            "is_active": row["is_active"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
            "photos_checked_at": row["photos_checked_at"] if "photos_checked_at" in row_keys else None,
            "photo_status": row["photo_status"] if "photo_status" in row_keys else "PENDING",
            "translation_status": row["translation_status"] if "translation_status" in row_keys else "PENDING",
            "translations_checked_at": row["translations_checked_at"] if "translations_checked_at" in row_keys else None
        }

    def get_all_listings(self, active_only=True, max_age_days=None):
        """Retrieves listings matching filter conditions."""
        cur = self.conn.cursor()
        query = "SELECT * FROM listings WHERE 1=1"
        params = []

        if active_only:
            query += " AND is_active = 1"

        if max_age_days is not None:
            min_ts = int(time.time() - (max_age_days * 86400))
            # Include records with creation_timestamp >= min_ts or where timestamp is 0 (fallback)
            query += " AND (creation_timestamp >= ? OR creation_timestamp = 0)"
            params.append(min_ts)

        query += " ORDER BY creation_timestamp DESC"
        cur.execute(query, params)
        return [self._row_to_dict(row) for row in cur.fetchall()]

    def count_listings(self, active_only=True):
        cur = self.conn.cursor()
        if active_only:
            cur.execute("SELECT COUNT(*) FROM listings WHERE is_active = 1")
        else:
            cur.execute("SELECT COUNT(*) FROM listings")
        return cur.fetchone()[0]

    def reactivate_all_listings(self):
        """Sets is_active = 1 for all stored listings."""
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("UPDATE listings SET is_active = 1")
            return cur.rowcount

    def optimize_db(self):
        """Maintains SQLite query planner statistics and database health."""
        with self.conn:
            self.conn.execute("PRAGMA optimize;")

    def prune_stale_listings(self, max_age_days=60):
        """Deactivates listings older than max_age_days."""
        min_ts = int(time.time() - (max_age_days * 86400))
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE listings 
                SET is_active = 0 
                WHERE is_active = 1 
                  AND creation_timestamp > 0 
                  AND creation_timestamp < ?
            """, (min_ts,))
            return cur.rowcount

    def migrate_from_json_directories(self, scrapers_root=None):
        """Discovers existing JSON files and migrates all raw listings into SQLite."""
        root = scrapers_root or os.path.join(PROJECT_ROOT, "scrapers")
        total_migrated = 0
        total_files = 0

        for site_dirname in os.listdir(root):
            site_path = os.path.join(root, site_dirname)
            if not os.path.isdir(site_path) or site_dirname in ["processors", "utilities", "__pycache__", "data", "backfill", "platforms", "test_output"]:
                continue

            for subdir in ["housing_posts_data", "raw_data"]:
                subdir_path = os.path.join(site_path, subdir)
                if os.path.exists(subdir_path):
                    for fname in os.listdir(subdir_path):
                        if fname.endswith(".json"):
                            total_files += 1
                            fpath = os.path.join(subdir_path, fname)
                            try:
                                with open(fpath, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                if isinstance(data, list) and data:
                                    res = self.batch_upsert_listings(data)
                                    total_migrated += (res["inserted"] + res["updated"] + res["touched"])
                            except Exception as e:
                                print(f"[WARN] Failed to migrate {fpath}: {e}")

        return {"files_processed": total_files, "records_migrated": total_migrated}
