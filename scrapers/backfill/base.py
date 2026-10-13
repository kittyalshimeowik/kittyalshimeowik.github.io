# scrapers/backfill/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BasePlatformBackfiller(ABC):
    """
    Abstract base class for all platform backfillers.
    Extend this class to add support for new platforms (e.g., Telegram, Estate.am, etc.).
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """The canonical source name in the database (e.g. 'Facebook', 'List.am')."""
        pass

    @abstractmethod
    def get_pending_photos_count(self, storage, active_only: bool = True) -> int:
        """Returns the number of listings from this platform missing photos."""
        pass

    @abstractmethod
    def get_pending_translations_count(self, storage, active_only: bool = True) -> int:
        """Returns the number of listings from this platform missing English translation."""
        pass

    @abstractmethod
    def backfill_photos(
        self,
        storage,
        limit: Optional[int] = None,
        headless: bool = True,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Runs the photo backfill for this platform.
        Returns a dict with statistics: {'processed': int, 'photos_found': int}
        """
        pass
