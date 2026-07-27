"""Quality hard_veto pack mutation + assert-can-bet (PR3)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.odds_common import evidence_pair_key
from nt.research_quality_gate import (
    HARD_VETO_REASONS,
    apply_quality_veto,
    assert_can_bet_exit_code,
    assert_can_bet_snapshot,
    build_data_coverage,
    evidence_pair_key_str,
    is_already_hard_vetoed,
    mutate_pack_hard_veto,
    resolve_evidence_pack_path,
    validate_hard_veto_reasons,
)


def _cfg(tmp_path: Path) -> dict:
    cfg = load_config()
    cfg = {**cfg, "paths": {**(cfg.get("paths") or {})}}
    cfg["paths"]["evidence"] = str(tmp_path / "evidence")
    cfg["paths"]["outbox"] = str(tmp_path / "outbox")
    cfg["paths"]["state_dir"] = str(tmp_path / "state")
    (tmp_path / "evidence").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return cfg


def _write_pack(
    evidence_dir: Path,
    *,
    match: str,
    selection: str,
    p_model: float = 0.58,
    filename: str | None = None,
) -> Path:
    fname = filename or f"{match.replace(' ', '_')}_{selection.replace(' ', '_')}.json"
    path = evidence_dir / fname
    pack = {
        "match": match,
        "selection": selection,
        "p_model": p_model,
        "summary": "Test pack with enough summary text.",
        "failure_modes": "late equalizer",
        "sources": [{"url": "https://example.com", "takeaway": "form solid last five"}],
        "sport": "football",
    }
    path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    return path


def test_hard_veto_reasons_closed_enum():
    assert "mic_grade_D" in HARD_VETO_REASONS
    assert "made_up_reason" not in HARD_VETO_REASONS
    valid, unknown = validate_hard_veto_reasons(["mic_grade_D", "not_a_reason"])
    assert valid == ["mic_grade_D"]
    assert unknown == ["not_a_reason"]


def test_resolve_mirrors_evidence_pair_key(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ev = Path(cfg["paths"]["evidence"])
    # Pack uses slightly different selection spelling; soft key should still resolve
    path = _write_pack(
        ev,
        match="Home FC vs Away United",
        selection="Vinner: Home FC",
        p_model=0.61,
        filename="home_win.json",
    )
    # Candidate-style selection (to win)
    resolved = resolve_evidence_pack_path(
        "Home FC vs Away United",
        "Home FC to Win",
        ev,
    )
    assert resolved is not None
    assert resolved.resolve() == path.resolve()
    # exact key
    resolved_exact = resolve_evidence_pack_path(
        "Home FC vs Away United",
        "Vinner: Home FC",
        ev,
    )
    assert resolved_exact is not None
    assert resolved_exact.resolve() == path.resolve()
    # pair key string form
    assert "||" in evidence_pair_key_str("Home FC vs Away United", "Home FC to Win")
    assert evidence_pair_key("A vs B", "X") == (
        evidence_pair_key("a vs b", "x")[0],
        evidence_pair_key("A vs B", "X")[1],
    )


def test_apply_hard_veto_nulls_p_model(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ev = Path(cfg["paths"]["evidence"])
    path = _write_pack(ev, match="A vs B", selection="Over 2.5", p_model=0.62)
    day = "2026-07-27"
    veto = {
        "schema_version": 1,
        "date": day,
        "vetoes": [
            {
                "match": "A vs B",
                "selection": "Over 2.5",
                "evidence_pair_key_str": evidence_pair_key_str("A vs B", "Over 2.5"),
                "action": "hard_veto",
                "reasons": ["mic_grade_D"],
            }
        ],
        "demotes": [],
    }
    veto_path = Path(cfg["paths"]["outbox"]) / f"quality_veto_{day}.json"
    veto_path.write_text(json.dumps(veto, indent=2) + "\n", encoding="utf-8")

    result = apply_quality_veto(cfg, day, dry_run=False)
    assert result["ok"] is True
    assert result["n_applied"] == 1
    assert result["n_unresolved"] == 0

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["p_model"] is None
    assert data["research_quality"]["action"] == "hard_veto"
    assert data["research_quality"]["prior_p_model"] == 0.62
    assert "mic_grade_D" in data["research_quality"]["reasons"]

    # recommend path would miss p_model: pack no longer placeable via attach
    assert data.get("p_model") is None


def test_zero_veto_still_writes_applied_marker(tmp_path: Path):
    cfg = _cfg(tmp_path)
    day = "2026-07-27"
    veto = {"schema_version": 1, "date": day, "vetoes": [], "demotes": []}
    veto_path = Path(cfg["paths"]["outbox"]) / f"quality_veto_{day}.json"
    veto_path.write_text(json.dumps(veto, indent=2) + "\n", encoding="utf-8")

    result = apply_quality_veto(cfg, day, dry_run=False)
    assert result["ok"] is True
    assert result["n_applied"] == 0
    applied = Path(cfg["paths"]["outbox"]) / f"quality_veto_applied_{day}.json"
    assert applied.is_file()
    marker = json.loads(applied.read_text(encoding="utf-8"))
    assert marker["n_vetoes"] == 0
    assert marker["n_applied"] == 0
    assert marker["date"] == day


def test_unknown_reason_rejected(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ev = Path(cfg["paths"]["evidence"])
    path = _write_pack(ev, match="A vs B", selection="BTTS Ja", p_model=0.55)
    day = "2026-07-27"
    veto = {
        "schema_version": 1,
        "date": day,
        "vetoes": [
            {
                "match": "A vs B",
                "selection": "BTTS Ja",
                "action": "hard_veto",
                "reasons": ["llm_vibes_bad"],  # not in closed enum
            }
        ],
        "demotes": [],
    }
    with pytest.warns(UserWarning, match="unknown"):
        result = apply_quality_veto(cfg, day, veto_doc=veto, dry_run=False)
    assert result["n_rejected"] == 1
    assert result["n_applied"] == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["p_model"] == 0.55  # unchanged


def test_idempotent_re_apply(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ev = Path(cfg["paths"]["evidence"])
    path = _write_pack(ev, match="X vs Y", selection="Under 2.5", p_model=0.57)
    day = "2026-07-27"
    veto = {
        "schema_version": 1,
        "date": day,
        "vetoes": [
            {
                "match": "X vs Y",
                "selection": "Under 2.5",
                "action": "hard_veto",
                "reasons": ["evidence_quality_insufficient"],
            }
        ],
        "demotes": [],
    }
    r1 = apply_quality_veto(cfg, day, veto_doc=veto, dry_run=False)
    assert r1["n_applied"] == 1
    data1 = json.loads(path.read_text(encoding="utf-8"))
    assert data1["p_model"] is None
    assert is_already_hard_vetoed(data1)

    r2 = apply_quality_veto(cfg, day, veto_doc=veto, dry_run=False)
    assert r2["n_applied"] == 0
    assert r2["n_idempotent_skip"] == 1
    data2 = json.loads(path.read_text(encoding="utf-8"))
    assert data2["research_quality"]["prior_p_model"] == 0.57  # not overwritten with null


def test_dry_run_no_mutation_no_marker(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ev = Path(cfg["paths"]["evidence"])
    path = _write_pack(ev, match="A vs B", selection="Over 2.5", p_model=0.60)
    day = "2026-07-27"
    veto = {
        "schema_version": 1,
        "date": day,
        "vetoes": [
            {
                "match": "A vs B",
                "selection": "Over 2.5",
                "action": "hard_veto",
                "reasons": ["opposite_side_thin"],
            }
        ],
    }
    result = apply_quality_veto(cfg, day, veto_doc=veto, dry_run=True)
    assert result["dry_run"] is True
    assert result["n_would_apply"] == 1
    assert result["applied_path"] is None
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["p_model"] == 0.60
    applied = Path(cfg["paths"]["outbox"]) / f"quality_veto_applied_{day}.json"
    assert not applied.exists()


def test_soft_key_resolve_on_apply(tmp_path: Path):
    """Veto row selection soft-matches pack selection via evidence_pair_key."""
    cfg = _cfg(tmp_path)
    ev = Path(cfg["paths"]["evidence"])
    path = _write_pack(
        ev,
        match="Merida vs Rival",
        selection="Vinner: Merida, Daniel",
        p_model=0.66,
        filename="merida.json",
    )
    day = "2026-07-27"
    veto = {
        "schema_version": 1,
        "date": day,
        "vetoes": [
            {
                "match": "Merida vs Rival",
                "selection": "Merida, Daniel to Win",
                "action": "hard_veto",
                "reasons": ["form_continuity_weak_flip"],
            }
        ],
    }
    result = apply_quality_veto(cfg, day, veto_doc=veto, dry_run=False)
    assert result["n_applied"] == 1
    assert result["n_unresolved"] == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["p_model"] is None


def test_assert_can_bet_exit_codes_temp_risk(tmp_path: Path):
    cfg = _cfg(tmp_path)
    risk_path = Path(cfg["paths"]["state_dir"]) / "risk.json"

    risk_path.write_text(
        json.dumps(
            {
                "can_bet": True,
                "remaining_risk_nok": 40.0,
                "stopped": False,
                "research_only": False,
                "reasons": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    snap_ok = assert_can_bet_snapshot(cfg, refresh=False)
    assert snap_ok["can_bet"] is True
    assert assert_can_bet_exit_code(snap_ok) == 0

    risk_path.write_text(
        json.dumps(
            {
                "can_bet": False,
                "remaining_risk_nok": 0.0,
                "stopped": True,
                "research_only": False,
                "reasons": ["KILL-SWITCH: today P/L -50.00 <= -40.00"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    snap_no = assert_can_bet_snapshot(cfg, refresh=False)
    assert snap_no["can_bet"] is False
    assert assert_can_bet_exit_code(snap_no) == 1
    assert snap_no["reasons"]


def test_mutate_pack_preserves_summary():
    pack = {"match": "A vs B", "selection": "X", "p_model": 0.5, "summary": "keep me"}
    out = mutate_pack_hard_veto(
        pack, reasons=["mic_missing"], veto_date="2026-07-27", resolved_path="evidence/a.json"
    )
    assert out["p_model"] is None
    assert out["summary"] == "keep me"
    assert out["research_quality"]["prior_p_model"] == 0.5


def test_build_data_coverage_helper():
    cov = build_data_coverage(
        mic_grade="B",
        both_sides=True,
        form=True,
        h2h=False,
        evidence_quality="adequate",
        evidence_quality_notes="thin h2h",
    )
    assert cov["mic_grade"] == "B"
    assert cov["evidence_quality"] == "adequate"
    assert cov["h2h"] is False
