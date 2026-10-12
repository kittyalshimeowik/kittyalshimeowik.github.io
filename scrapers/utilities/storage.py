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
    cat = record.get("property_category")
    if cat in ["Apartment", "House", "Land"]:
        score += 15.0
    score += min(len(record.get("full_text") or "") / 100.0, 10.0)
    return score


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
                    created_at TEXT,
                    creation_timestamp INTEGER,
                    extracted_at TEXT,
                    prices_json TEXT,
                    sizes_json TEXT,
                    rooms_json TEXT,
                    locations_json TEXT,
                    phones_json TEXT,
                    zoning_json TEXT,
                    completeness_score REAL DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    first_seen_at TEXT,
                    last_seen_at TEXT
                );
            """)
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
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA synchronous = NORMAL;")

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

        score = compute_record_completeness(record)
        return (
            str(canonical_id),
            record.get("source") or "Unknown",
            record.get("url") or "",
            str(record.get("category_id") or ""),
            record.get("property_category") or "General / Unclassified",
            record.get("listing_type") or "Unknown",
            record.get("full_text") or "",
            record.get("created_at"),
            int(record.get("creation_timestamp") or 0),
            record.get("extracted_at") or now_iso,
            json.dumps(record.get("prices") or [], ensure_ascii=False),
            json.dumps(record.get("sizes_sqm") or [], ensure_ascii=False),
            json.dumps(record.get("rooms") or [], ensure_ascii=False),
            json.dumps(record.get("locations") or [], ensure_ascii=False),
            json.dumps(record.get("phone_numbers") or [], ensure_ascii=False),
            json.dumps(record.get("zoning") or [], ensure_ascii=False),
            score,
            1, # is_active
            now_iso, # first_seen_at
            now_iso  # last_seen_at
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
                        full_text, created_at, creation_timestamp, extracted_at,
                        prices_json, sizes_json, rooms_json, locations_json, phones_json, zoning_json,
                        completeness_score, is_active, first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row_data)
                return "inserted"
            else:
                existing_score = existing["completeness_score"]
                new_score = row_data[16]
                if new_score >= existing_score:
                    # Update all details and last_seen_at
                    cur.execute("""
                        UPDATE listings SET
                            source = ?, url = ?, category_id = ?, property_category = ?, listing_type = ?,
                            full_text = ?, created_at = ?, creation_timestamp = ?, extracted_at = ?,
                            prices_json = ?, sizes_json = ?, rooms_json = ?, locations_json = ?, phones_json = ?, zoning_json = ?,
                            completeness_score = ?, is_active = 1, last_seen_at = ?
                        WHERE canonical_id = ?
                    """, row_data[1:17] + (now_iso, canonical_id))
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
                            full_text, created_at, creation_timestamp, extracted_at,
                            prices_json, sizes_json, rooms_json, locations_json, phones_json, zoning_json,
                            completeness_score, is_active, first_seen_at, last_seen_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, row_data)
                    inserted += 1
                else:
                    existing_score = existing["completeness_score"]
                    new_score = row_data[16]
                    if new_score >= existing_score:
                        cur.execute("""
                            UPDATE listings SET
                                source = ?, url = ?, category_id = ?, property_category = ?, listing_type = ?,
                                full_text = ?, created_at = ?, creation_timestamp = ?, extracted_at = ?,
                                prices_json = ?, sizes_json = ?, rooms_json = ?, locations_json = ?, phones_json = ?, zoning_json = ?,
                                completeness_score = ?, is_active = 1, last_seen_at = ?
                            WHERE canonical_id = ?
                        """, row_data[1:17] + (now_iso, canonical_id))
                        updated += 1
                    else:
                        cur.execute("UPDATE listings SET last_seen_at = ?, is_active = 1 WHERE canonical_id = ?", (now_iso, canonical_id))
                        touched += 1
        return {"inserted": inserted, "updated": updated, "touched": touched}

    def _row_to_dict(self, row):
        return {
            "canonical_id": row["canonical_id"],
            "source": row["source"],
            "url": row["url"],
            "category_id": row["category_id"],
            "property_category": row["property_category"],
            "listing_type": row["listing_type"],
            "full_text": row["full_text"],
            "created_at": row["created_at"],
            "creation_timestamp": row["creation_timestamp"],
            "extracted_at": row["extracted_at"],
            "prices": json.loads(row["prices_json"] or "[]"),
            "sizes_sqm": json.loads(row["sizes_json"] or "[]"),
            "rooms": json.loads(row["rooms_json"] or "[]"),
            "locations": json.loads(row["locations_json"] or "[]"),
            "phone_numbers": json.loads(row["phones_json"] or "[]"),
            "zoning": json.loads(row["zoning_json"] or "[]"),
            "completeness_score": row["completeness_score"],
            "is_active": row["is_active"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"]
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
            if not os.path.isdir(site_path) or site_dirname in ["processors", "utilities", "__pycache__", "data"]:
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
