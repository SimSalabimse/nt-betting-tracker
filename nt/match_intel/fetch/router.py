"""
Backend selection: firecrawl → playwright → http (config + availability).

Uses disk cache + rate limit / circuit breaker.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from nt.match_intel.fetch.bundle import MatchFetchBundle
from nt.match_intel.fetch.cache import get_cached_bundle, put_cached_bundle
from nt.match_intel.fetch.firecrawl_fetch import (
    fetch_firecrawl,
    firecrawl_cli_available,
    firecrawl_configured,
    firecrawl_sdk_available,
)
from nt.match_intel.fetch.http_fetch import fetch_http
from nt.match_intel.fetch.playwright_fetch import (
    fetch_playwright,
    host_needs_playwright,
    playwright_available,
)
from nt.match_intel.fetch.rate_limit import RateLimitCircuit, get_default_limiter


def _fetch_cfg(mi: dict[str, Any] | None) -> dict[str, Any]:
    mi = mi or {}
    fetch = mi.get("fetch") if isinstance(mi.get("fetch"), dict) else {}
    return dict(fetch or {})


def _timeout_s(mi: dict[str, Any] | None) -> float:
    mi = mi or {}
    fetch = _fetch_cfg(mi)
    return float(fetch.get("timeout_s") or mi.get("timeout_s") or 45)


def _prefer(mi: dict[str, Any] | None) -> str:
    """
    Prefer order head: firecrawl | playwright | http.

    Accepts fetch.prefer (PR-1) or fetch.primary (legacy design).
    """
    fetch = _fetch_cfg(mi)
    raw = str(fetch.get("prefer") or fetch.get("primary") or "firecrawl").strip().lower()
    # Normalize aliases
    if raw in ("http_bs4", "httpx", "urllib", "static"):
        return "http"
    if raw in ("playwright_bs4", "pw"):
        return "playwright"
    if raw in ("fc", "firecrawl_api"):
        return "firecrawl"
    if raw not in ("firecrawl", "playwright", "http"):
        return "firecrawl"
    return raw


def _playwright_hosts(mi: dict[str, Any] | None) -> list[str]:
    fetch = _fetch_cfg(mi)
    hosts = fetch.get("playwright_hosts")
    if isinstance(hosts, list) and hosts:
        return [str(h) for h in hosts]
    return [
        "flashscore.com",
        "www.flashscore.com",
        "sofascore.com",
        "www.sofascore.com",
    ]


def resolve_backend_order(
    url: str,
    *,
    mi_cfg: dict[str, Any] | None = None,
) -> list[str]:
    """
    Ordered list of backends to try for this URL.

    User prefer first, then remaining. For playwright_hosts, do not lead with http
    (wrong_backend risk); escalate to playwright when preferred fails.
    """
    prefer = _prefer(mi_cfg)
    needs_pw = host_needs_playwright(url, _playwright_hosts(mi_cfg))
    allow_fc = True
    fetch = _fetch_cfg(mi_cfg)
    if "allow_firecrawl" in fetch:
        allow_fc = bool(fetch.get("allow_firecrawl"))
    # When prefer is firecrawl, always allow firecrawl attempt
    if prefer == "firecrawl":
        allow_fc = True

    order: list[str] = []
    if prefer == "firecrawl" and allow_fc:
        order.append("firecrawl")
    elif prefer == "playwright":
        order.append("playwright")
    elif prefer == "http":
        if needs_pw:
            # Prefer playwright for SPA hosts even if prefer=http
            order.append("playwright")
            order.append("http")
        else:
            order.append("http")

    for b in ("firecrawl", "playwright", "http"):
        if b == "firecrawl" and not allow_fc and prefer != "firecrawl":
            continue
        if b not in order:
            # For SPA hosts, put http last
            if b == "http" and needs_pw and "playwright" not in order:
                order.insert(0, "playwright")
            order.append(b)

    # Ensure playwright before http on SPA hosts
    if needs_pw and "playwright" in order and "http" in order:
        pi, hi = order.index("playwright"), order.index("http")
        if hi < pi:
            order[hi], order[pi] = order[pi], order[hi]
    return order


def _backend_available(name: str) -> tuple[bool, str | None]:
    """Return (available, error_if_not)."""
    if name == "firecrawl":
        if firecrawl_sdk_available() or firecrawl_cli_available() or firecrawl_configured():
            # configured may be key-only; still attempt
            return True, None
        return False, "firecrawl_not_installed"
    if name == "playwright":
        if playwright_available():
            return True, None
        return False, "playwright_not_installed"
    if name == "http":
        return True, None
    return False, "fetch_failed"


def _run_backend(
    name: str,
    url: str,
    *,
    mi_cfg: dict[str, Any] | None,
    sport: str | None,
) -> MatchFetchBundle:
    mi = mi_cfg or {}
    fetch = _fetch_cfg(mi)
    timeout_s = _timeout_s(mi)
    if name == "firecrawl":
        return fetch_firecrawl(url, timeout_s=timeout_s)
    if name == "playwright":
        return fetch_playwright(
            url,
            timeout_s=timeout_s,
            wait_selector_ms=int(fetch.get("wait_selector_ms") or 12_000),
            h2h_wait_ms=int(fetch.get("h2h_wait_ms") or 8_000),
            fetch_h2h_tab=bool(fetch.get("fetch_h2h_tab", True)),
            max_xhr_bytes=int(fetch.get("max_xhr_bytes") or 1_500_000),
            max_bytes=int(fetch.get("max_bytes") or 2_500_000),
            sport=sport,
        )
    if name == "http":
        return fetch_http(
            url,
            timeout_s=timeout_s,
            max_bytes=int(fetch.get("max_bytes") or 2_500_000),
        )
    return MatchFetchBundle(ok=False, url=url, method=name, error="fetch_failed")


def fetch_match_bundle(
    url: str,
    *,
    mi_cfg: dict[str, Any] | None = None,
    match_key: str | None = None,
    source: str | None = None,
    sport: str | None = None,
    use_cache: bool = True,
    limiter: RateLimitCircuit | None = None,
    force: bool = False,
) -> MatchFetchBundle:
    """
    Fetch a match page with cache + rate limit + backend failover.

    Never raises. Tests should mock backends / use force+cache fixtures.
    """
    if not url or not str(url).strip():
        return MatchFetchBundle(ok=False, url=url or "", method="", error="empty_url")

    url = str(url).strip()
    mi = mi_cfg or {}
    limiter = limiter or get_default_limiter(mi)

    if limiter.is_open(url):
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="",
            error="circuit_open",
            duration_ms=0,
        )

    if use_cache and not force:
        cached = get_cached_bundle(url, cfg=mi, match_key=match_key, source=source)
        if cached is not None:
            return cached

    order = resolve_backend_order(url, mi_cfg=mi)
    last = MatchFetchBundle(ok=False, url=url, method="", error="fetch_failed")
    needs_pw = host_needs_playwright(url, _playwright_hosts(mi))

    for backend in order:
        avail, avail_err = _backend_available(backend)
        if not avail:
            last = MatchFetchBundle(
                ok=False,
                url=url,
                method=backend,
                error=avail_err or "fetch_failed",
            )
            # SPA host without playwright: do not pretend http can grade-C
            if backend == "playwright" and needs_pw and avail_err == "playwright_not_installed":
                # Still try other backends but remember wrong_backend if only http left
                continue
            continue

        limiter.wait_turn(url)
        bundle = _run_backend(backend, url, mi_cfg=mi, sport=sport)

        if bundle.ok:
            limiter.record_success(url)
            if use_cache:
                put_cached_bundle(
                    bundle, cfg=mi, match_key=match_key, source=source
                )
            return bundle

        # Map shell on SPA host via http → wrong_backend when playwright preferred
        err = bundle.error or "fetch_failed"
        if (
            backend == "http"
            and needs_pw
            and err in ("js_shell_empty", "fetch_failed")
        ):
            bundle.error = "wrong_backend" if err == "js_shell_empty" else err

        last = bundle
        if err in ("timeout", "blocked", "fetch_failed", "js_shell_empty", "wrong_backend"):
            limiter.record_failure(url)
            if limiter.is_open(url):
                return MatchFetchBundle(
                    ok=False,
                    url=url,
                    method=bundle.method,
                    error="circuit_open",
                    duration_ms=bundle.duration_ms,
                    html=bundle.html,
                )
        # Try next backend
        continue

    # If last error is playwright_not_installed on SPA host, keep that code
    if needs_pw and last.error in (None, "fetch_failed", "wrong_backend", "js_shell_empty"):
        if not playwright_available():
            # Prefer explicit install error when SPA host and nothing worked
            if last.method in ("", "http") or last.error in (
                "wrong_backend",
                "js_shell_empty",
                "fetch_failed",
            ):
                if not any(
                    b == "firecrawl" and (firecrawl_sdk_available() or firecrawl_cli_available())
                    for b in order
                ) or last.error in ("wrong_backend", "js_shell_empty"):
                    if last.error in ("wrong_backend", "js_shell_empty") and not last.ok:
                        # Keep last if firecrawl also failed; surface playwright missing when it was first SPA choice
                        pass
    return last


def fetch_page(
    url: str,
    *,
    mi_cfg: dict[str, Any] | None = None,
    **kwargs: Any,
) -> MatchFetchBundle:
    """Alias for fetch_match_bundle (simple single-URL API)."""
    return fetch_match_bundle(url, mi_cfg=mi_cfg, **kwargs)
