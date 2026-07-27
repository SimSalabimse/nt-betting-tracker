"""
Deprecation shim → nt.match_intel.fetch.firecrawl_fetch.

Implementation lives only under fetch/; this module re-exports for backward imports.
"""
from __future__ import annotations

from typing import Any

from nt.match_intel.fetch.firecrawl_fetch import (
    fetch_firecrawl,
    fetch_markdown as _fetch_markdown,
    firecrawl_api_key,
    firecrawl_cli_available,
    firecrawl_configured,
    firecrawl_sdk_available,
)


def firecrawl_available() -> bool:
    """True if SDK import works (legacy name). Prefer firecrawl_configured() for ops."""
    return firecrawl_sdk_available()


def fetch_markdown(url: str, *, timeout_s: float = 45.0) -> dict[str, Any]:
    """
    Attempt Firecrawl scrape → markdown/HTML.

    Returns {ok, markdown, html, error, method, ...}.
    Real network when FIRECRAWL_API_KEY or CLI credentials work.
    """
    return _fetch_markdown(url, timeout_s=timeout_s)


__all__ = [
    "fetch_firecrawl",
    "fetch_markdown",
    "firecrawl_api_key",
    "firecrawl_available",
    "firecrawl_cli_available",
    "firecrawl_configured",
    "firecrawl_sdk_available",
]
