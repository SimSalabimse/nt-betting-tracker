"""
PR-4: tennis live parsers + capture fixtures (offline only).

- Live Flashscore-like HTML/markdown/XHR → grade ≥ C (golden ≥ B with form)
- Registry tennis ready=True; v1_sports includes tennis
- Empty shell still grade F / parse_empty
- Not F with parser_not_implemented when tennis ∈ v1_sports
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.match_intel.coverage import critical_missing_count, key_credit
from nt.match_intel.fetch.bundle import MatchFetchBundle
from nt.match_intel.pipeline import build_match_intel, merge_fragments
from nt.match_intel.registry import get_live_parser, is_live_parser_ready
from nt.match_intel.schema import apply_process_miss, empty_mic_skeleton, finalize_coverage
from nt.match_intel.sources.tennis_live import (
    parse_tennis_bundle,
    parse_tennis_live_html,
    parse_tennis_markdown,
    parse_tennis_xhr,
)

LIVE = ROOT / "tests" / "fixtures" / "match_intel" / "live" / "tennis"
ARN = LIVE / "arnaldi_vs_musetti"
SIN = LIVE / "sinner_vs_medvedev"
MATCH_ARN = "Arnaldi Matteo vs Musetti Lorenzo"
MATCH_SIN = "Sinner Jannik vs Medvedev Daniil"


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
        url=f"https://www.flashscore.com/match/tennis/{match_dir.name}/",
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


def test_registry_tennis_ready():
    assert is_live_parser_ready("tennis") is True
    spec = get_live_parser("tennis")
    assert spec is not None
    assert spec.ready is True
    assert callable(spec.parse)
    assert "flashscore" in (spec.sources or [])


def test_config_v1_sports_includes_tennis():
    """KD-17: tennis joins v1_sports only with registry ready=True (same PR)."""
    cfg_path = ROOT / "config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    v1 = (data.get("research") or {}).get("match_intel") or {}
    sports = [str(s).lower() for s in (v1.get("v1_sports") or [])]
    assert "football" in sports
    assert "tennis" in sports
    for sp in sports:
        assert is_live_parser_ready(sp), f"{sp} in v1_sports must be ready=True"


def test_live_html_form_rank_competition_surface():
    html = (ARN / "summary.html").read_text(encoding="utf-8")
    frag = parse_tennis_live_html(html, match=MATCH_ARN)
    assert frag["competition"].get("name")
    assert "Hamburg" in str(frag["competition"].get("name")) or "ATP" in str(
        frag["competition"].get("name")
    )
    assert frag["competition"].get("format") == "clay"
    home = frag["sides"]["home"]
    away = frag["sides"]["away"]
    assert home["recent_form"]["n"] >= 5
    assert away["recent_form"]["n"] >= 5
    assert set(home["recent_form"]["results"]) <= set("WDL")
    assert home.get("standings", {}).get("rank") == 36
    assert away.get("standings", {}).get("rank") == 15
    assert "form_or_rank_home" in frag["fields_contributed"]
    assert "form_or_rank_away" in frag["fields_contributed"]
    assert "competition" in frag["fields_contributed"]
    assert "surface" in frag["fields_contributed"]
    assert int((frag.get("h2h") or {}).get("n") or 0) >= 3


def test_live_markdown_parse():
    md = (ARN / "summary.md").read_text(encoding="utf-8")
    frag = parse_tennis_markdown(md, match=MATCH_ARN)
    assert frag["competition"].get("name")
    assert frag["sides"]["home"]["recent_form"]["n"] >= 5
    assert frag["sides"]["away"]["recent_form"]["n"] >= 5
    assert frag["sides"]["home"].get("standings", {}).get("rank") == 36
    assert frag["competition"].get("format") == "clay"


def test_live_xhr_parse():
    data = json.loads((ARN / "xhr" / "summary.json").read_text(encoding="utf-8"))
    frag = parse_tennis_xhr([data], match=MATCH_ARN)
    assert "Hamburg" in str(frag["competition"].get("name")) or frag["competition"].get(
        "name"
    )
    assert frag["sides"]["home"]["recent_form"]["n"] >= 5
    assert frag["sides"]["home"]["standings"]["rank"] == 36
    assert frag["sides"]["away"]["standings"]["rank"] == 15
    assert frag["h2h"]["n"] >= 3
    assert frag["competition"].get("format") == "clay"


def test_parse_tennis_bundle_grade_ge_b():
    """Golden capture → grade ≥ B with form (prefer n_miss 0)."""
    bundle = _load_bundle(ARN, match=MATCH_ARN)
    frag = parse_tennis_bundle(bundle, match=MATCH_ARN, sport="tennis", cfg={})
    card = empty_mic_skeleton(MATCH_ARN, sport="tennis", errors=[])
    card["extraction"]["errors"] = []
    card["extraction"]["primary_method"] = "fixture"
    card["extraction"]["match_confidence"] = "exact"
    card["extraction"]["needs_review"] = False
    card = merge_fragments(card, frag)
    finalize_coverage(card)
    apply_process_miss(card)
    grade = card["coverage"]["grade"]
    assert grade in ("A", "B", "C"), card["coverage"]
    assert critical_missing_count(card) == 0
    assert grade in ("A", "B")
    assert key_credit(card, "form_or_rank_home") > 0
    assert key_credit(card, "form_or_rank_away") > 0
    assert key_credit(card, "competition") == 1.0
    assert card["extraction"].get("process_miss") is False
    assert card["sides"]["home"]["recent_form"]["n"] >= 3
    assert "parser_not_implemented" not in (card["extraction"].get("errors") or [])


def test_second_fixture_grade_ge_c():
    bundle = _load_bundle(SIN, match=MATCH_SIN)
    frag = parse_tennis_bundle(bundle, match=MATCH_SIN)
    card = empty_mic_skeleton(MATCH_SIN, sport="tennis", errors=[])
    card["extraction"]["errors"] = []
    card["extraction"]["match_confidence"] = "exact"
    card["extraction"]["needs_review"] = False
    card = merge_fragments(card, frag)
    finalize_coverage(card)
    assert card["coverage"]["grade"] in ("A", "B", "C")
    assert critical_missing_count(card) <= 1
    assert card["competition"]["name"]
    assert key_credit(card, "form_or_rank_home") > 0


def test_empty_shell_still_f():
    html = (LIVE / "empty_shell.html").read_text(encoding="utf-8")
    frag = parse_tennis_live_html(html, match="Alpha vs Beta")
    assert "form_or_rank_home" not in (frag.get("fields_contributed") or [])
    card = empty_mic_skeleton("Alpha vs Beta", sport="tennis", errors=[])
    card["extraction"]["errors"] = []
    card = merge_fragments(card, frag)
    finalize_coverage(card)
    apply_process_miss(card)
    assert card["coverage"]["grade"] == "F"


def test_pipeline_live_path_parses_tennis(monkeypatch, tmp_path: Path):
    """allow_network + url → fetch mock with live HTML → grade ≥ C, not parser_not_implemented."""
    from nt.match_intel.fetch import router as R

    html = (ARN / "summary.html").read_text(encoding="utf-8")
    md = (ARN / "summary.md").read_text(encoding="utf-8")

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html=html,
            markdown=md,
            page_meta={
                "title": "Arnaldi Matteo vs Musetti Lorenzo | ATP Hamburg | Flashscore",
                "home_name": "Arnaldi Matteo",
                "away_name": "Musetti Lorenzo",
                "competition_hint": "ATP Hamburg",
            },
        )

    monkeypatch.setattr(R, "fetch_match_bundle", _fake_bundle)

    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football", "tennis"],
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
        MATCH_ARN,
        sport="tennis",
        cfg=cfg,
        url="https://www.flashscore.com/match/arnaldi-musetti/",
        allow_network=True,
        write=True,
        out_dir=tmp_path,
        force=True,
    )
    ext = card["extraction"]
    assert "parser_not_implemented" not in (ext.get("errors") or [])
    assert "live_parser_not_ready" not in (ext.get("errors") or [])
    assert "no_source" not in (ext.get("errors") or [])
    assert ext.get("match_confidence") in ("exact", "alias", "fuzzy")
    assert card["coverage"]["grade"] in ("A", "B", "C")
    assert critical_missing_count(card) <= 1
    assert card["sides"]["home"]["recent_form"]["n"] >= 3
    assert ext.get("process_miss") is False


def test_pipeline_empty_fetch_parse_empty_not_stub(monkeypatch, tmp_path: Path):
    from nt.match_intel.fetch import router as R

    shell = (LIVE / "empty_shell.html").read_text(encoding="utf-8")

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="http",
            html=shell,
            page_meta={
                "title": "Arnaldi Matteo vs Musetti Lorenzo",
                "home_name": "Arnaldi Matteo",
                "away_name": "Musetti Lorenzo",
            },
        )

    monkeypatch.setattr(R, "fetch_match_bundle", _fake_bundle)
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football", "tennis"],
                "out_dir": str(tmp_path),
                "allow_network": True,
                "ttl_hours": 0,
                "fetch": {"prefer": "http", "cache_dir": str(tmp_path / "fc")},
            }
        }
    }
    card = build_match_intel(
        MATCH_ARN,
        sport="tennis",
        cfg=cfg,
        url="https://www.flashscore.com/match/x/",
        allow_network=True,
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    errs = card["extraction"].get("errors") or []
    assert "parser_not_implemented" not in errs
    assert "live_parser_not_ready" not in errs
    # Thin/empty extract → parse_empty (process miss), not product-gap stub
    assert "parse_empty" in errs or card["coverage"]["grade"] == "F"
    assert card["coverage"]["grade"] == "F"


def test_tennis_still_stub_when_not_in_v1(tmp_path: Path):
    """Sports outside v1_sports still get parser_not_implemented (product gap)."""
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
            }
        }
    }
    card = build_match_intel(
        MATCH_ARN,
        sport="tennis",
        cfg=cfg,
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    assert "parser_not_implemented" in (card["extraction"].get("errors") or [])
    assert card["extraction"].get("process_miss") is True
