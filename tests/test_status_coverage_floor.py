"""Coverage floor + temp_ev_relax section in generate_status / write_status."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.control_signals import emit_temp_ev_relax
from nt.status import (
    collect_coverage_floor_status,
    format_coverage_floor_section,
    generate_status,
    write_status,
)


def _minimal_cfg(tmp_path: Path) -> dict:
    state = tmp_path / "state"
    state.mkdir(parents=True, exist_ok=True)
    outbox = tmp_path / "outbox"
    (outbox / "light_research").mkdir(parents=True, exist_ok=True)
    bets = tmp_path / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,notes,source,created_at,updated_at\n",
        encoding="utf-8",
    )
    return {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "status": str(state / "status.md"),
            "outbox": str(outbox),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
        },
        "selection": {
            "high_odds_threshold": 2.5,
            "probability_haircut": 0.03,
            "standard_min_ev": 0.03,
        },
        "research": {
            "tiers": {
                "deep_target_n": 8,
                "deep_max_n": 15,
                "deep_target_dynamic": True,
                "deep_target_min": 8,
                "deep_target_max": 15,
                "deep_target_divisor": 8,
            },
            "coverage_floor": {
                "enabled": True,
                "top_promo_scaffold_pct": 0.20,
                "sport_rotation_min_lines": 5,
                "require_real_pack": True,
            },
        },
        "learning": {
            "control_signals": {
                "enabled": True,
                "temp_ev_relax": {
                    "enabled": True,
                    "delta_min": 0.01,
                    "delta_max": 0.02,
                    "ttl_hours": 24,
                    "stake_mult": 0.80,
                    "top_n_survivors": 3,
                    "min_board_matches": 15,
                    "require_coverage_warn": True,
                    "exclude_high_odds": True,
                    "exclude_grade_c": True,
                },
            }
        },
    }


def _bankroll() -> dict:
    return {
        "equity_nok": 500.0,
        "realized_pl_nok": 0.0,
        "baseline_nok": 500.0,
        "pending_at_risk_nok": 0.0,
        "liquid_nok": 500.0,
        "total_bets": 0,
        "era_archive_bets": 0,
        "post_archive_bets": 0,
        "updated_at": "2026-07-23T12:00:00Z",
    }


def _phase() -> dict:
    return {
        "phase_id": "1A",
        "label": "seed",
        "stake_min": 10,
        "stake_max": 15,
        "max_bets_per_round": 2,
        "max_doubles_per_round": 0,
        "rolling_roi": None,
    }


def _risk() -> dict:
    return {
        "daily_risk_cap_nok": 50.0,
        "formula": "test",
        "open_pending_risk_nok": 0.0,
        "remaining_risk_nok": 50.0,
        "today_realized_pl_nok": 0.0,
        "stop_day_loss_limit_nok": 40.0,
        "can_bet": True,
    }


def test_coverage_floor_section_when_temp_ev_relax_active(tmp_path: Path):
    cfg = _minimal_cfg(tmp_path)
    out = emit_temp_ev_relax(
        cfg,
        delta_ev=0.02,
        line_keys=["Match A vs B|Handikap -1.5: Away", "C vs D|Over 3.5"],
        force=True,
    )
    assert out["ok"] is True

    # light LATEST so deep_target can use shortlist size
    light = {
        "shortlist_n": 80,
        "deep_queue": [{"match": "x", "selection": "y"}],
        "deep_queue_composition": {"n": 1, "preferred_n": 1, "short_main_n": 0},
        "records": [
            {
                "match": "x",
                "selection": "y",
                "rough_ev_note": "promo | coverage_floor:top_promo_scaffold",
                "reason": "pass",
            },
            {
                "match": "h",
                "selection": "z",
                "rough_ev_note": "coverage_floor:sport_rotation",
                "reason": "pass",
            },
        ],
    }
    latest = Path(cfg["paths"]["outbox"]) / "light_research" / "LATEST.json"
    latest.write_text(json.dumps(light), encoding="utf-8")

    md = generate_status(cfg, _bankroll(), _phase(), _risk())
    assert "## Coverage floor" in md
    assert "temp_ev_relax" in md
    assert "active" in md
    assert "0.020" in md or "−0.020" in md or "-0.020" in md or "ΔEV" in md
    assert "line_keys=2" in md
    assert "deep_target_n_effective" in md
    # 80//8 = 10
    assert "10" in md
    assert "scaffold tags=1" in md
    assert "sport_rotation tags=1" in md
    assert "coverage_floor**: enabled" in md


def test_coverage_floor_section_inactive_relax(tmp_path: Path):
    cfg = _minimal_cfg(tmp_path)
    md = generate_status(cfg, _bankroll(), _phase(), _risk())
    assert "## Coverage floor" in md
    assert "temp_ev_relax**: inactive" in md
    assert "coverage_floor**: enabled" in md


def test_collect_coverage_floor_soft_fail_missing_files(tmp_path: Path):
    cfg = _minimal_cfg(tmp_path)
    # no light, no signals — still returns structure
    info = collect_coverage_floor_status(cfg)
    assert info.get("coverage_floor_enabled") is True
    assert info["temp_ev_relax"]["active"] is False
    section = format_coverage_floor_section(info)
    assert "Coverage floor" in section
    assert "inactive" in section


def test_write_status_includes_coverage_floor(tmp_path: Path):
    cfg = _minimal_cfg(tmp_path)
    emit_temp_ev_relax(
        cfg,
        delta_ev=0.015,
        line_keys=["Only|One"],
        force=True,
    )
    write_status(cfg, _bankroll(), _phase(), _risk())
    path = Path(cfg["paths"]["status"])
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "## Coverage floor" in text
    assert "temp_ev_relax" in text
    assert "active" in text
    assert "line_keys=1" in text
