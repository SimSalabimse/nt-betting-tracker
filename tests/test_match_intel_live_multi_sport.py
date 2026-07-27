"""
PR-5: multi-sport live parsers + capture fixtures (offline only).

esports (5a), snooker + darts (5b), baseball (5c):
- Registry ready=True; v1_sports includes all four (+ football, tennis)
- Golden fixtures → grade ≥ C
- Empty shell → grade F
- Pipeline network mock → not parser_not_implemented / live_parser_not_ready
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

from nt.match_intel.coverage import CRITICAL, OPTIONAL, critical_missing_count, key_credit
from nt.match_intel.fetch.bundle import MatchFetchBundle
from nt.match_intel.pipeline import build_match_intel, merge_fragments
from nt.match_intel.registry import get_live_parser, is_live_parser_ready
from nt.match_intel.schema import apply_process_miss, empty_mic_skeleton, finalize_coverage
from nt.match_intel.sources.baseball_live import parse_baseball_bundle, parse_baseball_live_html
from nt.match_intel.sources.darts_live import parse_darts_bundle, parse_darts_live_html
from nt.match_intel.sources.esports_live import parse_esports_bundle, parse_esports_live_html
from nt.match_intel.sources.snooker_live import parse_snooker_bundle, parse_snooker_live_html

LIVE = ROOT / "tests" / "fixtures" / "match_intel" / "live"

SPORTS = ("esports", "snooker", "darts", "baseball")
V1_EXPECTED = ("football", "tennis", "esports", "snooker", "darts", "baseball")

FIXTURES: dict[str, dict[str, Any]] = {
    "esports": {
        "dir": LIVE / "esports" / "g2_vs_natus_vincere",
        "match": "G2 vs Natus Vincere",
        "parse_bundle": parse_esports_bundle,
        "parse_html": parse_esports_live_html,
        "form_mode": "form",
        "comp_substr": "ESL",
    },
    "snooker": {
        "dir": LIVE / "snooker" / "osullivan_vs_trump",
        "match": "O'Sullivan Ronnie vs Trump Judd",
        "parse_bundle": parse_snooker_bundle,
        "parse_html": parse_snooker_live_html,
        "form_mode": "form_or_rank",
        "comp_substr": "World",
    },
    "darts": {
        "dir": LIVE / "darts" / "van_gerwen_vs_littler",
        "match": "van Gerwen Michael vs Littler Luke",
        "parse_bundle": parse_darts_bundle,
        "parse_html": parse_darts_live_html,
        "form_mode": "form_or_rank",
        "comp_substr": "PDC",
    },
    "baseball": {
        "dir": LIVE / "baseball" / "yankees_vs_red_sox",
        "match": "New York Yankees vs Boston Red Sox",
        "parse_bundle": parse_baseball_bundle,
        "parse_html": parse_baseball_live_html,
        "form_mode": "form",
        "comp_substr": "MLB",
        "need_standings": True,
    },
}


def _load_bundle(match_dir: Path, *, match: str = "", sport: str = "") -> MatchFetchBundle:
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
            xhrs.append(json.loads(p.read_text(encoding="utf-8-sig")))
    home, away = "", ""
    if " vs " in match:
        home, away = [x.strip() for x in match.split(" vs ", 1)]
    return MatchFetchBundle(
        ok=True,
        url=f"https://www.flashscore.com/match/{sport or 'sport'}/{match_dir.name}/",
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


# ---------------------------------------------------------------------------
# Registry + config (KD-17)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sport", SPORTS)
def test_registry_ready(sport: str):
    assert is_live_parser_ready(sport) is True
    spec = get_live_parser(sport)
    assert spec is not None
    assert spec.ready is True
    assert callable(spec.parse)
    assert "flashscore" in (spec.sources or [])


def test_config_v1_sports_includes_multi_sport():
    """KD-17: new sports join v1_sports only with registry ready=True (same PR)."""
    cfg_path = ROOT / "config.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    v1 = (data.get("research") or {}).get("match_intel") or {}
    sports = [str(s).lower() for s in (v1.get("v1_sports") or [])]
    for sp in V1_EXPECTED:
        assert sp in sports, f"{sp} missing from v1_sports"
    for sp in sports:
        assert is_live_parser_ready(sp), f"{sp} in v1_sports must be ready=True"


def test_coverage_keys_snooker_darts_baseball():
    assert CRITICAL["snooker"] == [
        "form_or_rank_home",
        "form_or_rank_away",
        "competition",
    ]
    assert CRITICAL["darts"] == [
        "form_or_rank_home",
        "form_or_rank_away",
        "competition",
    ]
    assert CRITICAL["baseball"] == [
        "form_home",
        "form_away",
        "competition",
        "standings_or_rank",
    ]
    assert CRITICAL["esports"] == ["form_home", "form_away", "competition"]
    assert "h2h" in OPTIONAL["snooker"]
    assert "h2h" in OPTIONAL["darts"]
    assert "h2h" in OPTIONAL["baseball"]
    assert "ranking_or_rating" in OPTIONAL["esports"]


# ---------------------------------------------------------------------------
# Live HTML + golden bundle grades
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sport", SPORTS)
def test_live_html_extracts_form_and_competition(sport: str):
    meta = FIXTURES[sport]
    html = (meta["dir"] / "summary.html").read_text(encoding="utf-8")
    frag = meta["parse_html"](html, match=meta["match"])
    assert frag["competition"].get("name")
    assert meta["comp_substr"].lower() in str(frag["competition"].get("name")).lower()
    home = frag["sides"]["home"]
    away = frag["sides"]["away"]
    assert home["recent_form"]["n"] >= 5
    assert away["recent_form"]["n"] >= 5
    assert set(home["recent_form"]["results"]) <= set("WDL")
    if meta["form_mode"] == "form_or_rank":
        assert home.get("standings", {}).get("rank") is not None
        assert away.get("standings", {}).get("rank") is not None
        assert "form_or_rank_home" in frag["fields_contributed"]
        assert "form_or_rank_away" in frag["fields_contributed"]
    else:
        assert "form_home" in frag["fields_contributed"]
        assert "form_away" in frag["fields_contributed"]
    if meta.get("need_standings"):
        assert home.get("standings", {}).get("rank") is not None
        assert away.get("standings", {}).get("rank") is not None
        assert "standings_or_rank" in frag["fields_contributed"]
    assert "competition" in frag["fields_contributed"]
    assert int((frag.get("h2h") or {}).get("n") or 0) >= 3


@pytest.mark.parametrize("sport", SPORTS)
def test_golden_bundle_grade_ge_c(sport: str):
    meta = FIXTURES[sport]
    bundle = _load_bundle(meta["dir"], match=meta["match"], sport=sport)
    frag = meta["parse_bundle"](bundle, match=meta["match"], sport=sport, cfg={})
    card = empty_mic_skeleton(meta["match"], sport=sport, errors=[])
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
    assert key_credit(card, "competition") == 1.0
    assert card["extraction"].get("process_miss") is False
    assert "parser_not_implemented" not in (card["extraction"].get("errors") or [])
    if meta["form_mode"] == "form_or_rank":
        assert key_credit(card, "form_or_rank_home") > 0
        assert key_credit(card, "form_or_rank_away") > 0
    else:
        assert key_credit(card, "form_home") > 0
        assert key_credit(card, "form_away") > 0
    if meta.get("need_standings"):
        assert key_credit(card, "standings_or_rank") == 1.0
        assert critical_missing_count(card) == 0


@pytest.mark.parametrize("sport", SPORTS)
def test_empty_shell_still_f(sport: str):
    shell = LIVE / sport / "empty_shell.html"
    html = shell.read_text(encoding="utf-8")
    meta = FIXTURES[sport]
    frag = meta["parse_html"](html, match="Alpha vs Beta")
    fields = frag.get("fields_contributed") or []
    assert "form_home" not in fields
    assert "form_or_rank_home" not in fields
    card = empty_mic_skeleton("Alpha vs Beta", sport=sport, errors=[])
    card["extraction"]["errors"] = []
    card = merge_fragments(card, frag)
    finalize_coverage(card)
    apply_process_miss(card)
    assert card["coverage"]["grade"] == "F"


# ---------------------------------------------------------------------------
# Pipeline path (network mocked)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sport", SPORTS)
def test_pipeline_live_path_parses(sport: str, monkeypatch, tmp_path: Path):
    from nt.match_intel.fetch import router as R

    meta = FIXTURES[sport]
    html = (meta["dir"] / "summary.html").read_text(encoding="utf-8")
    md = (meta["dir"] / "summary.md").read_text(encoding="utf-8")
    home, away = [x.strip() for x in meta["match"].split(" vs ", 1)]

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="firecrawl",
            html=html,
            markdown=md,
            page_meta={
                "title": f"{meta['match']} | Flashscore",
                "home_name": home,
                "away_name": away,
                "competition_hint": meta["comp_substr"],
            },
        )

    monkeypatch.setattr(R, "fetch_match_bundle", _fake_bundle)

    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": list(V1_EXPECTED),
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
        meta["match"],
        sport=sport,
        cfg=cfg,
        url=f"https://www.flashscore.com/match/{sport}/fixture/",
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
    assert ext.get("process_miss") is False


def test_pipeline_empty_fetch_parse_empty_not_stub(monkeypatch, tmp_path: Path):
    from nt.match_intel.fetch import router as R

    shell = (LIVE / "esports" / "empty_shell.html").read_text(encoding="utf-8")

    def _fake_bundle(url: str, **kwargs: Any) -> MatchFetchBundle:
        return MatchFetchBundle(
            ok=True,
            url=url,
            method="http",
            html=shell,
            page_meta={
                "title": "G2 vs Natus Vincere",
                "home_name": "G2",
                "away_name": "Natus Vincere",
            },
        )

    monkeypatch.setattr(R, "fetch_match_bundle", _fake_bundle)
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": list(V1_EXPECTED),
                "out_dir": str(tmp_path),
                "allow_network": True,
                "ttl_hours": 0,
                "fetch": {"prefer": "http", "cache_dir": str(tmp_path / "fc")},
            }
        }
    }
    card = build_match_intel(
        "G2 vs Natus Vincere",
        sport="esports",
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
    assert "parse_empty" in errs or card["coverage"]["grade"] == "F"
    assert card["coverage"]["grade"] == "F"


def test_sport_still_stub_when_not_in_v1(tmp_path: Path):
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
        "G2 vs Natus Vincere",
        sport="esports",
        cfg=cfg,
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    assert "parser_not_implemented" in (card["extraction"].get("errors") or [])
    assert card["extraction"].get("process_miss") is True
