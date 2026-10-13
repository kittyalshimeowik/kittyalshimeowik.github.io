# scrapers/platforms/base.py
"""
Base platform abstractions for the Armenia Real Estate Hub.
Allows plug-and-play addition of new real estate scraping and backfilling platforms.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
import re
from urllib.parse import urlparse

from scrapers.backfill.base import BasePlatformBackfiller


class BasePlatform(ABC):
    """
    Standard interface and metadata definition for a scraping platform.
    Subclass this to add new platforms (e.g., Telegram, Estate.am, Bnakaran.com, etc.).
    """

    @property
    @abstractmethod
    def key(self) -> str:
        """Unique lowercase identifier (e.g. 'facebook', 'listam', 'telegram')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name (e.g. 'Facebook', 'List.am', 'Telegram')."""
        pass

    @property
    def source_aliases(self) -> List[str]:
        """Aliases mapped to this platform in SQLite listings table (e.g. ['Facebook', 'fb'])."""
        return [self.display_name, self.key]

    @property
    def url_domains(self) -> List[str]:
        """List of domain substrings or hostnames matching this platform."""
        return []

    @property
    def scraper_script_relpath(self) -> Optional[str]:
        """Relative path from project root to the scraper script (e.g. 'scrapers/facebook/fb_scraper.py')."""
        return None

    def get_backfiller(self) -> Optional[BasePlatformBackfiller]:
        """Returns the platform backfiller instance, if supported."""
        return None

    def extract_canonical_id(self, url: str) -> Optional[str]:
        """Extracts numeric or unique post ID from platform URL. Override if custom logic needed."""
        if not url:
            return None
        # Common pattern: /item/123, /posts/123, /property/123
        match = re.search(r'/(?:posts|permalink|multi_permalink|story\.php|item|property|ad|listing|rent|sale)/(\d+)', url)
        if match:
            return match.group(1)
        return None

    def is_valid_url(self, url: str) -> bool:
        """Validates platform URL. Default checks domain match and non-empty path."""
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urlparse(url.strip())
            host = (parsed.netloc or "").lower()
            if not any(d.lower() in host for d in self.url_domains):
                return False
            return len(parsed.path) > 1
        except Exception:
            return False
