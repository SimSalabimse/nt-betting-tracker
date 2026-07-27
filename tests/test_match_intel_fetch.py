"""
MIC fetch layer unit tests — offline only (mocks; no live network).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.match_intel.fetch.bundle import MatchFetchBundle, bundle_from_dict, bundle_to_dict
from nt.match_intel.fetch.cache import (
    cache_key,
    get_cached_bundle,
    put_cached_bundle,
)
from nt.match_intel.fetch.rate_limit import RateLimitCircuit, reset_default_limiter
from nt.match_intel.pipeline import build_match_intel
from nt.match_intel.schema import mic_match_key


@pytest.fixture(autouse=True)
def _reset_limiter():
    reset_default_limiter()
    yield
    reset_default_limiter()


def test_bundle_roundtrip():
    b = MatchFetchBundle(
        ok=True,
        url="https://example.com/m",
        method="firecrawl",
        html="<html><title>A vs B</title></html>",
        markdown="# A vs B",
        duration_ms=12,
        xhrs=[{"url": "https://example.com/api", "data": {"x": 1}}],
    )
    d = bundle_to_dict(b)
    b2 = bundle_from_dict(d)
    assert b2 is not None
    assert b2.ok is True
    assert b2.method == "firecrawl"
    assert "A vs B" in b2.identity_text()


def test_disk_cache_ttl(tmp_path: Path):
    url = "https://example.com/match/1"
    cfg = {
        "fetch": {
            "cache_dir": str(tmp_path / "cache"),
            "cache_ttl_hours": 6,
        }
    }
    b = MatchFetchBundle(
        ok=True,
        url=url,
        method="http",
        html="<html><title>Home vs Away</title><body>content enough</body></html>",
        duration_ms=5,
    )
    path = put_cached_bundle(b, cfg=cfg, match_key="home_vs_away", source="test")
    assert path is not None and path.is_file()

    hit = get_cached_bundle(url, cfg=cfg, match_key="home_vs_away", source="test")
    assert hit is not None
    assert hit.ok is True
    assert hit.method == "cache"
    assert "Home" in (hit.html or hit.identity_text())

    # Expired TTL
    expired = get_cached_bundle(
        url, cfg=cfg, match_key="home_vs_away", source="test", ttl_hours=0
    )
    # ttl_hours=0 means any positive age fails — file mtime is ~now so age≈0 may still pass
    # Force by setting negative effective: write then use tiny TTL with sleep
    time.sleep(0.05)
    expired2 = get_cached_bundle(
        url,
        cfg={
            "fetch": {
                "cache_dir": str(tmp_path / "cache"),
                "cache_ttl_hours": 1e-9,  # ~3.6e-6 seconds
            }
        },
        match_key="home_vs_away",
        source="test",
        ttl_hours=1e-9,
    )
    # age after 50ms >> 1e-9 hours... wait 1e-9 hours is 3.6e-6 seconds, so after 50ms it expires
    assert expired2 is None


def test_cache_key_stable():
    k1 = cache_key("https://www.flashscore.com/match/abc", match_key="a_vs_b")
    k2 = cache_key("https://www.flashscore.com/match/abc", match_key="a_vs_b")
    k3 = cache_key("https://www.flashscore.com/match/xyz", match_key="a_vs_b")
    assert k1 == k2
    assert k1 != k3


def test_circuit_breaker_opens():
    lim = RateLimitCircuit(
        min_interval_ms=0,
        failure_threshold=3,
        open_seconds=60,
    )
    url = "https://example.com/x"
    assert lim.is_open(url) is False
    assert lim.record_failure(url) is False
    assert lim.record_failure(url) is False
    opened = lim.record_failure(url)
    assert opened is True
    assert lim.is_open(url) is True
    # success would close after half-open, but while open wait
    lim.record_success(url)  # allowed to clear
    assert lim.is_open(url) is False


def test_rate_limit_wait_turn():
    lim = RateLimitCircuit(min_interval_ms=80, failure_threshold=99, open_seconds=1)
    url = "https://host.example/a"
    t0 = time.perf_counter()
    lim.wait_turn(url)
    lim.wait_turn(url)
    elapsed = time.perf_counter() - t0
    assert elapsed >= 0.05  # roughly min interval


def test_firecrawl_shim_uses_fetch_package(monkeypatch):
    from nt.match_intel.sources import firecrawl as shim
    from nt.match_intel.fetch import firecrawl_fetch as fc

    def _fake(url: str, *, timeout_s: float = 45.0, prefer_cli: bool = False):
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html="<html><title>Alpha vs Beta | League</title></html>",
            markdown="# Alpha vs Beta",
            duration_ms=1,
            page_meta={"title": "Alpha vs Beta | League", "home_name": "Alpha", "away_name": "Beta"},
        )

    monkeypatch.setattr(fc, "fetch_firecrawl", _fake)
    # re-bind shim's path through fetch_markdown
    monkeypatch.setattr(
        "nt.match_intel.fetch.firecrawl_fetch.fetch_firecrawl",
        _fake,
    )

    out = shim.fetch_markdown("https://example.com/m")
    # Depending on import binding, either mock or real not-configured
    assert "method" in out
    assert out["method"] == "firecrawl"


def test_mock_firecrawl_fetch_markdown(monkeypatch):
    from nt.match_intel.fetch import firecrawl_fetch as fc

    monkeypatch.setattr(fc, "firecrawl_api_key", lambda: "test-key-not-real")
    monkeypatch.setattr(fc, "firecrawl_sdk_available", lambda: True)
    monkeypatch.setattr(fc, "firecrawl_cli_available", lambda: False)

    class _FakeApp:
        def __init__(self, api_key: str | None = None):
            self.api_key = api_key

        def scrape_url(self, url: str, formats=None, **kwargs):
            return {
                "markdown": "# Rosenborg vs Fredrikstad",
                "html": (
                    "<html><title>Rosenborg vs Fredrikstad | Eliteserien</title>"
                    "<body>Rosenborg Fredrikstad form</body></html>"
                ),
            }

    import sys
    import types

    mod = types.ModuleType("firecrawl")
    mod.FirecrawlApp = _FakeApp  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "firecrawl", mod)

    b = fc.fetch_firecrawl("https://www.flashscore.com/match/test")
    assert b.ok is True
    assert b.method == "firecrawl"
    assert "Rosenborg" in (b.html or b.markdown)


def test_router_uses_mock_backend(monkeypatch, tmp_path: Path):
    from nt.match_intel.fetch import router as R
    from nt.match_intel.fetch import firecrawl_fetch as fc

    def _fake_fc(url: str, *, timeout_s: float = 45.0, prefer_cli: bool = False):
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html=(
                "<html><title>Alpha FC vs Beta United | Cup</title>"
                "<body>Alpha FC vs Beta United match preview lots of text here</body></html>"
            ),
            markdown="# Alpha FC vs Beta United",
            duration_ms=3,
            page_meta={
                "title": "Alpha FC vs Beta United | Cup",
                "home_name": "Alpha FC",
                "away_name": "Beta United",
            },
        )

    monkeypatch.setattr(fc, "fetch_firecrawl", _fake_fc)
    monkeypatch.setattr(R, "fetch_firecrawl", _fake_fc)
    monkeypatch.setattr(R, "firecrawl_sdk_available", lambda: True)
    monkeypatch.setattr(R, "firecrawl_cli_available", lambda: False)
    monkeypatch.setattr(R, "firecrawl_configured", lambda: True)
    monkeypatch.setattr(R, "playwright_available", lambda: False)

    mi = {
        "allow_network": True,
        "fetch": {
            "prefer": "firecrawl",
            "cache_dir": str(tmp_path / "c"),
            "cache_ttl_hours": 6,
            "timeout_s": 5,
            "min_interval_ms_per_host": 0,
        },
        "circuit_break_failures": 99,
    }
    lim = RateLimitCircuit(min_interval_ms=0, failure_threshold=99, open_seconds=1)
    b = R.fetch_match_bundle(
        "https://example.com/alpha-vs-beta",
        mi_cfg=mi,
        match_key="alpha_fc_vs_beta_united",
        limiter=lim,
        force=True,
    )
    assert b.ok is True
    assert b.method == "firecrawl"

    # Second call hits cache
    b2 = R.fetch_match_bundle(
        "https://example.com/alpha-vs-beta",
        mi_cfg=mi,
        match_key="alpha_fc_vs_beta_united",
        limiter=lim,
        force=False,
    )
    assert b2.ok is True
    assert b2.method == "cache"


def test_pipeline_live_parse_after_fetch(monkeypatch, tmp_path: Path):
    """allow_network + url → fetch+match → live parse (football ready=True).

    Thin page without form widgets → parse_empty / grade F (not live_parser_not_ready).
    """
    from nt.match_intel.fetch import router as R

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html=(
                "<html><title>Rosenborg vs Fredrikstad | Eliteserien</title>"
                "<body>Rosenborg vs Fredrikstad preview content</body></html>"
            ),
            markdown="# Rosenborg vs Fredrikstad",
            duration_ms=2,
            page_meta={
                "title": "Rosenborg vs Fredrikstad | Eliteserien",
                "home_name": "Rosenborg",
                "away_name": "Fredrikstad",
            },
        )

    monkeypatch.setattr(R, "fetch_match_bundle", _fake_bundle)

    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "allow_network": True,
                "ttl_hours": 0,
                "fetch": {
                    "prefer": "firecrawl",
                    "cache_dir": str(tmp_path / "fetch_cache"),
                    "cache_ttl_hours": 6,
                },
            }
        }
    }
    card = build_match_intel(
        "Rosenborg vs Fredrikstad",
        sport="football",
        cfg=cfg,
        url="https://www.flashscore.com/match/rosenborg-fredrikstad/",
        allow_network=True,
        write=True,
        out_dir=tmp_path,
        force=True,
    )
    ext = card["extraction"]
    # PR-3: parser is ready — must not emit live_parser_not_ready
    assert "live_parser_not_ready" not in (ext.get("errors") or [])
    assert ext.get("match_confidence") in ("exact", "alias", "fuzzy")
    # Thin content → still low grade; process miss via parse_empty (not no_source)
    assert card["coverage"]["grade"] in ("F", "D", "C")
    assert "no_source" not in (ext.get("errors") or [])
    assert "network_disabled" not in (ext.get("errors") or [])
    if card["coverage"]["grade"] == "F":
        assert ext.get("process_miss") is True
        assert (
            ext.get("process_miss_reason") in ("parse_empty", "low_name_match", "fetch_failed")
            or "parse_empty" in (ext.get("errors") or [])
        )


def test_pipeline_url_not_found_when_network_no_url(tmp_path: Path):
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "allow_network": True,
                "ttl_hours": 0,
            }
        }
    }
    card = build_match_intel(
        "Alpha vs Beta",
        sport="football",
        cfg=cfg,
        url=None,
        allow_network=True,
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    assert "url_not_found" in card["extraction"]["errors"]
    assert card["extraction"]["process_miss"] is True


def test_pipeline_offline_unchanged(tmp_path: Path):
    """allow_network false still network_disabled without fixtures."""
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "allow_network": False,
            }
        }
    }
    card = build_match_intel(
        "Unknown FC vs Nowhere United",
        sport="football",
        cfg=cfg,
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    assert "network_disabled" in card["extraction"]["errors"]
    assert card["coverage"]["grade"] == "F"


def test_playwright_missing_clear_error(monkeypatch):
    from nt.match_intel.fetch import playwright_fetch as pw

    monkeypatch.setattr(pw, "playwright_available", lambda: False)
    b = pw.fetch_playwright("https://www.flashscore.com/match/x")
    assert b.ok is False
    assert b.error == "playwright_not_installed"


def test_http_fetch_offline_style_html_local(monkeypatch, tmp_path: Path):
    """http backend without network: mock urllib/httpx path via monkeypatch."""
    from nt.match_intel.fetch import http_fetch as H

    html = (
        "<html><head><title>Gamma vs Delta | Test</title></head>"
        "<body>" + ("match preview " * 30) + "</body></html>"
    )

    class _Resp:
        status_code = 200
        url = "https://static.example/g-vs-d"
        encoding = "utf-8"
        content = html.encode("utf-8")

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return _Resp()

    class _httpx:
        Client = _Client

    monkeypatch.setattr(H, "httpx_available", lambda: True)
    monkeypatch.setitem(sys.modules, "httpx", _httpx)

    b = H.fetch_http("https://static.example/g-vs-d", timeout_s=5)
    assert b.ok is True
    assert b.method == "http"
    assert b.page_meta.get("home_name") == "Gamma"


def test_registry_football_ready():
    from nt.match_intel.registry import get_live_parser, is_live_parser_ready

    assert is_live_parser_ready("football") is True
    spec = get_live_parser("football")
    assert spec is not None
    assert spec.ready is True
    assert callable(spec.parse)
