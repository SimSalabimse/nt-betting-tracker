"""
MIC pipeline: atomic write, offline football HTML parse, non-football stubs.
No network required.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.match_intel.coverage import grade_card
from nt.match_intel.io import atomic_write_json, mic_path, read_mic, write_mic
from nt.match_intel.matching import fuzzy_token_jaccard, match_confidence, resolve_match
from nt.match_intel.pipeline import build_match_intel, run_match_intel_batch
from nt.match_intel.schema import mic_match_key
from nt.match_intel.sources.flashscore import parse_flashscore_html

FIXTURES = ROOT / "tests" / "fixtures" / "match_intel"


def test_atomic_write(tmp_path: Path):
    path = tmp_path / "out" / "card.json"
    obj = {"hello": "world", "n": 1}
    atomic_write_json(path, obj)
    assert path.is_file()
    assert not path.with_suffix(".json.tmp").exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == obj
    # overwrite
    atomic_write_json(path, {"hello": "again"})
    assert json.loads(path.read_text(encoding="utf-8"))["hello"] == "again"


def test_write_mic_path(tmp_path: Path):
    card = {
        "match_key": "alpha_vs_beta",
        "match": "Alpha vs Beta",
        "coverage": {"grade": "B", "score": 0.7},
    }
    p = write_mic(card, tmp_path)
    assert p == tmp_path / "alpha_vs_beta.json"
    assert read_mic(p)["match"] == "Alpha vs Beta"
    assert mic_path(tmp_path, "Alpha vs Beta").name == "alpha_vs_beta.json"


def test_offline_football_parse_fixture():
    html = (FIXTURES / "barcelona_sc_vs_ldu_quito_flashscore.html").read_text(encoding="utf-8")
    frag = parse_flashscore_html(html, match="Barcelona SC vs LDU Quito")
    assert frag["competition"].get("name") == "Liga Pro"
    home = frag["sides"]["home"]
    away = frag["sides"]["away"]
    assert home["recent_form"]["n"] >= 5
    assert away["recent_form"]["n"] >= 5
    assert home["standings"]["rank"] == 2
    assert away["standings"]["rank"] == 5
    assert "form_home" in frag["fields_contributed"]
    assert "h2h" in frag["fields_contributed"]
    assert frag["h2h"]["n"] >= 1


def test_build_match_intel_from_html_fixture(tmp_path: Path):
    html = (FIXTURES / "barcelona_sc_vs_ldu_quito_flashscore.html").read_text(encoding="utf-8")
    cfg = {
        "research": {
            "match_intel": {
                "enabled": True,
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "ttl_hours": 0,
                "allow_network": False,
            }
        }
    }
    card = build_match_intel(
        "Barcelona SC vs LDU Quito",
        sport="football",
        cfg=cfg,
        html_by_source={"flashscore": html},
        write=True,
        out_dir=tmp_path,
        force=True,
    )
    assert card["match_key"] == "barcelona_sc_vs_ldu_quito"
    cov = card["coverage"]
    assert cov["grade"] in ("A", "B")  # rich fixture should be high quality
    assert critical_missing_count_safe(card) == 0
    assert cov["score"] >= 0.60
    path = tmp_path / "barcelona_sc_vs_ldu_quito.json"
    assert path.is_file()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["coverage"]["grade"] == cov["grade"]
    # sources recorded
    assert any(s.get("publisher") == "flashscore" for s in card.get("sources") or [])


def critical_missing_count_safe(card: dict) -> int:
    from nt.match_intel.coverage import critical_missing_count

    return critical_missing_count(card)


def test_build_from_fixture_dir(tmp_path: Path):
    cfg = {"research": {"match_intel": {"v1_sports": ["football"], "out_dir": str(tmp_path)}}}
    card = build_match_intel(
        "Barcelona SC vs LDU Quito",
        sport="football",
        cfg=cfg,
        fixture_dir=FIXTURES,
        write=True,
        out_dir=tmp_path,
        force=True,
    )
    assert card["coverage"]["grade"] in ("A", "B", "C")
    assert card["competition"]["name"] == "Liga Pro"


def test_non_football_skeleton_parser_not_implemented(tmp_path: Path):
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
            }
        }
    }
    card = build_match_intel(
        "Djokovic vs Alcaraz",
        sport="tennis",
        cfg=cfg,
        write=True,
        out_dir=tmp_path,
        force=True,
    )
    assert "parser_not_implemented" in (card.get("extraction") or {}).get("errors", [])
    assert card["coverage"]["grade"] in ("F", "C", "D")
    assert (tmp_path / f"{mic_match_key('Djokovic vs Alcaraz')}.json").is_file()
    # PR-0: process_miss taxonomy
    ext = card["extraction"]
    assert ext.get("process_miss") is True
    assert ext.get("process_miss_reason") == "parser_not_implemented"


def test_football_no_source_grade_f(tmp_path: Path):
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
        write=True,
        out_dir=tmp_path,
        force=True,
    )
    assert "no_source" in card["extraction"]["errors"]
    assert card["coverage"]["grade"] == "F"
    ext = card["extraction"]
    assert ext.get("process_miss") is True
    # Prefer network_disabled when allow_network is false (still keeps no_source)
    assert ext.get("process_miss_reason") in ("network_disabled", "no_source")


def test_batch_matches(tmp_path: Path):
    html = (FIXTURES / "minimal_form_only.html").read_text(encoding="utf-8")
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "max_board_matches": 40,
            }
        }
    }
    key = mic_match_key("Alpha FC vs Beta United")
    payload = run_match_intel_batch(
        cfg,
        matches=["Alpha FC vs Beta United", "Someone vs Else"],
        sport="football",
        out_dir=tmp_path,
        force=True,
        html_by_source={key: {"flashscore": html}},
    )
    assert payload["ok"]
    assert payload["summary"]["n"] == 2
    grades = payload["summary"]["grades"]
    assert sum(grades.values()) == 2


def test_matching_exact_and_fuzzy():
    conf, score = match_confidence(
        "Barcelona SC vs LDU Quito", "Barcelona SC vs LDU Quito"
    )
    assert conf == "exact"
    assert score == 1.0

    conf2, score2 = match_confidence(
        "Barcelona SC vs LDU Quito", "Barcelona vs LDU Quito"
    )
    assert conf2 in ("exact", "fuzzy", "alias")
    assert score2 >= 0.85 or conf2 == "exact"

    conf3, _ = match_confidence("Alpha vs Beta", "Gamma vs Delta")
    assert conf3 == "none"

    j = fuzzy_token_jaccard("Bodø Glimt", "Bodo Glimt")
    assert j >= 0.5  # accent fold may vary; not none of tokens

    res = resolve_match(
        "Alpha FC vs Beta United",
        ["Gamma vs Delta", "Alpha FC vs Beta United"],
    )
    assert res["matched"]
    assert res["confidence"] == "exact"


def test_b_requires_n_miss_zero_in_grade_card():
    """Contract: grade B never with critical missing."""
    from nt.match_intel.coverage import CRITICAL, key_credit
    from nt.match_intel.schema import empty_mic_skeleton, side_dict

    card = empty_mic_skeleton("A vs B", sport="football", errors=[])
    card["extraction"]["primary_method"] = "test"
    card["extraction"]["errors"] = []
    card["competition"] = {"name": "L"}
    card["sides"]["home"] = side_dict(
        "A",
        recent_form={"n": 5, "results": list("WWWWW"), "scores": [], "summary": ""},
        standings={"rank": 1},
    )
    card["sides"]["away"] = side_dict("B")  # form missing
    g = grade_card(card)
    assert g["grade"] != "B"
    assert critical_missing_count_safe(card) >= 1


def test_process_miss_false_on_rich_offline_fixture(tmp_path: Path):
    """Successful offline HTML extract is not a process miss."""
    html = (FIXTURES / "barcelona_sc_vs_ldu_quito_flashscore.html").read_text(encoding="utf-8")
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
        "Barcelona SC vs LDU Quito",
        sport="football",
        cfg=cfg,
        html_by_source={"flashscore": html},
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    ext = card["extraction"]
    assert ext.get("process_miss") is False
    assert ext.get("process_miss_reason") in ("", None)
    assert card["coverage"]["grade"] in ("A", "B", "C")


def test_process_miss_thin_public_not_process_miss():
    from nt.match_intel.schema import apply_process_miss, empty_mic_skeleton

    card = empty_mic_skeleton("Thin vs Board", sport="football", errors=[])
    card["extraction"]["primary_method"] = "playwright_parse"
    card["extraction"]["errors"] = ["thin_public"]
    card["extraction"]["thin_public_confirmed"] = True
    apply_process_miss(card)
    assert card["extraction"]["process_miss"] is False
    assert card["extraction"]["process_miss_reason"] == "thin_public"


def test_kickoff_pass_through_from_batch(tmp_path: Path):
    """Batch must pass odds kickoff into build_match_intel → kickoff_local on card."""
    from nt.match_intel.pipeline import unique_matches_from_odds

    # Simulate unique_matches-style work items (what batch builds from odds)
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "allow_network": False,
                "max_board_matches": 10,
            }
        }
    }
    # Direct path: run_match_intel_batch with matches lacks kickoff; use build with
    # kickoff via internal work-list simulation (monkeypatch unique path).
    from nt.match_intel import pipeline as pipe

    work_items = [
        {
            "match": "Rosenborg vs Fredrikstad",
            "match_key": mic_match_key("Rosenborg vs Fredrikstad"),
            "sport": "football",
            "competition": None,
            "kickoff": "2026-07-27 18:00",
        }
    ]
    orig = pipe.unique_matches_from_odds

    def _fake_unique(*_a, **_k):
        return work_items

    pipe.unique_matches_from_odds = _fake_unique  # type: ignore[assignment]
    try:
        # odds_path truthy so batch uses unique_matches path
        odds_stub = tmp_path / "odds_stub.txt"
        odds_stub.write_text("placeholder\n", encoding="utf-8")
        # unique_matches is faked; parse_odds_file not called
        payload = run_match_intel_batch(
            cfg,
            odds_path=odds_stub,
            out_dir=tmp_path,
            force=True,
            write=True,
        )
    finally:
        pipe.unique_matches_from_odds = orig  # type: ignore[assignment]

    assert payload["ok"]
    assert payload["summary"]["n"] == 1
    card = payload["cards"][0]
    assert card.get("kickoff_local") == "2026-07-27 18:00"
    # process_miss still true (no offline HTML) but kickoff free field filled
    assert card["extraction"].get("process_miss") is True
    # batch index + summary instrumentation
    assert payload["summary"].get("process_miss_n") == 1
    assert "errors" in payload["summary"]
    assert isinstance(payload["summary"]["errors"], dict)
    index_path = payload["summary"].get("index_path")
    assert index_path
    idx = json.loads(Path(index_path).read_text(encoding="utf-8"))
    assert idx["n"] == 1
    assert idx["process_miss_n"] == 1
    assert "grades" in idx
    assert "errors" in idx


def test_kickoff_on_build_match_intel_direct(tmp_path: Path):
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
        "Alpha vs Beta",
        sport="football",
        cfg=cfg,
        kickoff="2026-08-01 20:00",
        write=False,
        out_dir=tmp_path,
        force=True,
    )
    assert card.get("kickoff_local") == "2026-08-01 20:00"


def test_batch_summary_process_miss_histogram(tmp_path: Path):
    cfg = {
        "research": {
            "match_intel": {
                "v1_sports": ["football"],
                "out_dir": str(tmp_path),
                "allow_network": False,
            }
        }
    }
    payload = run_match_intel_batch(
        cfg,
        matches=["A vs B", "C vs D"],
        sport="football",
        out_dir=tmp_path,
        force=True,
        write=True,
    )
    s = payload["summary"]
    assert s["n"] == 2
    assert s["process_miss_n"] == 2
    assert s["grades"]["F"] == 2
    assert s["errors"]  # at least network_disabled and/or no_source
    assert Path(s["index_path"]).is_file()
