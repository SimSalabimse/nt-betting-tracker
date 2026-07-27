"""
Optional Firecrawl adapter.

Not a hard dependency — import fails closed. Live fetch is never used in tests.
"""
from __future__ import annotations

from typing import Any


def firecrawl_available() -> bool:
    try:
        import firecrawl  # type: ignore  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def fetch_markdown(url: str, *, timeout_s: float = 45.0) -> dict[str, Any]:
    """
    Attempt Firecrawl scrape → markdown/HTML.

    Returns {ok, markdown, html, error, method}.
    Never raises for missing package.
    """
    if not url:
        return {"ok": False, "markdown": "", "html": "", "error": "empty_url", "method": "firecrawl"}
    try:
        # Soft optional — several package names exist historically
        client = None
        try:
            from firecrawl import FirecrawlApp  # type: ignore

            client = FirecrawlApp()
        except Exception:  # noqa: BLE001
            client = None
        if client is None:
            return {
                "ok": False,
                "markdown": "",
                "html": "",
                "error": "firecrawl_not_installed",
                "method": "firecrawl",
            }
        # Do not call network from library defaults without explicit API key/env;
        # leave a clear not-configured path for CI.
        return {
            "ok": False,
            "markdown": "",
            "html": "",
            "error": "firecrawl_not_configured",
            "method": "firecrawl",
        }
    except Exception as ex:  # noqa: BLE001
        return {
            "ok": False,
            "markdown": "",
            "html": "",
            "error": str(ex),
            "method": "firecrawl",
        }
