"""
Phase 2.4 — secure transfer, day/week snapshots, stake_decisions.jsonl.

Flag-off: no segment writes, no JSONL from capital path.
Flag-on: transfer + snapshots + audit append; idempotent secure math.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_runtime import (
    append_stake_decision,
    apply_secure_transfer_to_segments,
    capital_v2_enabled,
    ensure_day_week_snapshots,
    persist_stake_decisions_for_picks,
    stake_decisions_path,
    sync_capital_v2_state,
)
from nt.capital_segments import load_segments, segments_path
from nt.capital_v2 import empty_segments, riskable_liquid, unit_size
from nt.portfolio import Recommendation
from nt.recommend import refresh_state
from nt.risk import evaluate_risk


def _cfg(tmp_path: Path, *, enabled: bool) -> dict:
    state = tmp_path / "state"
    state.mkdir(parents=True, exist_ok=True)
    bets = tmp_path / "bets.csv"
    if not bets.is_file():
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
            "status": str(tmp_path / "status.md"),
            "bankroll_md": str(tmp_path / "bankroll.md"),
            "capital_segments": str(state / "capital_segments.json"),
            "stake_decisions": str(state / "stake_decisions.jsonl"),
            "outbox": str(tmp_path / "outbox"),
            "evidence": str(tmp_path / "evidence"),
        },
        "bankroll": {"baseline_nok": 500.0, "era_start": "2026-07-01"},
        "norsk_tipping": {"min_stake_nok": 10},
        "capital_v2": {
            "enabled": enabled,
            "secure_bucket": {
                "enabled": True,
                # Explicit Variant A (matches live defaults / asserted soft 15%)
                "variant": "A",
                "soft_trigger_multiple_of_ref": 1.25,
                "soft_transfer_fraction": 0.15,
                "hard_trigger_multiple_of_ref": 1.50,
                "hard_transfer_fraction": 0.30,
                "min_working_frac_of_equity": 0.55,
                "min_working_units": 8.0,
                "unlock_after_settled": 25,
                "manual_unlock_cooldown_days": 7,
            },
        },
        "risk": {"stop_day_loss_pct_of_equity": 0.08, "stop_day_loss_floor_nok": 40},
        "phases": {
            "1A": {
                "label": "Protect",
                "enter_equity": 0,
                "enter_settled": 0,
                "stake_min": 10,
                "stake_max": 12,
                "max_bets_per_round": 4,
                "max_doubles_per_round": 0,
                "daily_risk_pct": 0.08,
                "daily_risk_floor": 30,
                "daily_risk_ceil": 42,
                "next": "1B",
            }
        },
        "learning": {"enabled": False},
        "project": {"root": str(tmp_path)},
    }


PHASE = {
    "phase_id": "1A",
    "daily_risk_pct": 0.08,
    "daily_risk_floor": 30.0,
    "daily_risk_ceil": 42.0,
}


# ── flag-off ──────────────────────────────────────────────────────────────


def test_flag_off_sync_does_not_write_segments(tmp_path: Path):
    cfg = _cfg(tmp_path, enabled=False)
    assert capital_v2_enabled(cfg) is False
    segs = sync_capital_v2_state(cfg, 700.0, [], persist=True)
    assert segs["secure_nok"] == 0.0
    assert not segments_path(cfg).is_file()


def test_flag_off_refresh_no_capital_file(tmp_path: Path, monkeypatch):
    cfg = _cfg(tmp_path, enabled=False)
    # Minimal phase/bankroll deps
    from nt import recommend as rec_mod

    monkeypatch.setattr(
        rec_mod,
        "compute_bankroll",
        lambda c: {
            "equity_nok": 550.0,
            "settled_count": 0,
            "pending_stake_nok": 0.0,
        },
    )
    monkeypatch.setattr(rec_mod, "load_phase_state", lambda c: {"phase_id": "1A"})
    monkeypatch.setattr(
        rec_mod,
        "evaluate_phase",
        lambda *a, **k: {
            "phase_id": "1A",
            "daily_risk_pct": 0.08,
            "daily_risk_floor": 30,
            "daily_risk_ceil": 42,
            "label": "Protect",
        },
    )
    monkeypatch.setattr(rec_mod, "write_bankroll_state", lambda *a, **k: None)
    monkeypatch.setattr(rec_mod, "write_phase_state", lambda *a, **k: None)
    monkeypatch.setattr(rec_mod, "write_status", lambda *a, **k: None)

    bankroll, phase, risk = refresh_state(cfg)
    assert risk.get("capital_v2_enabled") is not True
    assert "size_mode" not in risk
    assert not segments_path(cfg).is_file()
    assert not stake_decisions_path(cfg).is_file()


# ── secure transfer ───────────────────────────────────────────────────────


def test_secure_transfer_variant_a_soft_and_ref_reset():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["unit_hwm_reset_equity_nok"] = 500.0
    segs["secure_nok"] = 0.0
    # Variant A soft: equity 700 ≥ 1.25×500=625, < 1.50×500=750 → 15% of 200 = 30
    out, info = apply_secure_transfer_to_segments(segs, ledger_equity=700.0)
    assert info["triggered"] is True
    assert info["tier"] == "soft"
    assert info["transferred"] == 30.0
    assert out["secure_nok"] == 30.0
    assert out["unit_hwm_reset_equity_nok"] == 670.0  # working equity after transfer
    assert len(out["secure_transfers"]) == 1


def test_secure_transfer_idempotent_after_reset():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["unit_hwm_reset_equity_nok"] = 500.0
    out1, info1 = apply_secure_transfer_to_segments(segs, ledger_equity=700.0)
    assert info1["triggered"] is True
    out2, info2 = apply_secure_transfer_to_segments(out1, ledger_equity=700.0)
    assert info2["triggered"] is False
    assert out2["secure_nok"] == out1["secure_nok"]
    assert len(out2["secure_transfers"]) == 1


def test_secure_skipped_when_frozen():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["unit_hwm_reset_equity_nok"] = 500.0
    segs["freeze"] = {
        "active": True,
        "reason": "test",
        "activated_at": "x",
        "unfreeze_requires": "manual",
    }
    out, info = apply_secure_transfer_to_segments(segs, ledger_equity=900.0)
    assert info["triggered"] is False
    assert info["reason"] == "frozen"
    assert out["secure_nok"] == 0.0


def test_sync_persists_secure_and_snapshots(tmp_path: Path, monkeypatch):
    import nt.capital_runtime as cr
    import nt.capital_v2 as cv

    # sync_capital_v2_state binds oslo_today from capital_runtime's import site
    # (from nt.capital_v2 import oslo_today) — patch both modules.
    fixed_day = "2026-07-21"
    monkeypatch.setattr(cv, "oslo_today", lambda: fixed_day)
    monkeypatch.setattr(cr, "oslo_today", lambda: fixed_day)
    cfg = _cfg(tmp_path, enabled=True)
    segs = sync_capital_v2_state(cfg, 700.0, [], persist=True)
    path = segments_path(cfg)
    assert path.is_file()
    disk = json.loads(path.read_text(encoding="utf-8"))
    # Variant A soft: 0.15 * (700-500) = 30
    assert disk["secure_nok"] == 30.0
    assert disk["unit_hwm_reset_equity_nok"] == 670.0
    assert disk["day_snapshot"]["oslo_date"] == fixed_day
    assert disk["day_snapshot"]["liquid_start_nok"] == riskable_liquid(700.0, 30.0, 0.0)
    assert disk["week_snapshot"]["week_id"] == "2026-W30"
    # second sync same equity: no double transfer
    segs2 = sync_capital_v2_state(cfg, 700.0, [], persist=True)
    assert segs2["secure_nok"] == 30.0
    assert len(segs2["secure_transfers"]) == 1


# ── snapshots ─────────────────────────────────────────────────────────────


def test_day_snapshot_freezes_liquid_start():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-20")
    segs = ensure_day_week_snapshots(
        segs,
        liquid_now=550.0,
        unit_now=10.0,
        today="2026-07-21",
        week_id="2026-W30",
        realized_day=0.0,
        realized_week=0.0,
    )
    assert segs["day_snapshot"]["liquid_start_nok"] == 550.0
    # same day, lower liquid (open risk later) — start frozen
    segs2 = ensure_day_week_snapshots(
        segs,
        liquid_now=500.0,
        unit_now=10.0,
        today="2026-07-21",
        week_id="2026-W30",
        realized_day=-20.0,
        realized_week=-20.0,
    )
    assert segs2["day_snapshot"]["liquid_start_nok"] == 550.0
    assert segs2["day_snapshot"]["realized_pl_nok"] == -20.0


def test_week_boundary_resets_snapshot():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-19")
    segs = ensure_day_week_snapshots(
        segs,
        liquid_now=500.0,
        unit_now=10.0,
        today="2026-07-19",
        week_id="2026-W29",
        realized_day=0.0,
        realized_week=-10.0,
    )
    assert segs["week_snapshot"]["week_id"] == "2026-W29"
    segs2 = ensure_day_week_snapshots(
        segs,
        liquid_now=480.0,
        unit_now=10.0,
        today="2026-07-20",
        week_id="2026-W30",
        realized_day=0.0,
        realized_week=0.0,
    )
    assert segs2["week_snapshot"]["week_id"] == "2026-W30"
    assert segs2["week_snapshot"]["liquid_start_nok"] == 480.0


def test_risk_uses_frozen_day_liquid_for_daily_limit(tmp_path: Path, monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    cfg = _cfg(tmp_path, enabled=True)
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["day_snapshot"] = {
        "oslo_date": "2026-07-21",
        "liquid_start_nok": 500.0,
        "unit_size_nok": 10.0,
        "realized_pl_nok": 0.0,
    }
    segs["week_snapshot"] = {
        "week_id": "2026-W30",
        "liquid_start_nok": 500.0,
        "unit_size_nok": 10.0,
        "realized_pl_nok": 0.0,
    }
    rows = [
        {
            "date": "2026-07-21",
            "updated_at": "2026-07-21T12:00:00Z",
            "result": "Loss",
            "p_l_nok": "-20",
            "stake_nok": "20",
        }
    ]
    # current equity lower; SoD liquid still 500 → daily limit 20
    risk = evaluate_risk(cfg, 480.0, PHASE, rows, segments=segs)
    assert risk["capital_v2_enabled"] is True
    assert risk["liquid_start_of_day_nok"] == 500.0
    assert risk["daily_loss_limit_nok"] == 20.0
    assert risk["daily_hard_stopped"] is True


# ── stake decisions JSONL ─────────────────────────────────────────────────


def test_append_stake_decision_jsonl(tmp_path: Path):
    cfg = _cfg(tmp_path, enabled=True)
    rec = {
        "match": "A vs B",
        "selection": "A",
        "final_stake_nok": 10.0,
        "size_mode": "NORMAL",
        "unit_size_nok": 10.0,
        "rule_bundle_version": "br_v2.0.0",
        "inputs": {"ev": 0.1},
    }
    append_stake_decision(cfg, rec)
    append_stake_decision(cfg, {**rec, "final_stake_nok": 10.0, "bet_id": "abc"})
    path = stake_decisions_path(cfg)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    a = json.loads(lines[0])
    b = json.loads(lines[1])
    assert a["final_stake_nok"] == 10.0
    assert b["bet_id"] == "abc"
    assert "ts" in a


def test_persist_stake_decisions_for_picks(tmp_path: Path):
    cfg = _cfg(tmp_path, enabled=True)
    picks = [
        Recommendation(
            match="X vs Y",
            selection="X",
            decimal_odds=1.8,
            stake_nok=10.0,
            ev=0.1,
            grade="B",
            odds_band="1.8-2.2",
            sport="darts",
            market_type="Vinner",
            p_model=0.7,
            notes="test",
            stake_decision={
                "final_stake_nok": 10.0,
                "size_mode": "NORMAL",
                "unit_size_nok": 10.0,
                "active_unit_nok": 10.0,
                "remaining_room_nok": 40.0,
                "constraints_applied": ["unit_ladder:10"],
                "inputs": {},
            },
        )
    ]
    n = persist_stake_decisions_for_picks(
        cfg,
        picks,
        bet_ids=["betdeadbeef"],
        phase_id="1A",
        risk={"remaining_risk_nok": 40.0, "size_mode": "NORMAL", "unit_size_nok": 10.0},
    )
    assert n == 1
    line = json.loads(stake_decisions_path(cfg).read_text(encoding="utf-8").strip())
    assert line["bet_id"] == "betdeadbeef"
    assert line["final_stake_nok"] == 10.0
    assert line["inputs"]["phase_id"] == "1A"


def test_persist_noop_when_flag_off(tmp_path: Path):
    cfg = _cfg(tmp_path, enabled=False)
    picks = [
        Recommendation(
            match="X",
            selection="Y",
            decimal_odds=1.8,
            stake_nok=10,
            ev=0.1,
            grade="B",
            odds_band="1.8-2.2",
            sport="darts",
            market_type="V",
            p_model=0.7,
            notes="",
            stake_decision={"final_stake_nok": 10},
        )
    ]
    assert persist_stake_decisions_for_picks(cfg, picks) == 0
    assert not stake_decisions_path(cfg).is_file()


# ── integration: sync → risk ──────────────────────────────────────────────


def test_sync_then_risk_sees_secure(tmp_path: Path, monkeypatch):
    import nt.capital_v2 as cv

    monkeypatch.setattr(cv, "oslo_today", lambda: "2026-07-21")
    cfg = _cfg(tmp_path, enabled=True)
    segs = sync_capital_v2_state(cfg, 700.0, [], persist=True)
    risk = evaluate_risk(cfg, 700.0, PHASE, [], segments=segs)
    # Variant A soft: 30 secure, working 670
    assert risk["secure_nok"] == 30.0
    assert risk["working_equity_nok"] == 670.0
    # phase cap on working equity
    assert risk["daily_risk_cap_nok"] == round(
        max(30.0, min(42.0, 670.0 * 0.08)), 2
    )
