"""
MIC URL discovery unit tests — offline only (fixtures + mocks; no live network).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.match_intel.discovery import (
    build_flashscore_search_url,
    build_search_query,
    discover_match_url,
    load_alias_store,
    lookup_alias_url,
    parse_flashscore_search_results,
    rank_candidates,
    save_alias_store,
    upsert_alias,
)
from nt.match_intel.fetch.bundle import MatchFetchBundle
from nt.match_intel.pipeline import build_match_intel, run_match_intel_batch

FIXTURES = ROOT / "tests" / "fixtures" / "match_intel"
SEARCH_HTML = (FIXTURES / "flashscore_search_rosenborg.html").read_text(encoding="utf-8")


def test_build_flashscore_search_url():
    url = build_flashscore_search_url("Rosenborg vs Fredrikstad")
    assert "flashscore.com" in url
    assert "/search/" in url
    assert "q=" in url
    assert "Rosenborg" in url or "Rosenborg" in build_search_query("Rosenborg vs Fredrikstad")
    q = build_search_query("Rosenborg vs Fredrikstad")
    assert "Rosenborg" in q and "Fredrikstad" in q


def test_parse_flashscore_search_html_fixture():
    cands = parse_flashscore_search_results(SEARCH_HTML)
    assert len(cands) >= 2
    urls = [c.url for c in cands]
    assert any("rosenborg" in u.lower() and "fredrikstad" in u.lower() for u in urls)
    # Absolute + relative normalized
    assert all(u.startswith("https://") for u in urls)
    # No tennis/static noise
    assert not any("/tennis/" in u for u in urls)


def test_parse_flashscore_search_markdown():
    md = """
# Search
[Rosenborg vs Fredrikstad](https://www.flashscore.com/match/football/rbk-1/ffk-2/)
[Other FC vs Someone](/match/football/other-3/someone-4/)
"""
    cands = parse_flashscore_search_results(md)
    assert len(cands) >= 2
    labels = [c.label().lower() for c in cands]
    assert any("rosenborg" in x for x in labels)


def test_rank_candidates_confidence_gate():
    cands = parse_flashscore_search_results(SEARCH_HTML)
    ranked = rank_candidates(
        "Rosenborg vs Fredrikstad",
        cands,
        min_score=0.85,
    )
    assert ranked.ok is True
    assert ranked.confidence in ("exact", "alias", "fuzzy")
    assert ranked.score >= 0.85 or ranked.confidence in ("exact", "alias")
    assert ranked.url and "match" in ranked.url

    # Unrelated match should fail gate
    bad = rank_candidates("Alpha United vs Zeta City", cands, min_score=0.85)
    assert bad.ok is False
    assert bad.error == "url_not_found"


def test_alias_load_save_upsert(tmp_path: Path):
    path = tmp_path / "match_aliases.json"
    save_alias_store(path, {"aliases": []})
    store = load_alias_store(path)
    assert store["aliases"] == []

    row = upsert_alias(
        path,
        match="Rosenborg vs Fredrikstad",
        url="https://www.flashscore.com/match/football/rbk/ffk/",
        sport="football",
        confidence="exact",
    )
    assert row["odds_match"] == "Rosenborg vs Fredrikstad"
    store2 = load_alias_store(path)
    assert len(store2["aliases"]) == 1
    hit = lookup_alias_url("Rosenborg vs Fredrikstad", store2["aliases"], sport="football")
    assert hit is not None
    assert "flashscore.com" in hit["url"]

    # Upsert same match updates in place
    upsert_alias(
        path,
        match="Rosenborg vs Fredrikstad",
        url="https://www.flashscore.com/match/football/rbk/ffk/v2/",
        sport="football",
        confidence="fuzzy",
    )
    store3 = load_alias_store(path)
    assert len(store3["aliases"]) == 1
    assert store3["aliases"][0]["url"].endswith("/v2/")


def test_discover_from_alias_offline(tmp_path: Path):
    path = tmp_path / "aliases.json"
    upsert_alias(
        path,
        match="Rosenborg vs Fredrikstad",
        url="https://www.flashscore.com/match/football/rbk/ffk/",
        sport="football",
        confidence="exact",
    )
    mi = {"alias_path": str(path), "allow_network": False}
    res = discover_match_url(
        "Rosenborg vs Fredrikstad",
        sport="football",
        mi_cfg=mi,
        allow_network=False,
    )
    assert res.ok is True
    assert res.source == "alias"
    assert res.confidence == "alias"
    assert res.url and res.url.startswith("http")


def test_discover_from_search_fixture_offline():
    res = discover_match_url(
        "Rosenborg vs Fredrikstad",
        sport="football",
        mi_cfg={"allow_network": False, "min_match_score": 0.85},
        allow_network=False,
        search_html=SEARCH_HTML,
    )
    assert res.ok is True
    assert res.source == "search"
    assert res.confidence in ("exact", "alias", "fuzzy")
    assert res.url and "rosenborg" in res.url.lower()


def test_discover_writeback_high_confidence(tmp_path: Path):
    path = tmp_path / "aliases.json"
    save_alias_store(path, {"aliases": []})
    mi = {
        "alias_path": str(path),
        "write_aliases": True,
        "min_match_score": 0.85,
    }
    res = discover_match_url(
        "Rosenborg vs Fredrikstad",
        sport="football",
        mi_cfg=mi,
        allow_network=False,
        search_html=SEARCH_HTML,
        writeback=True,
    )
    assert res.ok is True
    store = load_alias_store(path)
    assert len(store["aliases"]) >= 1
    assert store["aliases"][0]["url"] == res.url


def test_discover_no_network_no_fixture_url_not_found():
    res = discover_match_url(
        "Unknown FC vs Nowhere United",
        sport="football",
        mi_cfg={"allow_network": False},
        allow_network=False,
    )
    assert res.ok is False
    assert res.error == "url_not_found"


def test_pipeline_discovery_then_live_parser_not_ready(monkeypatch, tmp_path: Path):
    """discover (fixture search) → fetch mock → live_parser_not_ready."""
    from nt.match_intel.fetch import router as R

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html=(
                "<html><title>Rosenborg vs Fredrikstad | Eliteserien</title>"
                "<body>Rosenborg vs Fredrikstad preview content enough text</body></html>"
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
                "min_match_score": 0.85,
                "alias_path": str(tmp_path / "aliases.json"),
                "fetch": {
                    "prefer": "firecrawl",
                    "cache_dir": str(tmp_path / "fetch_cache"),
                },
            }
        }
    }
    card = build_match_intel(
        "Rosenborg vs Fredrikstad",
        sport="football",
        cfg=cfg,
        url=None,  # force discovery
        allow_network=True,
        write=True,
        out_dir=tmp_path,
        force=True,
        search_html=SEARCH_HTML,
    )
    ext = card["extraction"]
    assert "live_parser_not_ready" in (ext.get("errors") or [])
    assert ext.get("match_confidence") in ("exact", "alias", "fuzzy")
    assert ext.get("discovery_source") == "search"
    assert "url_not_found" not in (ext.get("errors") or [])
    assert "no_source" not in (ext.get("errors") or [])


def test_pipeline_skips_discovery_when_url(monkeypatch, tmp_path: Path):
    from nt.match_intel import discovery as D
    from nt.match_intel.fetch import router as R

    called = {"discover": 0}

    def _no_discover(*a, **k):
        called["discover"] += 1
        raise AssertionError("discover_match_url should not run when --url set")

    monkeypatch.setattr(D, "discover_match_url", _no_discover)
    # Also patch import path used by pipeline
    monkeypatch.setattr(
        "nt.match_intel.pipeline.discover_match_url",
        _no_discover,
    )

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="http",
            html="<html><title>Alpha vs Beta</title><body>Alpha vs Beta content</body></html>",
            page_meta={"home_name": "Alpha", "away_name": "Beta", "title": "Alpha vs Beta"},
        )

    monkeypatch.setattr(R, "fetch_match_bundle", _fake_bundle)

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
        url="https://www.flashscore.com/match/football/alpha/beta/",
        allow_network=True,
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    assert called["discover"] == 0
    assert card["extraction"].get("discovery_source") == "cli_url"
    assert "live_parser_not_ready" in card["extraction"]["errors"]


def test_pipeline_url_not_found_when_network_no_discovery(tmp_path: Path):
    """allow_network + no url + no fixtures + no backends → url_not_found (no sockets)."""
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "allow_network": True,
                "ttl_hours": 0,
                "alias_path": str(tmp_path / "empty_aliases.json"),
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


def test_batch_discovery_metrics(monkeypatch, tmp_path: Path):
    from nt.match_intel.fetch import router as R

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        # Extract teams from URL path roughly
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html=(
                "<html><title>Rosenborg vs Fredrikstad</title>"
                "<body>Rosenborg Fredrikstad</body></html>"
            ),
            page_meta={
                "home_name": "Rosenborg",
                "away_name": "Fredrikstad",
                "title": "Rosenborg vs Fredrikstad",
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
                "max_board_matches": 5,
            }
        }
    }
    payload = run_match_intel_batch(
        cfg,
        matches=["Rosenborg vs Fredrikstad", "Molde vs Brann"],
        sport="football",
        allow_network=True,
        force=True,
        write=False,
        out_dir=tmp_path,
        search_html_by_match={
            "rosenborg_vs_fredrikstad": SEARCH_HTML,
            # Molde present in fixture → may resolve
            "molde_vs_brann": SEARCH_HTML,
        },
    )
    summary = payload["summary"]
    assert summary["discovery_attempted_n"] == 2
    assert summary["discovery_resolved_n"] >= 1
    assert summary.get("discovery_resolved_rate") is not None
    assert summary["discovery_resolved_rate"] >= 0.4  # gate ≥40% on this tiny work set


def test_committed_alias_scaffold_shape():
    """Repo scaffold is list-friendly for load_aliases / load_alias_store."""
    path = ROOT / "data" / "state" / "match_aliases.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "aliases" in data
    assert isinstance(data["aliases"], list)
