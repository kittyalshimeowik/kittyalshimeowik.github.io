# scrapers/backfill/registry.py

from typing import Dict, List, Optional
from scrapers.backfill.base import BasePlatformBackfiller
from scrapers.backfill.facebook_backfiller import FacebookBackfiller
from scrapers.backfill.listam_backfiller import ListAmBackfiller

# Central registry for all supported backfillers
_REGISTRY: Dict[str, BasePlatformBackfiller] = {
    "facebook": FacebookBackfiller(),
    "listam": ListAmBackfiller(),
}


def register_platform_backfiller(name: str, backfiller: BasePlatformBackfiller):
    """Extensibility hook: Registers a new platform backfiller."""
    _REGISTRY[name.lower()] = backfiller


def get_platform_backfiller(name: str) -> Optional[BasePlatformBackfiller]:
    """Retrieves a registered platform backfiller by key or alias."""
    if not name:
        return None
    key = name.lower()
    if key in _REGISTRY:
        return _REGISTRY[key]
    
    # Check platform registry for dynamically registered platforms
    try:
        from scrapers.platforms.registry import get_platform
        plat = get_platform(name)
        if plat:
            bf = plat.get_backfiller()
            if bf:
                _REGISTRY[plat.key] = bf
                return bf
    except ImportError:
        pass
    return None


def get_all_platform_backfillers() -> Dict[str, BasePlatformBackfiller]:
    """Returns all registered platform backfillers."""
    # Synchronize with platform registry if available
    try:
        from scrapers.platforms.registry import get_all_backfillers as _get_platform_backfillers
        all_bfs = _get_platform_backfillers()
        for k, v in all_bfs.items():
            if k not in _REGISTRY:
                _REGISTRY[k] = v
    except ImportError:
        pass
    return dict(_REGISTRY)


def list_supported_platforms() -> List[str]:
    """Returns list of registered platform names."""
    return list(get_all_platform_backfillers().keys())
