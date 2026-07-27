"""
PR-3: football live parsers + capture fixtures (offline only).

- Live Flashscore HTML/markdown/XHR → grade ≥ C golden card
- Registry ready=True
- Empty shell still grade F / parse_empty
- process_miss cleared when real form present
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

from nt.match_intel.coverage import critical_missing_count, grade_card
from nt.match_intel.fetch.bundle import MatchFetchBundle
from nt.match_intel.pipeline import build_match_intel, merge_fragments
from nt.match_intel.registry import get_live_parser, is_live_parser_ready
from nt.match_intel.schema import apply_process_miss, empty_mic_skeleton, finalize_coverage
from nt.match_intel.sources.flashscore_live import (
    parse_flashscore_live_html,
    parse_flashscore_markdown,
    parse_flashscore_xhr,
    parse_football_bundle,
)

LIVE = ROOT / "tests" / "fixtures" / "match_intel" / "live" / "football"
RBK = LIVE / "rosenborg_vs_fredrikstad"
BSC = LIVE / "barcelona_sc_vs_ldu_quito"


def _load_bundle(match_dir: Path, *, match: str = "") -> MatchFetchBundle:
    summary = (match_dir / "summary.html").read_text(encoding="utf-8")
    md = ""
    if (match_dir / "summary.md").is_file():
        md = (match_dir / "summary.md").read_text(encoding="utf-8")
    h2h = ""
    if (match_dir / "h2h.html").is_file():
        h2h = (match_dir / "h2h.html").read_text(encoding="utf-8")
    xhrs: list[dict[str, Any]] = []
    xhr_dir = match_dir / "xhr"
    if xhr_dir.is_dir():
        for p in sorted(xhr_dir.glob("*.json")):
            xhrs.append(json.loads(p.read_text(encoding="utf-8")))
    home, away = "", ""
    if " vs " in match:
        home, away = [x.strip() for x in match.split(" vs ", 1)]
    return MatchFetchBundle(
        ok=True,
        url=f"https://www.flashscore.com/match/fixture/{match_dir.name}/",
        method="fixture",
        html=summary,
        markdown=md,
        xhrs=xhrs,
        resources={
            "summary_html": summary,
            "h2h_html": h2h or None,
            "markdown": md,
            "xhr_json": xhrs,
        },
        page_meta={
            "title": f"{home} vs {away}" if home else match_dir.name,
            "home_name": home,
            "away_name": away,
        },
    )


def test_registry_football_ready():
    assert is_live_parser_ready("football") is True
    spec = get_live_parser("football")
    assert spec is not None
    assert spec.ready is True
    assert callable(spec.parse)
    assert "flashscore" in (spec.sources or [])


def test_live_html_form_competition_standings():
    html = (RBK / "summary.html").read_text(encoding="utf-8")
    frag = parse_flashscore_live_html(html, match="Rosenborg vs Fredrikstad")
    assert frag["competition"].get("name")
    assert "Eliteserien" in str(frag["competition"].get("name"))
    home = frag["sides"]["home"]
    away = frag["sides"]["away"]
    assert home["recent_form"]["n"] >= 5
    assert away["recent_form"]["n"] >= 5
    assert set(home["recent_form"]["results"]) <= set("WDL")
    assert home.get("standings", {}).get("rank") == 2
    assert away.get("standings", {}).get("rank") == 7
    assert "form_home" in frag["fields_contributed"]
    assert "form_away" in frag["fields_contributed"]
    assert "competition" in frag["fields_contributed"]


def test_live_markdown_parse():
    md = (RBK / "summary.md").read_text(encoding="utf-8")
    frag = parse_flashscore_markdown(md, match="Rosenborg vs Fredrikstad")
    assert frag["competition"].get("name")
    assert frag["sides"]["home"]["recent_form"]["n"] >= 5
    assert frag["sides"]["away"]["recent_form"]["n"] >= 5
    assert frag["sides"]["home"].get("standings", {}).get("rank") == 2


def test_live_xhr_parse():
    data = json.loads((RBK / "xhr" / "summary.json").read_text(encoding="utf-8"))
    frag = parse_flashscore_xhr([data], match="Rosenborg vs Fredrikstad")
    assert frag["competition"].get("name") == "Eliteserien"
    assert frag["sides"]["home"]["recent_form"]["n"] >= 5
    assert frag["sides"]["home"]["standings"]["rank"] == 2
    assert frag["h2h"]["n"] >= 3


def test_parse_football_bundle_grade_ge_c():
    """Golden capture → merge + finalize → grade ≥ C (prefer B with n_miss 0)."""
    match = "Rosenborg vs Fredrikstad"
    bundle = _load_bundle(RBK, match=match)
    frag = parse_football_bundle(bundle, match=match, sport="football", cfg={})
    card = empty_mic_skeleton(match, sport="football", errors=[])
    card["extraction"]["errors"] = []
    card["extraction"]["primary_method"] = "fixture"
    card["extraction"]["match_confidence"] = "exact"
    card["extraction"]["needs_review"] = False
    card = merge_fragments(card, frag)
    finalize_coverage(card)
    apply_process_miss(card)
    grade = card["coverage"]["grade"]
    assert grade in ("A", "B", "C"), card["coverage"]
    assert critical_missing_count(card) <= 1
    # Rosenborg fixture is rich — aim n_miss == 0
    assert critical_missing_count(card) == 0
    assert grade in ("A", "B")
    assert card["extraction"].get("process_miss") is False
    assert card["sides"]["home"]["recent_form"]["n"] >= 3
    assert card["sides"]["away"]["recent_form"]["n"] >= 3


def test_second_fixture_grade_ge_c():
    match = "Barcelona SC vs LDU Quito"
    bundle = _load_bundle(BSC, match=match)
    frag = parse_football_bundle(bundle, match=match)
    card = empty_mic_skeleton(match, sport="football", errors=[])
    card["extraction"]["errors"] = []
    card["extraction"]["match_confidence"] = "exact"
    card["extraction"]["needs_review"] = False
    card = merge_fragments(card, frag)
    finalize_coverage(card)
    assert card["coverage"]["grade"] in ("A", "B", "C")
    assert critical_missing_count(card) <= 1
    assert card["competition"]["name"]


def test_empty_shell_still_f():
    html = (LIVE / "empty_shell.html").read_text(encoding="utf-8")
    frag = parse_flashscore_live_html(html, match="Alpha vs Beta")
    assert "form_home" not in (frag.get("fields_contributed") or [])
    card = empty_mic_skeleton("Alpha vs Beta", sport="football", errors=[])
    card["extraction"]["errors"] = []
    card = merge_fragments(card, frag)
    finalize_coverage(card)
    apply_process_miss(card)
    assert card["coverage"]["grade"] == "F"


def test_pipeline_live_path_parses_bundle(monkeypatch, tmp_path: Path):
    """allow_network + url → fetch mock with live HTML → grade ≥ C, not process_miss."""
    from nt.match_intel.fetch import router as R

    html = (RBK / "summary.html").read_text(encoding="utf-8")
    md = (RBK / "summary.md").read_text(encoding="utf-8")

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html=html,
            markdown=md,
            page_meta={
                "title": "Rosenborg vs Fredrikstad | Eliteserien | Flashscore",
                "home_name": "Rosenborg",
                "away_name": "Fredrikstad",
                "competition_hint": "Eliteserien",
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
    assert "live_parser_not_ready" not in (ext.get("errors") or [])
    assert "no_source" not in (ext.get("errors") or [])
    assert ext.get("match_confidence") in ("exact", "alias", "fuzzy")
    assert card["coverage"]["grade"] in ("A", "B", "C")
    assert critical_missing_count(card) <= 1
    # Real form present → process_miss cleared
    assert card["sides"]["home"]["recent_form"]["n"] >= 3
    assert ext.get("process_miss") is False
    assert ext.get("process_miss_reason") in ("", None)


def test_pipeline_empty_fetch_parse_empty(monkeypatch, tmp_path: Path):
    from nt.match_intel.fetch import router as R

    shell = (LIVE / "empty_shell.html").read_text(encoding="utf-8")

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="http",
            html=shell,
            page_meta={
                "title": "Rosenborg vs Fredrikstad",
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
            }
        }
    }
    card = build_match_intel(
        "Rosenborg vs Fredrikstad",
        sport="football",
        cfg=cfg,
        url="https://www.flashscore.com/match/x/",
        allow_network=True,
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    assert card["coverage"]["grade"] == "F"
    errs = card["extraction"].get("errors") or []
    # Empty live extract → parse_empty (not live_parser_not_ready)
    assert "live_parser_not_ready" not in errs
    assert "parse_empty" in errs or card["sides"]["home"]["recent_form"]["n"] == 0
    assert card["extraction"].get("process_miss") is True


def test_offline_data_star_still_works_via_bundle_fallback():
    """data-* offline fixture HTML still grades via live path fallback."""
    offline = (
        ROOT / "tests" / "fixtures" / "match_intel" / "barcelona_sc_vs_ldu_quito_flashscore.html"
    ).read_text(encoding="utf-8")
    bundle = MatchFetchBundle(
        ok=True,
        url="fixture://offline",
        method="fixture",
        html=offline,
        page_meta={"home_name": "Barcelona SC", "away_name": "LDU Quito"},
    )
    frag = parse_football_bundle(bundle, match="Barcelona SC vs LDU Quito")
    assert "form_home" in frag["fields_contributed"]
    assert frag["competition"].get("name") == "Liga Pro"


def test_fotmob_live_secondary():
    from nt.match_intel.sources.fotmob import parse_fotmob_live_content

    md = """
# Alpha FC vs Beta United
Competition: Test League
Home form: W W W D L
Away form: L D W W W
Alpha FC Rank: 1
Beta United Rank: 4
"""
    frag = parse_fotmob_live_content(html="", markdown=md, match="Alpha FC vs Beta United")
    assert "form_home" in frag["fields_contributed"]
    assert frag["competition"].get("name")
