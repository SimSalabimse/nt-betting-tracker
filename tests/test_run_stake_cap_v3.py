"""
HV Research Regime v3 — PR5: soft pack + run-stake audit (T2 / T14 / T16).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.portfolio import (
    Candidate,
    build_portfolio,
    compute_run_stake_audit,
    soft_pack_active,
)


def _pack(
    p: float = 0.72,
    match: str = "X",
    selection: str = "Y",
    odds: float = 2.0,
) -> dict:
    sources = [
        {
            "url": f"https://example.com/{i}",
            "takeaway": "ok stats line for grade B",
            "kind": "injury" if i == 0 else "stats",
        }
        for i in range(8)
    ]
    return {
        "match": match,
        "selection": selection,
        "p_model": p,
        "summary": "Clear mid-band edge with multi-source case for this selection.",
        "failure_modes": "variance / late lineup rotation",
        "context_risk": "low",
        "availability_status": "confirmed",
        "availability_notes": "full strength confirmed for test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
        # PR3 fail-closed place: dual-write real research odds (not inferred)
        "odds_at_research": float(odds),
        "decimal_odds_ref": float(odds),
        "researched_at": "2026-07-20T12:00:00Z",
        "odds_snapshot_inferred": False,
    }


def _cfg(**rec_extra) -> dict:
    return {
        "norsk_tipping": {"min_stake_nok": 10.0},
        "capital_v2": {
            "enabled": True,
            "unit_ladder": [
                {"max_liquid_exclusive": 1500.0, "unit": 12.0},
                {"max_liquid_exclusive": 2500.0, "unit": 15.0},
                {"max_liquid_exclusive": None, "unit": 20.0},
            ],
            "grade_stake_mult": {"C": 1.0, "B": 1.4, "A": 2.0, "A_high_conf": 2.2},
            "kelly": {"enabled": False},
        },
        "selection": {
            "probability_haircut": 0.03,
            "standard_min_ev": 0.02,
            "strong_min_ev": 0.015,
            "absolute_min_ev": 0.01,
            "strong_min_sources": 8,
            "grade_c_placeable": True,
            "grade_c_require_core_reason": True,
            "grade_c_min_sources": 4,
            "high_odds_threshold": 2.5,
            "high_odds_min_ev": 0.05,
            "high_odds_min_grade": "A",
            "high_odds_stake_multiplier": 0.6,
            "high_odds_max_per_round": 2,
            "band_penalty": {"min_sample": 15, "bad_roi_below": -0.10, "extra_ev_required": 0.05},
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
        },
        "recommend": {
            "max_run_stake_pct_of_equity": 0.20,
            "target_bets_per_run": 3,
            "soft_pack_phases": ["1A"],
            "soft_pack_on_exploration": True,
            **rec_extra,
        },
        "learning": {
            "enabled": False,
            "diversification": {
                "max_per_sport": 4,
                "max_per_market": 4,
                "max_per_band": 4,
                "max_per_match": 1,
                "max_football_per_round": 2,
                "min_non_football_per_round": 0,
                "prefer_explore_first": False,
                "explore_min_ev": 0.012,
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
        "combos": {"enabled": False},
    }


def _phase(**kw) -> dict:
    base = {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 5,
        "max_doubles_per_round": 0,
        "daily_risk_pct": 0.08,
        "daily_risk_floor": 30,
        "daily_risk_ceil": 42,
    }
    base.update(kw)
    return base


def _risk(
    *,
    remaining: float = 40.0,
    equity: float = 500.0,
    unit: float = 12.0,
    regime: str = "exploration",
) -> dict:
    return {
        "can_bet": True,
        "stopped": False,
        "remaining_risk_nok": remaining,
        "daily_risk_cap_nok": max(remaining, 40.0),
        "reasons": [],
        "size_mode": "NORMAL",
        "unit_size_nok": unit,
        "riskable_liquid_nok": equity,
        "working_equity_nok": equity,
        "equity_nok": equity,
        "secure_nok": 0.0,
        "phase_id": "1A",
        "bankroll_regime": regime,
        "regime_min_ev": 0.02 if regime == "exploration" else 0.03,
        "regime_prefer_mid_odds": regime in ("exploration", "survival"),
        "capital_v2_enabled": True,
    }


def _cand(
    match: str,
    selection: str,
    odds: float,
    p: float,
    sport: str,
) -> Candidate:
    pack = _pack(p, match=match, selection=selection, odds=odds)
    return Candidate(
        date="2026-07-22",
        match=match,
        selection=selection,
        decimal_odds=odds,
        sport=sport,
        market_type="Vinner",
        p_model=p,
        evidence=pack,
    )


# ── T2: 20% of 500 = 100 budget math ─────────────────────────────────────


def test_t2_run_stake_budget_math_20pct_of_500():
    """Equity 500 → equity cap 100; with remaining 40 → budget 40, binding phase."""
    a = compute_run_stake_audit(
        remaining_risk_nok=40.0,
        equity_nok=500.0,
        run_pct=0.20,
        used_nok=0.0,
    )
    assert a["run_stake_equity_cap_nok"] == pytest.approx(100.0)
    assert a["run_stake_cap_nok"] == pytest.approx(40.0)
    assert a["run_stake_remaining_risk_nok"] == pytest.approx(40.0)
    assert a["run_stake_binding"] == "phase_remaining"

    # When remaining is large, equity pct binds
    b = compute_run_stake_audit(
        remaining_risk_nok=200.0,
        equity_nok=500.0,
        run_pct=0.20,
        used_nok=0.0,
    )
    assert b["run_stake_equity_cap_nok"] == pytest.approx(100.0)
    assert b["run_stake_cap_nok"] == pytest.approx(100.0)
    assert b["run_stake_binding"] == "equity_pct"

    # Via build_portfolio side channel (phase binds)
    cfg = _cfg()
    cands = [
        _cand("A vs B", "Vinner: A", 1.90, 0.72, "tennis"),
        _cand("C vs D", "Vinner: C", 1.95, 0.71, "darts"),
        _cand("E vs F", "Vinner: E", 2.00, 0.70, "basketball"),
    ]
    risk = _risk(remaining=40.0, equity=500.0, unit=12.0)
    picked, _ = build_portfolio(cfg, cands, _phase(), risk, historical_rows=[], learning={})
    audit = getattr(build_portfolio, "_run_stake_audit", {})
    assert float(audit["run_stake_equity_cap_nok"]) == pytest.approx(100.0)
    assert float(audit["run_stake_cap_nok"]) == pytest.approx(40.0)
    assert audit["run_stake_binding"] == "phase_remaining"
    used = sum(p.stake_nok for p in picked)
    assert used <= 40.0 + 1e-6
    assert float(audit["run_stake_used_nok"]) == pytest.approx(used)

    # End-to-end equity_pct binding via portfolio (remaining 200 > equity cap 100)
    risk_eq = _risk(remaining=200.0, equity=500.0, unit=12.0)
    picked2, _ = build_portfolio(cfg, cands, _phase(), risk_eq, historical_rows=[], learning={})
    audit2 = getattr(build_portfolio, "_run_stake_audit", {})
    assert float(audit2["run_stake_equity_cap_nok"]) == pytest.approx(100.0)
    assert float(audit2["run_stake_cap_nok"]) == pytest.approx(100.0)
    assert audit2["run_stake_binding"] == "equity_pct"
    assert sum(p.stake_nok for p in picked2) <= 100.0 + 1e-6


# ── soft_pack_active + recommend_cfg SSOT ────────────────────────────────


def test_soft_pack_active_defaults():
    from nt.defaults import recommend_cfg

    cfg = _cfg()
    assert soft_pack_active(cfg, phase_id="1A", bankroll_regime="exploration") is True
    assert soft_pack_active(cfg, phase_id="1A", bankroll_regime="survival") is True  # phase list
    assert soft_pack_active(cfg, phase_id="1B", bankroll_regime="exploration") is True  # on_expl
    assert soft_pack_active(cfg, phase_id="1B", bankroll_regime="survival") is False
    assert soft_pack_active(cfg, phase_id="2", bankroll_regime="normal") is False

    cfg2 = _cfg(soft_pack_phases=["1A", "1B"], soft_pack_on_exploration=False)
    assert soft_pack_active(cfg2, phase_id="1B", bankroll_regime="exploration") is True
    assert soft_pack_active(cfg2, phase_id="2", bankroll_regime="exploration") is False

    # recommend_cfg is the shared defaults SSOT
    rc = recommend_cfg({})
    assert rc["target_bets_per_run"] == 3
    assert rc["soft_pack_phases"] == ["1A"]
    assert rc["soft_pack_on_exploration"] is True
    assert rc["max_run_stake_pct_of_equity"] == pytest.approx(0.20)
    # Empty phases list is preserved (disables phase match)
    rc2 = recommend_cfg({"recommend": {"soft_pack_phases": []}})
    assert rc2["soft_pack_phases"] == []

    # R1: [] must not re-default to ["1A"] inside soft_pack_active
    cfg_empty = _cfg(soft_pack_phases=[], soft_pack_on_exploration=False)
    assert soft_pack_active(cfg_empty, phase_id="1A", bankroll_regime="survival") is False
    assert soft_pack_active(cfg_empty, phase_id="1A", bankroll_regime="exploration") is False
    # Empty phases + exploration flag still arms soft pack via regime path
    cfg_empty_expl = _cfg(soft_pack_phases=[], soft_pack_on_exploration=True)
    assert soft_pack_active(cfg_empty_expl, phase_id="1A", bankroll_regime="survival") is False
    assert soft_pack_active(cfg_empty_expl, phase_id="1A", bankroll_regime="exploration") is True


def test_soft_pack_gate_uses_target_bets_not_hardcoded_3():
    """target_bets_per_run=4 requires ≥4 clears; 3 clears → soft_pack_applied false."""
    cfg = _cfg(target_bets_per_run=4)
    cands = [
        _cand("A1 vs B1", "Vinner: A1", 1.90, 0.72, "tennis"),
        _cand("A2 vs B2", "Vinner: A2", 1.95, 0.71, "darts"),
        _cand("A3 vs B3", "Vinner: A3", 2.00, 0.70, "basketball"),
    ]
    risk = _risk(remaining=50.0, equity=500.0, unit=12.0)
    picked, _ = build_portfolio(cfg, cands, _phase(), risk, historical_rows=[], learning={})
    audit = getattr(build_portfolio, "_run_stake_audit", {})
    assert audit.get("target_bets_per_run") == 4
    assert audit.get("soft_pack_applied") is False  # n_ev_clear 3 < target 4
    assert audit.get("soft_pack_eligible") is True
    assert "soft_pack_applied" in (picked[0].stake_decision or {}) if picked else True


# ── T14: PLACE markdown + JSON audit fields ──────────────────────────────


def test_t14_place_and_json_run_stake_audit_fields(tmp_path, monkeypatch):
    """PLACE markdown + recommend JSON expose full run_stake_* audit."""
    from nt.recommend import run_recommend

    cfg = _cfg()
    # Isolate paths under tmp
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    bets = tmp_path / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "sport,market_type,odds_band,research_grade,phase,notes,source,created_at,updated_at\n",
        encoding="utf-8",
    )
    cfg["paths"] = {
        "bets": str(bets),
        "evidence": str(evidence),
        "outbox": str(outbox),
        "state_dir": str(state),
        "inbox": str(tmp_path / "inbox"),
    }
    cfg["bankroll"] = {"baseline_nok": 500, "era_start": "2026-07-22", "include_era_archive": False}
    cfg["phases"] = {
        "1A": {
            "stake_min": 10,
            "stake_max": 12,
            "max_bets_per_round": 5,
            "max_doubles_per_round": 0,
            "daily_risk_pct": 0.08,
            "daily_risk_floor": 30,
            "daily_risk_ceil": 42,
            "min_settled": 0,
            "min_equity": 0,
        }
    }
    cfg["research"] = {"require_research_for_recommend": False}
    cfg["bankroll_regime"] = {
        "enabled": True,
        "exploration": {
            "exit_settled": 40,
            "exit_equity": 650,
            "min_ev": 0.02,
            "open_risk_cap_nok": 100,
        },
        "survival": {"min_ev": 0.03, "open_risk_cap_nok": 100},
    }
    cfg["risk"] = {
        "loss_streak_grade_a_only": 99,
        "max_open_pending_risk_pct": 0.5,
    }
    cfg["capital_v2"]["enabled"] = True

    # Evidence packs matching CSV rows
    rows_meta = [
        ("Match A vs B", "Vinner: A", 1.90, 0.72, "tennis"),
        ("Match C vs D", "Vinner: C", 1.95, 0.71, "darts"),
        ("Match E vs F", "Vinner: E", 2.00, 0.70, "esports"),
    ]
    odds_lines = ["date,match,selection,decimal_odds,sport,market_type,p_model,notes"]
    for match, sel, odds, p, sport in rows_meta:
        odds_lines.append(f"2026-07-22,{match},{sel},{odds},{sport},Vinner,{p},")
        pack = _pack(p, match=match, selection=sel, odds=odds)
        # attach_evidence looks up by match/selection keys — write simple filename packs
        key = f"{match.replace(' ', '_').replace(':', '')}__{sel.replace(' ', '_').replace(':', '')}"
        (evidence / f"{key}.json").write_text(
            __import__("json").dumps(pack), encoding="utf-8"
        )
        # also write match-only style pack if needed
        (evidence / f"{match.split(' vs ')[0].strip().replace(' ', '_')}.json").write_text(
            __import__("json").dumps(pack), encoding="utf-8"
        )
    odds_path = tmp_path / "odds.csv"
    odds_path.write_text("\n".join(odds_lines) + "\n", encoding="utf-8")

    # Stub refresh_state so we don't depend on full capital_runtime file IO
    def _fake_refresh(c):
        phase = _phase()
        risk = _risk(remaining=40.0, equity=500.0, unit=12.0)
        bankroll = {
            "equity_nok": 500.0,
            "baseline_nok": 500.0,
            "settled_count": 0,
            "realized_pl_nok": 0.0,
            "pending_risk_nok": 0.0,
        }
        return bankroll, phase, risk

    monkeypatch.setattr("nt.recommend.refresh_state", _fake_refresh)
    # Avoid writing real learning
    monkeypatch.setattr("nt.learning.load_learning", lambda _c: {})

    result = run_recommend(cfg, odds_path, log_pending=False, force_mechanical=True)

    # JSON audit fields (flat + nested)
    for key in (
        "run_stake_cap_nok",
        "run_stake_equity_cap_nok",
        "run_stake_remaining_risk_nok",
        "run_stake_used_nok",
        "run_stake_binding",
    ):
        assert key in result, f"missing {key} in recommend JSON"
        assert result[key] is not None
    assert result["run_stake_equity_cap_nok"] == pytest.approx(100.0)
    assert result["run_stake_cap_nok"] == pytest.approx(40.0)
    assert result["run_stake_binding"] in ("phase_remaining", "equity_pct")
    assert isinstance(result.get("run_stake"), dict)
    assert result["run_stake"]["run_stake_binding"] == result["run_stake_binding"]

    # PLACE markdown audit line
    place_text = (outbox / "PLACE_THESE.md").read_text(encoding="utf-8")
    assert "Run stake:" in place_text
    assert "binding:" in place_text
    assert "phase_remaining" in place_text or "equity_pct" in place_text
    assert "equity cap" in place_text
    # Cap value surfaces
    assert "100" in place_text or "40" in place_text


# ── T16: soft pack 3×B → 3 seats under remaining 40 ──────────────────────


def test_t16_soft_pack_three_grade_b_not_two_fat():
    """
    3 grade-B EV-clears, equity 500, remaining 40, unit 12:
    → 3 places, stakes sum ≤40, unit-first then leftover-only top-up
    (e.g. 16+12+12), not two fat grade-mult + thin/dropped third.
    """
    cfg = _cfg()
    # p high enough for grade B + EV after 3pp haircut at ~1.9
    # EV = p*odds - 1 - haircut*odds; p=0.72, odds=1.9 → 0.72*1.9 - 1 - 0.03*1.9 = 0.311
    cands = [
        _cand("Alpha vs Beta", "Vinner: Alpha", 1.90, 0.72, "tennis"),
        _cand("Gamma vs Delta", "Vinner: Gamma", 1.95, 0.71, "darts"),
        _cand("Epsilon vs Zeta", "Vinner: Epsilon", 2.00, 0.70, "basketball"),
    ]
    risk = _risk(remaining=40.0, equity=500.0, unit=12.0, regime="exploration")
    phase = _phase(phase_id="1A", max_bets_per_round=5)

    picked, rejects = build_portfolio(
        cfg, cands, phase, risk, historical_rows=[], learning={}
    )

    assert len(picked) == 3, (
        f"soft pack should place 3 seats, got {len(picked)}; "
        f"rejects={rejects[:5]!r}"
    )
    stakes = sorted(float(p.stake_nok) for p in picked)
    total = sum(stakes)
    assert total <= 40.0 + 1e-6
    assert total >= 36.0 - 1e-9  # unit-first 12×3, leftover ≤4 spent on top-up
    assert all(s >= 10.0 for s in stakes)
    # Leftover-only top-up pattern: two seats at unit, one may take residual ≤ grade-B 16
    assert stakes[0] == pytest.approx(12.0)  # lowest stays at unit
    assert stakes[1] == pytest.approx(12.0)
    assert stakes[2] <= 16.0 + 1e-9
    assert stakes[2] >= 12.0 - 1e-9

    audit = getattr(build_portfolio, "_run_stake_audit", {})
    assert audit.get("soft_pack_applied") is True  # mode engaged
    assert audit.get("soft_pack_seats_hit") is True  # n_picked >= target
    assert audit.get("n_picked") == 3
    assert audit.get("target_bets_per_run") == 3
    assert audit.get("run_stake_binding") == "phase_remaining"
    for p in picked:
        assert p.stake_decision is not None
        assert p.stake_decision.get("soft_pack_applied") is True
        assert p.stake_decision.get("soft_pack_seats_hit") is True
        cons = " ".join(p.stake_decision.get("constraints_applied") or [])
        assert "soft_pack_unit_cap:" in cons
        assert p.grade in ("A", "B", "C")


def test_t16_without_soft_pack_still_budget_safe():
    """Soft pack off: still never exceeds run budget (fail-closed)."""
    cfg = _cfg(soft_pack_phases=[], soft_pack_on_exploration=False)
    cands = [
        _cand("A1 vs B1", "Vinner: A1", 1.90, 0.72, "tennis"),
        _cand("A2 vs B2", "Vinner: A2", 1.95, 0.71, "darts"),
        _cand("A3 vs B3", "Vinner: A3", 2.00, 0.70, "basketball"),
    ]
    risk = _risk(remaining=40.0, equity=500.0, unit=12.0, regime="survival")
    picked, _ = build_portfolio(
        cfg, cands, _phase(phase_id="2"), risk, historical_rows=[], learning={}
    )
    total = sum(p.stake_nok for p in picked)
    assert total <= 40.0 + 1e-6
    audit = getattr(build_portfolio, "_run_stake_audit", {})
    assert audit.get("soft_pack_applied") is False
    assert audit.get("soft_pack_seats_hit") is False
    # soft_pack_applied always present on stake_decision (false when off)
    for p in picked:
        if p.stake_decision is not None:
            assert p.stake_decision.get("soft_pack_applied") is False
