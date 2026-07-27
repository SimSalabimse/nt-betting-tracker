"""
MIC fetch layer: Firecrawl / Playwright / HTTP with disk cache + circuit breaker.

Public entrypoints:
  - fetch_page / fetch_match_bundle (router)
  - MatchFetchBundle
"""
from __future__ import annotations

from nt.match_intel.fetch.bundle import MatchFetchBundle, bundle_from_dict, bundle_to_dict
from nt.match_intel.fetch.router import fetch_match_bundle, fetch_page, resolve_backend_order

__all__ = [
    "MatchFetchBundle",
    "bundle_from_dict",
    "bundle_to_dict",
    "fetch_match_bundle",
    "fetch_page",
    "resolve_backend_order",
]
