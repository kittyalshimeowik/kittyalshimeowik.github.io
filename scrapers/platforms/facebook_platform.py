# scrapers/platforms/facebook_platform.py

import re
from typing import Optional, List
from urllib.parse import urlparse

from scrapers.platforms.base import BasePlatform
from scrapers.backfill.base import BasePlatformBackfiller
from scrapers.backfill.facebook_backfiller import FacebookBackfiller


class FacebookPlatform(BasePlatform):
    """Facebook platform definition for scraping and backfill."""

    @property
    def key(self) -> str:
        return "facebook"

    @property
    def display_name(self) -> str:
        return "Facebook"

    @property
    def source_aliases(self) -> List[str]:
        return ["Facebook", "fb", "FB"]

    @property
    def url_domains(self) -> List[str]:
        return ["facebook.com", "fb.com"]

    @property
    def scraper_script_relpath(self) -> Optional[str]:
        return "scrapers/facebook/fb_scraper.py"

    def get_backfiller(self) -> Optional[BasePlatformBackfiller]:
        return FacebookBackfiller()

    def extract_canonical_id(self, url: str) -> Optional[str]:
        if not url:
            return None
        path_match = re.search(r'/(?:posts|permalink|multi_permalink|story\.php)/(\d+)', url)
        if path_match:
            return path_match.group(1)
        query_match = re.search(r'(?:story_fbid|fbid)=(\d+)', url)
        if query_match:
            return query_match.group(1)
        return None

    def is_valid_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urlparse(url.strip())
            host = (parsed.netloc or "").lower()
            if not ("facebook.com" in host or "fb.com" in host):
                return False
            return len(parsed.path) >= 5
        except Exception:
            return False
