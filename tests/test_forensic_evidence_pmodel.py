"""Dry-run evidence soft-match audit (no permanent writes in tests)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.forensic import CONF_EXACT, audit_evidence_pmodel, score_match


def test_score_match_exact():
    pack = {
        "match": "A vs B",
        "selection": "BTTS Ja",
        "path": Path("evidence/a.json"),
        "p_model": 0.6,
    }
    conf, method = score_match("A vs B", "BTTS Ja", pack)
    assert conf == CONF_EXACT
    assert method == "exact"


def test_score_match_no_false_market_mix():
    pack = {
        "match": "A vs B",
        "selection": "Over 2.5",
        "path": Path("evidence/a.json"),
        "p_model": 0.7,
        "sport": "football",
    }
    conf, method = score_match("A vs B", "Under 2.5", pack)
    # Must not exact-match opposite market
    assert conf < 0.85 or method != "exact"


def test_soft_match_v2_rejects_sport_mismatch():
    """Token-like soft matches across sports must not score > 0 under v2 gate."""
    from nt.forensic import soft_context_ok

    ok, reason = soft_context_ok(
        "baseball",
        "basketball",
        "Totalt 7.5 Over",
        "Vinner LA Clippers",
    )
    assert ok is False
    assert "sport_mismatch" in reason


def test_soft_match_v2_nba_basketball_alias_agree():
    """Phase 3: legacy nba label and basketball are the same sport bucket."""
    from nt.forensic import soft_context_ok

    ok, reason = soft_context_ok(
        "nba",
        "basketball",
        "Totalt 182.5 Over",
        "Totalt 182.5: Over 182.5",
    )
    assert ok is True, reason
    assert reason == "ok"

    pack = {
        "match": "Los Angeles Lakers vs LA Clippers",
        "selection": "Vinner (inkludert overtid/straffer): LA Clippers",
        "path": Path("evidence/clippers_win.json"),
        "p_model": 0.72,
        "sport": "basketball",
    }
    conf, method = score_match(
        "San Diego Padres vs Los Angeles Dodgers",
        "Totalt 7.5 (inkludert ekstra innings) Over",
        pack,
        bet_sport="baseball",
        require_soft_gate=True,
    )
    assert conf == 0.0
    assert method.startswith("rejected_") or method == "none"


def test_soft_match_v2_market_family_gate():
    from nt.forensic import soft_context_ok

    ok, reason = soft_context_ok(
        "tennis",
        "tennis",
        "Vinner: Darderi, Luciano",
        "Over 21.5 games",
    )
    assert ok is False
    assert "market_mismatch" in reason or "market_unknown" in reason


def test_audit_dry_run_no_write(tmp_path: Path, monkeypatch):
    from nt import forensic as fmod
    from nt.config import load_config

    cfg = load_config()
    # Point side-cars at tmp so even a bug cannot write real files
    cfg = dict(cfg)
    cfg["paths"] = dict(cfg["paths"])
    cfg["paths"]["decisions_jsonl"] = str(tmp_path / "dec.jsonl")
    cfg["paths"]["evidence_links_jsonl"] = str(tmp_path / "links.jsonl")

    monkeypatch.setattr(fmod, "decisions_path", lambda c: Path(c["paths"]["decisions_jsonl"]))
    monkeypatch.setattr(fmod, "evidence_links_path", lambda c: Path(c["paths"]["evidence_links_jsonl"]))
    # Still use real evidence + bets for meaningful match, but write targets are tmp
    from nt import decisions as dmod

    monkeypatch.setattr(dmod, "decisions_path", lambda c: Path(c["paths"]["decisions_jsonl"]))
    monkeypatch.setattr(dmod, "evidence_links_path", lambda c: Path(c["paths"]["evidence_links_jsonl"]))

    # Seed empty decisions so we don't depend on live densify state
    Path(cfg["paths"]["decisions_jsonl"]).write_text("", encoding="utf-8")

    report = audit_evidence_pmodel(cfg, dry_run=True, min_confidence=0.85)
    assert report["dry_run"] is True
    assert report["results"]["written"] == 0
    assert not Path(cfg["paths"]["decisions_jsonl"]).read_text(encoding="utf-8").strip()
    assert "coverage" in report
    assert report["min_confidence"] == 0.85
