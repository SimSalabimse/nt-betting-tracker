"""Mechanism B: temporary auditable EV softening (temp_ev_relax safety net)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.control_signals import (
    active_temp_ev_relax_overlay,
    clear_temp_ev_relax_on_settle,
    emit_temp_ev_relax,
    emit_temp_gate_raise,
    load_active_by_kind,
    load_active_signals,
    maybe_emit_temp_ev_relax,
    revoke_signals,
)
from nt.portfolio import Candidate, build_portfolio


def _cfg(tmp: Path, **ter_over) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    ter = {
        "enabled": True,
        "delta_min": 0.01,
        "delta_max": 0.02,
        "ttl_hours": 24,
        "clear_on_settle": True,
        "stake_mult": 0.80,
        "top_n_survivors": 3,
        "min_board_matches": 15,
        "require_coverage_warn": True,
        "exclude_high_odds": True,
        "exclude_grade_c": True,
    }
    ter.update(ter_over)
    return {
        "paths": {
            "state_dir": str(state),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
            "coverage_health_json": str(state / "coverage_health.json"),
        },
        "norsk_tipping": {"min_stake_nok": 10},
        "selection": {
            "probability_haircut": 0.03,
            "standard_min_ev": 0.03,
            "strong_min_ev": 0.015,
            "absolute_min_ev": 0.01,
            "strong_min_sources": 8,
            "grade_c_placeable": True,
            "grade_c_require_core_reason": True,
            "grade_c_min_sources": 4,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.08,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {
                "min_sample": 15,
                "bad_roi_below": -0.10,
                "extra_ev_required": 0.05,
            },
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
        },
        "learning": {
            "enabled": False,
            "control_signals": {
                "enabled": True,
                "min_ev_raise": 0.02,
                "max_raise": 0.05,
                "ttl_days": 10,
                "force_confirmed_lineup": True,
                "temp_ev_relax": ter,
            },
            "diversification": {
                "max_per_sport": 9,
                "max_per_market": 9,
                "max_per_band": 9,
                "max_per_match": 3,
                "max_football_per_round": 9,
                "min_non_football_per_round": 0,
                "prefer_explore_first": False,
                "explore_min_ev": 0.012,
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
        "capital_v2": {"enabled": False},
    }


def _phase(**kw):
    base = {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 4,
        "max_doubles_per_round": 0,
        "daily_risk_pct": 0.08,
        "daily_risk_floor": 30,
        "daily_risk_ceil": 42,
    }
    base.update(kw)
    return base


def _risk(remaining: float = 100.0):
    return {"can_bet": True, "remaining_risk_nok": remaining, "reasons": []}


def _pack(
    p: float,
    *,
    grade_sources: int = 8,
    summary: str = "solid core reason with enough characters for grade B",
    thin: bool = False,
) -> dict:
    n = 2 if thin else grade_sources
    sources = [
        {"url": f"https://example.com/{i}", "takeaway": "ok stats note", "kind": "stats"}
        for i in range(n)
    ]
    return {
        "match": "X",
        "selection": "Y",
        "p_model": p,
        "summary": summary if not thin else "short",
        "failure_modes": "rotation; injury; weather",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "full strength expected for test pack",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
    }


def test_emit_and_load_active_overlay(tmp_path: Path):
    cfg = _cfg(tmp_path)
    out = emit_temp_ev_relax(
        cfg,
        delta_ev=0.015,
        line_keys=[
            {"match": "Team A vs Team B", "selection": "Handicap -1.5"},
            "Other|Over 3.5",
        ],
        source="test",
        coverage_level="warn",
        board_matches=20,
    )
    assert out["ok"]
    assert out["signal"]["kind"] == "temp_ev_relax"
    assert out["signal"]["delta_ev"] == 0.015
    assert out["signal"]["stake_mult"] == 0.80
    assert "Team A vs Team B|Handicap -1.5" in out["signal"]["line_keys"]
    assert "Other|Over 3.5" in out["signal"]["line_keys"]

    active = load_active_by_kind(cfg, "temp_ev_relax")
    assert len(active) == 1
    ov = active_temp_ev_relax_overlay(cfg)
    assert ov["active"] is True
    assert ov["delta_ev"] == 0.015
    assert ov["stake_mult"] == 0.80
    assert "Team A vs Team B|Handicap -1.5" in ov["line_key_set"]

    # Also present in load_active_signals (multi-kind)
    all_active = load_active_signals(cfg)
    kinds = {str(a.get("kind")) for a in all_active}
    assert "temp_ev_relax" in kinds


def test_delta_clamped_to_band(tmp_path: Path):
    cfg = _cfg(tmp_path)
    high = emit_temp_ev_relax(
        cfg, delta_ev=0.10, line_keys=["M|S"], source="clamp", force=True
    )
    assert high["ok"]
    assert high["signal"]["delta_ev"] == 0.02  # delta_max
    low = emit_temp_ev_relax(
        cfg, delta_ev=0.001, line_keys=["M2|S2"], source="clamp", force=True
    )
    assert low["ok"]
    assert low["signal"]["delta_ev"] == 0.01  # delta_min


def test_skip_duplicate_same_keys(tmp_path: Path):
    cfg = _cfg(tmp_path)
    keys = ["A|B", "C|D"]
    assert emit_temp_ev_relax(cfg, delta_ev=0.02, line_keys=keys)["ok"]
    again = emit_temp_ev_relax(cfg, delta_ev=0.02, line_keys=keys)
    assert again["ok"] is False
    assert again["reason"] == "already_active_same_keys"


def test_min_ev_reduced_only_for_allowlisted(tmp_path: Path):
    """Allowlisted line gets -delta min_ev; non-allowlisted still blocked at standard floor.

    Haircut is subtractive: EV = (p - haircut) * odds - 1.
    p=0.54, odds=2.0, haircut=0.03 → EV = 0.02.
    standard_min_ev=0.03 rejects; with delta 0.02 → min_ev 0.01 → pass.
    """
    cfg = _cfg(tmp_path)
    p_border = 0.54  # EV = 0.02 after haircut
    emit_temp_ev_relax(
        cfg,
        delta_ev=0.02,
        line_keys=["Alpha vs Beta|Handicap +1.5"],
        force=True,
    )
    # 6 sources → grade B but not strong_min_ev (needs ≥8)
    allow = Candidate(
        date="2026-07-23",
        match="Alpha vs Beta",
        selection="Handicap +1.5",
        decimal_odds=2.0,
        sport="football",
        market_type="handicap",
        p_model=p_border,
        evidence=_pack(p_border, grade_sources=6),
    )
    other = Candidate(
        date="2026-07-23",
        match="Gamma vs Delta",
        selection="Handicap +1.5",
        decimal_odds=2.0,
        sport="tennis",
        market_type="handicap",
        p_model=p_border,
        evidence=_pack(p_border, grade_sources=6),
    )
    picked, rejects = build_portfolio(
        cfg, [allow, other], _phase(), _risk(), [], learning={}
    )
    allow_picked = [p for p in picked if p.match == "Alpha vs Beta"]
    other_picked = [p for p in picked if p.match == "Gamma vs Delta"]
    assert len(allow_picked) == 1, f"allowlisted should pass; rejects={rejects}"
    assert "temp_ev_relax" in (allow_picked[0].notes or "")
    assert len(other_picked) == 0
    other_rej = [
        r
        for r in rejects
        if isinstance(r, dict) and r.get("match") == "Gamma vs Delta"
    ]
    assert other_rej, "non-allowlisted should be EV-rejected"
    assert "EV" in str(other_rej[0].get("reason") or "")
    assert other_rej[0].get("temp_ev_relax_delta") in (None, 0, 0.0)


def test_high_odds_excluded(tmp_path: Path):
    """High-odds path never receives min_ev soften even if allowlisted."""
    cfg = _cfg(tmp_path)
    # EV just under high_odds_min_ev=0.08 after haircut:
    # (p-0.03)*3.2 - 1 = 0.06 → (p-0.03)=0.33125 → p≈0.361
    # If relax wrongly applied, standard path would not apply (high=True).
    p = 0.361
    emit_temp_ev_relax(
        cfg,
        delta_ev=0.02,
        line_keys=["HiOdds Match|Longshot ML"],
        force=True,
    )
    c = Candidate(
        date="2026-07-23",
        match="HiOdds Match",
        selection="Longshot ML",
        decimal_odds=3.2,  # >= 2.5 high-odds
        sport="football",
        market_type="ml",
        p_model=p,
        evidence=_pack(p, grade_sources=12),
    )
    c.evidence["p_model_sd"] = 0.04
    c.evidence["summary"] = "deep research pack with uncertainty band documented here"
    picked, rejects = build_portfolio(cfg, [c], _phase(), _risk(), [], learning={})
    assert not any(p.match == "HiOdds Match" for p in picked)
    # Reject reason must not claim temp_ev_relax helped
    hi_rej = [
        r for r in rejects if isinstance(r, dict) and r.get("match") == "HiOdds Match"
    ]
    assert hi_rej
    assert not hi_rej[0].get("temp_ev_relax_delta")
    ov = active_temp_ev_relax_overlay(cfg)
    assert "HiOdds Match|Longshot ML" in ov["line_key_set"]


def test_grade_c_excluded(tmp_path: Path):
    """True grade-C pack (placeable under HV v2) must not receive min_ev soften."""
    from nt.evidence import grade_evidence

    cfg = _cfg(tmp_path)
    p_border = 0.54  # EV = 0.02 after haircut
    emit_temp_ev_relax(
        cfg,
        delta_ev=0.02,
        line_keys=["Weak Pack Match|Over 2.5"],
        force=True,
    )
    # Grade C recipe: ≥3 sources (max(3, need//2)), has p_model, missing failure_modes
    # → issues non-empty but not F. Long summary so grade_c_require_core_reason passes.
    grade_c_pack = {
        "match": "Weak Pack Match",
        "selection": "Over 2.5",
        "p_model": p_border,
        "summary": "clear core reason with enough characters for grade C placeable path",
        # missing failure_modes → issues → grade C (not F)
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "full strength expected for test pack",
        "script_lean": "high_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": [
            {"url": f"https://example.com/c{i}", "takeaway": "ok stats", "kind": "stats"}
            for i in range(4)
        ],
    }
    g, _iss = grade_evidence(
        grade_c_pack, cfg, 2.0, selection="Over 2.5", sport="football"
    )
    assert g == "C", f"expected grade C pack, got {g} issues={_iss}"

    c = Candidate(
        date="2026-07-23",
        match="Weak Pack Match",
        selection="Over 2.5",
        decimal_odds=2.0,
        sport="football",
        market_type="totals",
        p_model=p_border,
        evidence=grade_c_pack,
    )
    picked, rejects = build_portfolio(cfg, [c], _phase(), _risk(), [], learning={})
    # Without relax, EV 0.02 < standard 0.03 → reject. Must not place via soften.
    assert not any(p.match == "Weak Pack Match" for p in picked)
    c_rej = [
        r
        for r in rejects
        if isinstance(r, dict) and r.get("match") == "Weak Pack Match"
    ]
    assert c_rej
    # EV path: prove relax was not applied (would have lowered min to ~0.01)
    assert c_rej[0].get("grade") == "C"
    assert not c_rej[0].get("temp_ev_relax_delta")
    assert "EV" in str(c_rej[0].get("reason") or "")


def test_stake_mult_applied(tmp_path: Path):
    cfg = _cfg(tmp_path)
    # Strong EV so both pass without needing relax for EV; only allowlisted gets stake mult
    # p=0.58, odds=2 → EV = (0.55)*2 - 1 = 0.10
    p_strong = 0.58
    emit_temp_ev_relax(
        cfg,
        delta_ev=0.02,
        line_keys=["Stake Match|Handicap -1"],
        force=True,
    )
    allow = Candidate(
        date="2026-07-23",
        match="Stake Match",
        selection="Handicap -1",
        decimal_odds=2.0,
        sport="football",
        market_type="handicap",
        p_model=p_strong,
        evidence=_pack(p_strong),
    )
    base = Candidate(
        date="2026-07-23",
        match="Base Match",
        selection="Handicap -1",
        decimal_odds=2.0,
        sport="tennis",
        market_type="handicap",
        p_model=p_strong,
        evidence=_pack(p_strong),
    )
    # One at a time so remaining risk does not cap stakes differently
    picked_a, rej_a = build_portfolio(cfg, [allow], _phase(), _risk(), [], learning={})
    picked_b, rej_b = build_portfolio(cfg, [base], _phase(), _risk(), [], learning={})
    assert len(picked_a) == 1, f"allow rejects={rej_a}"
    assert len(picked_b) == 1, f"base rejects={rej_b}"
    assert "temp_ev_relax" in (picked_a[0].notes or "")
    assert "temp_ev_relax" not in (picked_b[0].notes or "")
    # Mult 0.80 applied on learning_stake_mult path
    assert abs(picked_a[0].learning_stake_mult - 0.80) < 1e-6
    assert abs(picked_b[0].learning_stake_mult - 1.0) < 1e-6
    # Stake for allowlisted should be <= baseline (EV-scale band * 0.80)
    assert picked_a[0].stake_nok <= picked_b[0].stake_nok + 1e-9


def test_ttl_expired_inactive(tmp_path: Path):
    cfg = _cfg(tmp_path)
    out = emit_temp_ev_relax(
        cfg, delta_ev=0.02, line_keys=["Gone|Sel"], source="ttl", force=True
    )
    assert out["ok"]
    # Backdate expires_at into the past
    path = Path(cfg["paths"]["control_signals_jsonl"])
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(lines[-1])
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    rec["expires_at"] = past
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    ov = active_temp_ev_relax_overlay(cfg)
    assert ov["active"] is False
    assert load_active_by_kind(cfg, "temp_ev_relax") == []


def test_clear_on_settle_helper(tmp_path: Path):
    cfg = _cfg(tmp_path)
    emit_temp_ev_relax(
        cfg, delta_ev=0.02, line_keys=["S|X"], source="settle_test", force=True
    )
    assert active_temp_ev_relax_overlay(cfg)["active"] is True
    out = clear_temp_ev_relax_on_settle(cfg, actor="pytest")
    assert out["ok"]
    assert out.get("cleared", 0) >= 1
    assert active_temp_ev_relax_overlay(cfg)["active"] is False
    assert load_active_by_kind(cfg, "temp_ev_relax") == []


def test_clear_on_settle_respects_flag(tmp_path: Path):
    cfg = _cfg(tmp_path, clear_on_settle=False)
    emit_temp_ev_relax(
        cfg, delta_ev=0.02, line_keys=["S|Y"], source="no_clear", force=True
    )
    out = clear_temp_ev_relax_on_settle(cfg)
    assert out["ok"]
    assert out.get("skipped") == "clear_on_settle_false"
    assert active_temp_ev_relax_overlay(cfg)["active"] is True


def test_temp_gate_raise_still_works(tmp_path: Path):
    """temp_ev_relax must not break temp_gate_raise load/overlay."""
    cfg = _cfg(tmp_path)
    emit_temp_ev_relax(cfg, delta_ev=0.02, line_keys=["A|B"], force=True)
    emit_temp_gate_raise(cfg, sport="tennis", market="handicap", bet_id="b1")
    from nt.control_signals import active_temp_gate_overlay
    from nt.process_gates import process_gate_raise

    ov = active_temp_gate_overlay(cfg, sport="tennis")
    assert ov["min_ev_raise"] >= 0.02
    assert process_gate_raise(cfg, sport="tennis") >= 0.02
    # revoke sport must not kill temp_ev_relax
    revoke_signals(cfg, sport="tennis", actor="pytest")
    assert process_gate_raise(cfg, sport="tennis") == 0.0
    assert active_temp_ev_relax_overlay(cfg)["active"] is True


def test_trigger_conditions(tmp_path: Path):
    cfg = _cfg(tmp_path)
    survivors = [
        {
            "match": f"Match {i}",
            "selection": "Handicap +1.5",
            "decimal_odds": 2.0,
            "promotion_score": 100 - i,
        }
        for i in range(5)
    ]

    # Fail: board too small
    r = maybe_emit_temp_ev_relax(
        cfg,
        board_matches=10,
        coverage_level="warn",
        deep_queue_n=0,
        survivors=survivors,
    )
    assert r["ok"] is False
    assert r["reason"] == "board_matches_below_min"

    # Fail: coverage ok
    r = maybe_emit_temp_ev_relax(
        cfg,
        board_matches=20,
        coverage_level="ok",
        deep_queue_n=0,
        survivors=survivors,
    )
    assert r["ok"] is False
    assert r["reason"] == "coverage_not_warn_or_critical"

    # Fail: deep queue not empty
    r = maybe_emit_temp_ev_relax(
        cfg,
        board_matches=20,
        coverage_level="critical",
        deep_queue_n=3,
        survivors=survivors,
    )
    assert r["ok"] is False
    assert r["reason"] == "deep_queue_not_empty"

    # Fail: no survivors
    r = maybe_emit_temp_ev_relax(
        cfg,
        board_matches=20,
        coverage_level="warn",
        deep_queue_n=0,
        survivors=[],
    )
    assert r["ok"] is False
    assert r["reason"] == "no_survivors"

    # Pass: large board + warn + empty deep + survivors → top 3
    r = maybe_emit_temp_ev_relax(
        cfg,
        board_matches=20,
        coverage_level="warn",
        deep_queue_n=0,
        survivors=survivors,
    )
    assert r["ok"] is True
    keys = r["signal"]["line_keys"]
    assert len(keys) == 3
    assert keys[0] == "Match 0|Handicap +1.5"
    assert active_temp_ev_relax_overlay(cfg)["active"] is True

    # Spam guard: same keys again
    r2 = maybe_emit_temp_ev_relax(
        cfg,
        board_matches=20,
        coverage_level="warn",
        deep_queue_n=0,
        survivors=survivors,
    )
    assert r2["ok"] is False
    assert "already_active" in r2["reason"]


def test_trigger_excludes_high_odds_survivors(tmp_path: Path):
    cfg = _cfg(tmp_path)
    survivors = [
        {
            "match": "Long",
            "selection": "ML",
            "decimal_odds": 3.5,
            "promotion_score": 200,
        },
        {
            "match": "Mid",
            "selection": "HC +1.5",
            "decimal_odds": 2.1,
            "promotion_score": 50,
        },
    ]
    r = maybe_emit_temp_ev_relax(
        cfg,
        board_matches=20,
        coverage_level="critical",
        deep_queue_n=0,
        survivors=survivors,
    )
    assert r["ok"]
    assert r["signal"]["line_keys"] == ["Mid|HC +1.5"]


def test_process_gate_not_cancelled_by_relax(tmp_path: Path):
    """When process_gate is active, temp_ev_relax is skipped entirely (fail-closed).

    min_ev == standard + process_gate_raise; relax must not apply.
    """
    cfg = _cfg(tmp_path)
    p_border = 0.54  # EV = 0.02
    # Without gate: EV 0.02 would pass under relax (min 0.03-0.02=0.01).
    # With gate +2pp: min must be 0.03+0.02=0.05 — reject; no relax delta.
    emit_temp_ev_relax(
        cfg,
        delta_ev=0.02,
        line_keys=["Gate Match|Handicap +1.5"],
        force=True,
    )
    emit_temp_gate_raise(cfg, sport="football", market="handicap", bet_id="pe1")
    c = Candidate(
        date="2026-07-23",
        match="Gate Match",
        selection="Handicap +1.5",
        decimal_odds=2.0,
        sport="football",
        market_type="handicap",
        p_model=p_border,
        evidence=_pack(p_border, grade_sources=6),
    )
    picked, rejects = build_portfolio(cfg, [c], _phase(), _risk(), [], learning={})
    assert not any(p.match == "Gate Match" for p in picked)
    rej = [
        r for r in rejects if isinstance(r, dict) and r.get("match") == "Gate Match"
    ]
    assert rej
    reason = str(rej[0].get("reason") or "")
    assert "process_gate" in reason
    # Relax must not have been applied
    assert not rej[0].get("temp_ev_relax_delta")
    assert "temp_ev_relax" not in reason
    assert rej[0].get("process_gate_raise") and float(rej[0]["process_gate_raise"]) >= 0.02
    # Effective min = standard 0.03 + process_gate 0.02 = 0.05
    assert "min 0.050" in reason or "min 0.05" in reason


def test_haircut_invariant_under_relax(tmp_path: Path):
    """Relax must never change probability_haircut / ev_after_haircut."""
    from nt.evidence import ev_after_haircut

    cfg = _cfg(tmp_path)
    haircut = float(cfg["selection"]["probability_haircut"])
    p, odds = 0.54, 2.0
    base_ev = ev_after_haircut(p, odds, haircut)
    emit_temp_ev_relax(
        cfg, delta_ev=0.02, line_keys=["H|S"], force=True
    )
    # Haircut config unchanged; formula result identical
    assert float(cfg["selection"]["probability_haircut"]) == haircut
    assert ev_after_haircut(p, odds, haircut) == base_ev
    assert abs(base_ev - 0.02) < 1e-9

    c = Candidate(
        date="2026-07-23",
        match="H",
        selection="S",
        decimal_odds=odds,
        sport="football",
        market_type="handicap",
        p_model=p,
        evidence=_pack(p, grade_sources=6),
    )
    picked, _ = build_portfolio(cfg, [c], _phase(), _risk(), [], learning={})
    assert len(picked) == 1
    # Portfolio EV equals haircut formula (not softened p)
    assert abs(picked[0].ev - base_ev) < 1e-6
    assert "temp_ev_relax" in (picked[0].notes or "")


def test_absolute_floor_binds_after_relax(tmp_path: Path):
    """After delta, absolute_min_ev still law — EV below floor is rejected."""
    cfg = _cfg(tmp_path)
    # absolute_min_ev=0.01; p such that EV=0.005
    # (p-0.03)*2 - 1 = 0.005 → (p-0.03)=0.5025 → p=0.5325
    p_thin = 0.5325
    emit_temp_ev_relax(
        cfg,
        delta_ev=0.02,
        line_keys=["Floor Match|Handicap +1.5"],
        force=True,
    )
    c = Candidate(
        date="2026-07-23",
        match="Floor Match",
        selection="Handicap +1.5",
        decimal_odds=2.0,
        sport="football",
        market_type="handicap",
        p_model=p_thin,
        evidence=_pack(p_thin, grade_sources=6),
    )
    picked, rejects = build_portfolio(cfg, [c], _phase(), _risk(), [], learning={})
    assert not any(p.match == "Floor Match" for p in picked)
    rej = [
        r for r in rejects if isinstance(r, dict) and r.get("match") == "Floor Match"
    ]
    assert rej
    # min after relax would be 0.03-0.02=0.01 absolute floor
    reason = str(rej[0].get("reason") or "")
    assert "EV" in reason
    assert "0.010" in reason or "min 0.01" in reason


def test_clear_mixed_clear_on_settle_flags(tmp_path: Path):
    """Only signals with clear_on_settle=true are tombstoned; others remain."""
    cfg = _cfg(tmp_path)
    a = emit_temp_ev_relax(
        cfg, delta_ev=0.02, line_keys=["Keep|A"], force=True, source="keep"
    )
    b = emit_temp_ev_relax(
        cfg, delta_ev=0.02, line_keys=["Drop|B"], force=True, source="drop"
    )
    assert a["ok"] and b["ok"]
    # Patch first signal to opt out of settle-clear
    path = Path(cfg["paths"]["control_signals_jsonl"])
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    recs = [json.loads(ln) for ln in lines]
    for rec in recs:
        if rec.get("kind") == "temp_ev_relax" and "Keep|A" in (rec.get("line_keys") or []):
            rec["clear_on_settle"] = False
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
        encoding="utf-8",
    )
    out = clear_temp_ev_relax_on_settle(cfg, actor="pytest")
    assert out["ok"]
    assert out.get("cleared") == 1
    assert out.get("n_kept") == 1
    ov = active_temp_ev_relax_overlay(cfg)
    assert ov["active"] is True
    assert "Keep|A" in ov["line_key_set"]
    assert "Drop|B" not in ov["line_key_set"]


def test_run_settle_clears_temp_ev_relax(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """run_settle with a successful settle invokes clear and reports temp_ev_relax_clear."""
    from nt.bets_io import write_bets
    from nt.settle import run_settle

    cfg = _cfg(tmp_path)
    state = Path(cfg["paths"]["state_dir"])
    bets_path = tmp_path / "bets.csv"
    cfg["paths"]["bets"] = str(bets_path)
    cfg["paths"]["edges_jsonl"] = str(tmp_path / "edges.jsonl")
    cfg["paths"]["outbox"] = str(tmp_path / "outbox")
    cfg["paths"]["status"] = str(state / "status.md")
    cfg["paths"]["bankroll_md"] = str(state / "current_bankroll.md")
    cfg["bankroll"] = {"baseline_nok": 500.0, "era_start": "2026-07-01"}
    cfg["phases"] = {
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
    }
    cfg["risk"] = {
        "loss_streak_grade_a_only": 99,
        "stop_day_loss_pct_of_equity": 0.08,
        "stop_day_loss_floor_nok": 40,
    }
    cfg["capital_v2"] = {"enabled": False}
    (tmp_path / "outbox").mkdir(exist_ok=True)

    write_bets(
        bets_path,
        [
            {
                "bet_id": "t1",
                "date": "2026-07-23",
                "match": "Settle Team A vs B",
                "selection": "Over 2.5",
                "decimal_odds": "2.000",
                "stake_nok": "10.00",
                "result": "Pending",
                "p_l_nok": "",
                "payout_nok": "",
                "sport": "football",
                "market_type": "totals",
                "odds_band": "1.8-2.2",
                "research_grade": "B",
                "phase": "1A",
                "notes": "",
                "source": "test",
                "created_at": "2026-07-23T10:00:00Z",
                "updated_at": "2026-07-23T10:00:00Z",
            }
        ],
        backup=False,
    )

    # Keep refresh lightweight (focus is clear wiring after settled non-empty)
    import nt.settle as settle_mod

    monkeypatch.setattr(
        settle_mod,
        "refresh_state",
        lambda c: (
            {"equity_nok": 500.0},
            {"phase_id": "1A"},
            {"daily_risk_cap_nok": 40.0, "remaining_risk_nok": 40.0},
        ),
    )

    emit_temp_ev_relax(
        cfg, delta_ev=0.02, line_keys=["Settle Team A vs B|Over 2.5"], force=True
    )
    assert active_temp_ev_relax_overlay(cfg)["active"] is True

    results = tmp_path / "results.yaml"
    results.write_text(
        "results:\n  - bet_id: t1\n    outcome: loss\n    payout_nok: 0\n",
        encoding="utf-8",
    )
    out = run_settle(cfg, results)
    assert out.get("settled"), f"expected settle success, got {out}"
    clear_info = out.get("temp_ev_relax_clear") or {}
    assert clear_info.get("ok") is True
    assert clear_info.get("cleared", 0) >= 1
    assert active_temp_ev_relax_overlay(cfg)["active"] is False
