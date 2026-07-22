"""
Phase 2.7 — enablement path integration tests.

Flag-off = legacy risk + sizing. Flag-on = full capital_v2 stack.
Default config remains disabled. Env override CAPITAL_V2_ENABLED works.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_runtime import capital_v2_enabled, unfreeze_capital
from nt.capital_segments import load_segments, save_segments, set_freeze
from nt.capital_v2 import capital_v2_cfg, compute_secure_transfer
from nt.config import load_config
from nt.portfolio import Candidate, build_portfolio
from nt.risk import evaluate_risk


PHASE = {
    "phase_id": "1A",
    "daily_risk_pct": 0.08,
    "daily_risk_floor": 30.0,
    "daily_risk_ceil": 42.0,
    "stake_min": 10,
    "stake_max": 12,
    "max_bets_per_round": 4,
    "max_doubles_per_round": 0,
}


def _cfg(tmp_path: Path, *, enabled: bool) -> dict:
    state = tmp_path / "state"
    state.mkdir(parents=True, exist_ok=True)
    bets = tmp_path / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,"
        "payout_nok,sport,market_type,odds_band,research_grade,phase,notes,"
        "source,created_at,updated_at\n",
        encoding="utf-8",
    )
    return {
        "paths": {
            "state_dir": str(state),
            "bets": str(bets),
            "capital_segments": str(state / "capital_segments.json"),
            "stake_decisions": str(state / "stake_decisions.jsonl"),
            "status": str(tmp_path / "status.md"),
            "bankroll_md": str(tmp_path / "bankroll.md"),
            "outbox": str(tmp_path / "outbox"),
            "evidence": str(tmp_path / "evidence"),
        },
        "bankroll": {"baseline_nok": 500.0},
        "norsk_tipping": {"min_stake_nok": 10},
        "capital_v2": {"enabled": enabled},
        "risk": {"stop_day_loss_pct_of_equity": 0.08, "stop_day_loss_floor_nok": 40},
        "learning": {"enabled": False},
        "selection": {
            "probability_haircut": 0.05,
            "standard_min_ev": 0.03,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.08,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {"min_sample": 99},
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
        },
    }


def test_default_live_config_capital_v2_policy():
    """Production policy (P0+): capital_v2 enabled in live config.yaml."""
    cfg = load_config()
    assert capital_v2_cfg(cfg).get("enabled") is True
    assert capital_v2_enabled(cfg) is True


def test_env_override_enables(monkeypatch, tmp_path):
    monkeypatch.setenv("CAPITAL_V2_ENABLED", "true")
    cfg = _cfg(tmp_path, enabled=False)
    # env wins even if config false
    assert capital_v2_cfg(cfg)["enabled"] is True
    monkeypatch.delenv("CAPITAL_V2_ENABLED", raising=False)
    assert capital_v2_cfg(cfg)["enabled"] is False


def test_flag_off_vs_on_risk_shape(tmp_path, monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    rows = []
    off = evaluate_risk(_cfg(tmp_path, enabled=False), 550.0, PHASE, rows)
    on = evaluate_risk(_cfg(tmp_path, enabled=True), 550.0, PHASE, rows)
    assert "size_mode" not in off
    assert on.get("capital_v2_enabled") is True
    assert on.get("size_mode") == "NORMAL"
    assert "portfolio_open_room_nok" in on
    assert off["can_bet"] is True
    assert on["can_bet"] is True


def test_flag_on_sizing_unit_not_phase_band(tmp_path):
    cfg = _cfg(tmp_path, enabled=True)
    risk = {
        "can_bet": True,
        "stopped": False,
        "remaining_risk_nok": 40.0,
        "size_mode": "NORMAL",
        "unit_size_nok": 10.0,
        "riskable_liquid_nok": 500.0,
        "capital_v2_enabled": True,
        "equity_nok": 500.0,
        "secure_nok": 0.0,
        "phase_id": "1A",
    }
    pack = {
        "p_model": 0.75,
        "summary": "test pack long enough for grade",
        "failure_modes": "fail mode text here",
        "context_risk": "low",
        "availability_status": "confirmed",
        "availability_notes": "ok",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": [
            {"url": f"https://ex.com/{i}", "takeaway": "ok", "kind": "stats"}
            for i in range(8)
        ],
        "odds_at_research": 1.85,
        "decimal_odds_ref": 1.85,
    }
    cands = [
        Candidate(
            date="2026-07-21",
            match="A vs B",
            selection="Vinner: A",
            decimal_odds=1.85,
            sport="darts",
            market_type="Vinner",
            p_model=0.75,
            evidence=pack,
        )
    ]
    picked, _ = build_portfolio(cfg, cands, PHASE, risk, historical_rows=[])
    assert len(picked) == 1
    # High-Volume v2: unit 10 × grade B mult 1.4 = 14 (not bare phase band)
    assert picked[0].stake_nok == 14.0
    assert picked[0].stake_decision is not None
    assert picked[0].stake_decision["size_mode"] == "NORMAL"


def test_unfreeze_clears_flag_and_audits(tmp_path):
    cfg = _cfg(tmp_path, enabled=True)
    segs = load_segments(cfg, baseline_nok=500.0)
    segs = set_freeze(segs, active=True, reason="dd_25pct")
    save_segments(cfg, segs)
    assert (load_segments(cfg).get("freeze") or {}).get("active") is True
    out = unfreeze_capital(cfg, reason="test", actor="pytest")
    assert out["ok"] is True
    assert out["was_frozen"] is True
    segs2 = load_segments(cfg)
    assert segs2["freeze"]["active"] is False
    assert len(segs2.get("freeze_audit") or []) >= 1


def test_secure_buffer_holds_after_enablement_path():
    r = compute_secure_transfer(
        ledger_equity=1000,
        secure_nok=0,
        ref_hwm=100,
        transfer_fraction=0.9,
        unit_size_nok=10.0,
        min_working_frac=0.55,
        min_working_units=8.0,
    )
    assert r.working_equity_after + 1e-9 >= 550.0
    assert r.secure_after <= 1000.0
