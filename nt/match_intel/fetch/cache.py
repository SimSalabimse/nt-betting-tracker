"""Disk cache for MatchFetchBundle (TTL)."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from nt.match_intel.fetch.bundle import MatchFetchBundle, bundle_from_dict, bundle_to_dict

# Default under repo-relative data cache (also allow .firecrawl/ via config)
DEFAULT_CACHE_DIR = "data/cache/match_intel_fetch"


def _safe_host(url: str) -> str:
    try:
        host = urlparse(url).netloc or "unknown"
    except Exception:  # noqa: BLE001
        host = "unknown"
    host = re.sub(r"[^a-zA-Z0-9._-]+", "_", host).strip("._") or "unknown"
    return host[:80]


def cache_key(url: str, *, match_key: str | None = None, source: str | None = None) -> str:
    """Stable filesystem key for a URL (+ optional match/source)."""
    raw = f"{source or ''}|{match_key or ''}|{(url or '').strip()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    host = _safe_host(url)
    mk = re.sub(r"[^a-z0-9_]+", "_", (match_key or "page").lower())[:40] or "page"
    return f"{host}_{mk}_{digest}"


def resolve_cache_dir(cfg: dict[str, Any] | None = None) -> Path:
    """
    Resolve cache directory from match_intel / fetch config.

    Prefer fetch.cache_dir; fall back to data/cache/match_intel_fetch.
    """
    mi = cfg or {}
    fetch = mi.get("fetch") if isinstance(mi.get("fetch"), dict) else {}
    fetch = fetch or {}
    raw = fetch.get("cache_dir") or mi.get("cache_dir") or DEFAULT_CACHE_DIR
    return Path(str(raw))


def cache_path(
    url: str,
    *,
    cfg: dict[str, Any] | None = None,
    match_key: str | None = None,
    source: str | None = None,
    cache_dir: Path | str | None = None,
) -> Path:
    root = Path(cache_dir) if cache_dir is not None else resolve_cache_dir(cfg)
    return root / f"{cache_key(url, match_key=match_key, source=source)}.json"


def get_cached_bundle(
    url: str,
    *,
    cfg: dict[str, Any] | None = None,
    match_key: str | None = None,
    source: str | None = None,
    cache_dir: Path | str | None = None,
    ttl_hours: float | None = None,
) -> MatchFetchBundle | None:
    """Return cached ok bundle if file exists and within TTL; else None."""
    mi = cfg or {}
    fetch = mi.get("fetch") if isinstance(mi.get("fetch"), dict) else {}
    fetch = fetch or {}
    if ttl_hours is None:
        ttl_hours = float(
            fetch.get("cache_ttl_hours")
            or mi.get("cache_ttl_hours")
            or mi.get("ttl_hours")
            or 6
        )
    path = cache_path(
        url, cfg=cfg, match_key=match_key, source=source, cache_dir=cache_dir
    )
    if not path.is_file():
        return None
    try:
        age_s = time.time() - path.stat().st_mtime
        if age_s > float(ttl_hours) * 3600:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    bundle = bundle_from_dict(data if isinstance(data, dict) else None)
    if bundle is None or not bundle.ok:
        return None
    # Mark as cache hit for observability
    bundle.method = "cache"
    return bundle


def put_cached_bundle(
    bundle: MatchFetchBundle,
    *,
    cfg: dict[str, Any] | None = None,
    match_key: str | None = None,
    source: str | None = None,
    cache_dir: Path | str | None = None,
) -> Path | None:
    """Write bundle JSON to disk; returns path or None on failure."""
    if not bundle or not bundle.url:
        return None
    path = cache_path(
        bundle.url,
        cfg=cfg,
        match_key=match_key,
        source=source,
        cache_dir=cache_dir,
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = bundle_to_dict(bundle)
        # Do not force method=cache on disk — keep original fetch method
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return path
    except OSError:
        return None


def clear_cache(cache_dir: Path | str) -> int:
    """Delete all .json cache files under dir; return count removed."""
    root = Path(cache_dir)
    if not root.is_dir():
        return 0
    n = 0
    for p in root.glob("*.json"):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n
