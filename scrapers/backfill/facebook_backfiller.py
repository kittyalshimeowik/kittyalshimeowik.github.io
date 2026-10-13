# scrapers/backfill/facebook_backfiller.py

from typing import Dict, Any, Optional
from scrapers.backfill.base import BasePlatformBackfiller
from scrapers.facebook.backfill_fb_photos import (
    run_fb_photos_backfill,
    get_fb_posts_to_backfill
)

class FacebookBackfiller(BasePlatformBackfiller):
    @property
    def platform_name(self) -> str:
        return "Facebook"

    def get_pending_photos_count(self, storage, active_only: bool = True) -> int:
        cur = storage.conn.cursor()
        query = """
            SELECT COUNT(*) FROM listings
            WHERE source = 'Facebook'
              AND (images_json IS NULL OR images_json = '[]' OR length(images_json) <= 2)
              AND photos_checked_at IS NULL
        """
        if active_only:
            query += " AND is_active = 1"
        cur.execute(query)
        return cur.fetchone()[0]

    def get_pending_translations_count(self, storage, active_only: bool = True) -> int:
        cur = storage.conn.cursor()
        query = """
            SELECT COUNT(*) FROM listings
            WHERE source = 'Facebook'
              AND (full_text_en IS NULL OR length(trim(full_text_en)) <= 5)
              AND full_text IS NOT NULL AND length(trim(full_text)) > 5
        """
        if active_only:
            query += " AND is_active = 1"
        cur.execute(query)
        return cur.fetchone()[0]

    def backfill_photos(
        self,
        storage,
        limit: Optional[int] = None,
        headless: bool = True,
        active_only: bool = True
    ) -> Dict[str, Any]:
        return run_fb_photos_backfill(
            limit=limit,
            headless=headless,
            active_only=active_only,
            regenerate_site_data=False
        )
