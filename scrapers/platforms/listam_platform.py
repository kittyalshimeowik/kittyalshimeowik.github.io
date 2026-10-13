# scrapers/platforms/listam_platform.py

import re
from typing import Optional, List
from urllib.parse import urlparse

from scrapers.platforms.base import BasePlatform
from scrapers.backfill.base import BasePlatformBackfiller
from scrapers.backfill.listam_backfiller import ListAmBackfiller


class ListAmPlatform(BasePlatform):
    """List.am platform definition for scraping and backfill."""

    @property
    def key(self) -> str:
        return "listam"

    @property
    def display_name(self) -> str:
        return "List.am"

    @property
    def source_aliases(self) -> List[str]:
        return ["List.am", "listam", "list.am"]

    @property
    def url_domains(self) -> List[str]:
        return ["list.am"]

    @property
    def scraper_script_relpath(self) -> Optional[str]:
        return "scrapers/listam/list_am_scraper.py"

    def get_backfiller(self) -> Optional[BasePlatformBackfiller]:
        return ListAmBackfiller()

    def extract_canonical_id(self, url: str) -> Optional[str]:
        if not url:
            return None
        match = re.search(r'/item/(\d+)', url)
        if match:
            return match.group(1)
        return None

    def is_valid_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urlparse(url.strip())
            host = (parsed.netloc or "").lower()
            if "list.am" not in host:
                return False
            return bool(re.search(r'/item/\d+', parsed.path))
        except Exception:
            return False
