# scrapers/platforms/registry.py
"""
Central platform registry for the Armenia Real Estate Hub.
Provides dynamic discovery, validation, and execution hooks for all platforms.
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse

from scrapers.platforms.base import BasePlatform
from scrapers.platforms.facebook_platform import FacebookPlatform
from scrapers.platforms.listam_platform import ListAmPlatform
from scrapers.backfill.base import BasePlatformBackfiller

# Default platform registry
_PLATFORMS: Dict[str, BasePlatform] = {
    "facebook": FacebookPlatform(),
    "listam": ListAmPlatform(),
}


def register_platform(platform: BasePlatform):
    """
    Dynamically registers a new platform.
    Can be used at runtime to add Telegram, Estate.am, etc.
    """
    _PLATFORMS[platform.key.lower()] = platform


def get_platform(name_or_alias: str) -> Optional[BasePlatform]:
    """
    Retrieves a registered platform by key or alias (e.g., 'facebook', 'List.am', 'fb').
    Case-insensitive.
    """
    if not name_or_alias:
        return None
    target = name_or_alias.strip().lower()

    # Direct key lookup
    if target in _PLATFORMS:
        return _PLATFORMS[target]

    # Search through aliases
    for platform in _PLATFORMS.values():
        aliases = [a.lower() for a in platform.source_aliases]
        if target in aliases:
            return platform

    return None


def get_platform_for_url(url: str) -> Optional[BasePlatform]:
    """Detects matching platform for a given URL based on hostname."""
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
        for platform in _PLATFORMS.values():
            if any(d.lower() in host for d in platform.url_domains):
                return platform
    except Exception:
        pass
    return None


def list_supported_platforms() -> List[str]:
    """Returns list of registered platform keys (e.g. ['facebook', 'listam'])."""
    return list(_PLATFORMS.keys())


def get_all_platforms() -> Dict[str, BasePlatform]:
    """Returns a copy of all registered platforms."""
    return dict(_PLATFORMS)


def get_all_backfillers() -> Dict[str, BasePlatformBackfiller]:
    """Returns a dict of all platform backfillers."""
    backfillers = {}
    for key, platform in _PLATFORMS.items():
        bf = platform.get_backfiller()
        if bf:
            backfillers[key] = bf
    return backfillers
