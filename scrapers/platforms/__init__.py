# scrapers/platforms/__init__.py
from scrapers.platforms.base import BasePlatform
from scrapers.platforms.registry import (
    register_platform,
    get_platform,
    get_platform_for_url,
    list_supported_platforms,
    get_all_platforms,
    get_all_backfillers
)

__all__ = [
    "BasePlatform",
    "register_platform",
    "get_platform",
    "get_platform_for_url",
    "list_supported_platforms",
    "get_all_platforms",
    "get_all_backfillers"
]
