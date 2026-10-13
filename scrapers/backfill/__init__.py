# scrapers/backfill/__init__.py

from scrapers.backfill.base import BasePlatformBackfiller
from scrapers.backfill.registry import (
    register_platform_backfiller,
    get_platform_backfiller,
    get_all_platform_backfillers,
    list_supported_platforms
)

__all__ = [
    "BasePlatformBackfiller",
    "register_platform_backfiller",
    "get_platform_backfiller",
    "get_all_platform_backfillers",
    "list_supported_platforms"
]
