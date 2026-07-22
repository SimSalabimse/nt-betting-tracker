"""
HV Research Regime v3 — PR7 hard release gate.

T4: 3 honest p ≥ p_needed after 3pp haircut + dual-write packs → soft-pack places ~3
T5: market-mimic p≈implied → empty slip (equal merge priority to T4)
T12: EV-fail refresh injects preferred when pre-seeded failing packs
Policy invariants: haircut still 0.03, max_run_stake_pct_of_equity still 0.20

Never invents p_model for production path — fixtures set p_model explicitly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.clearability import p_needed_for_min_ev
from nt.defaults import recommend_cfg
from nt.evidence import ev_after_haircut
from nt.light_research import LightRecord, build_deep_queue
from nt.portfolio import Candidate, build_portfolio


# ---------------------------------------------------------------------------
# Shared fixtures (PR3 dual-write place law)
# ---------------------------------------------------------------------------


def _dual_write_pack(
    *,
    match: str,
    selection: str,
    p_model: float,
    odds: float,
    sport: str = "tennis",
) -> dict:
    sources = [
        {
            "url": f"https://example.com/{i}",
            "takeaway": "fixture research line for HV v3 integration",
            "kind": "injury" if i == 0 else "stats",
        }
        for i in range(8)
    ]
    return {
        "match": match,
        "selection": selection,
        "sport": sport,
        "p_model": p_model,
        "summary": (
            "Honest mid-band edge: multi-source form + script agreement for this selection."
        ),
        "failure_modes": "variance; late injury flip",
        "context_risk": "low",
        "availability_status": "confirmed",
        "availability_notes": "full strength confirmed for integration fixture",
        "lineup_status": "confirmed",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
        # Dual-write research odds (not inferred) — required for place
        "odds_at_research": float(odds),
        "decimal_odds_ref": float(odds),
        "researched_at": "2026-07-20T12:00:00Z",
        "odds_snapshot_inferred": False,
    }


def _portfolio_cfg() -> dict:
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
            "band_penalty": {
                "min_sample": 15,
                "bad_roi_below": -0.10,
                "extra_ev_required": 0.05,
            },
            "band_prior_boost": {},
            "min_research_sources": {"default": 6, "grade_A": 10, "high_odds": 12},
            "grade_a_require_uncertainty": True,
        },
        "recommend": {
            "max_run_stake_pct_of_equity": 0.20,
            "target_bets_per_run": 3,
            "soft_pack_phases": ["1A"],
            "soft_pack_on_exploration": True,
        },
        "research": {
            "pack_integrity": {
                "require_odds_at_research_for_place": True,
                "stale_odds_rel_threshold": 0.03,
            }
        },
        "learning": {
            "enabled": False,
            "diversification": {
                "max_per_sport": 4,
                "max_per_market": 4,
                "max_per_band": 4,
                "max_per_match": 1,
                "prefer_explore_first": False,
                "explore_min_ev": 0.012,
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
        "combos": {"enabled": False},
    }


def _phase() -> dict:
    return {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 5,
        "max_doubles_per_round": 0,
    }


def _risk(remaining: float = 40.0, equity: float = 500.0, unit: float = 12.0) -> dict:
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
        "bankroll_regime": "exploration",
        "regime_min_ev": 0.02,
        "regime_prefer_mid_odds": True,
        "capital_v2_enabled": True,
    }


def _cand(
    match: str,
    selection: str,
    odds: float,
    p_model: float,
    sport: str,
) -> Candidate:
    pack = _dual_write_pack(
        match=match,
        selection=selection,
        p_model=p_model,
        odds=odds,
        sport=sport,
    )
    return Candidate(
        date="2026-07-22",
        match=match,
        selection=selection,
        decimal_odds=odds,
        sport=sport,
        market_type="Vinner",
        p_model=p_model,
        evidence=pack,
    )


def _refresh_cfg() -> dict:
    return {
        "selection": {"probability_haircut": 0.03, "standard_min_ev": 0.02},
        "research": {
            "tiers": {
                "engine_deep_queue": True,
                "clearability_promotion": True,
                "dual_track_deep_queue": True,
                "second_pass_from_dump": True,
                "second_pass_max_inject": 12,
                "raw_ev_exhausted": -0.05,
                "second_pass_min_deep_packs": 8,
                "deep_target_n": 8,
                "deep_max_n": 12,
                "deep_min_preferred_share": 0.55,
                "deep_max_short_main_share": 0.25,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "short_chalk_odds": 1.70,
            }
        },
    }


def _rec(
    match: str,
    selection: str,
    odds: float,
    *,
    sport: str = "football",
    family: str = "ml",
    prior_p: float | None = 0.48,
    has_p: bool = False,
    raw_ev: float | None = None,
    source: str = "auto",
    is_inject: bool = False,
) -> LightRecord:
    haircut = 0.03
    prior_ev = None
    if prior_p is not None:
        prior_ev = (float(prior_p) - haircut) * float(odds) - 1.0
    return LightRecord(
        match=match,
        selection=selection,
        sport=sport,
        decimal_odds=float(odds),
        odds_band="mid",
        market_family=family,
        verdict="pass",
        has_p_model=has_p,
        has_deep_pack=has_p,
        prior_p=prior_p,
        prior_ev=prior_ev,
        prior_available=prior_ev is not None,
        raw_ev=raw_ev,
        source=source,
        is_inject=is_inject,
    )


# ---------------------------------------------------------------------------
# Policy invariants (always ship with T4/T5/T12)
# ---------------------------------------------------------------------------


def test_hv_v3_haircut_and_run_stake_cap_invariants():
    """Haircut still 0.03; max_run_stake_pct_of_equity still 0.20 (live + defaults)."""
    cfg_path = ROOT / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert float(raw["selection"]["probability_haircut"]) == pytest.approx(0.03)
    assert float(raw["recommend"]["max_run_stake_pct_of_equity"]) == pytest.approx(0.20)

    rc = recommend_cfg({})
    assert float(rc["max_run_stake_pct_of_equity"]) == pytest.approx(0.20)

    # Math identity: 3pp at odds 2.0 → fair EV −0.06
    assert ev_after_haircut(0.50, 2.0, 0.03) == pytest.approx(-0.06)
    assert p_needed_for_min_ev(2.0, min_ev=0.02, haircut=0.03) == pytest.approx(0.54)


# ---------------------------------------------------------------------------
# T4 — place-capable three-bet soft pack
# ---------------------------------------------------------------------------


def test_t4_soft_pack_three_honest_edges_under_remaining_40():
    """
    T4: 3 synthetic candidates with honest p that clears EV after 3pp haircut
    and dual-write packs → soft-pack under remaining 40 places ~3.
    """
    cfg = _portfolio_cfg()
    haircut = float(cfg["selection"]["probability_haircut"])
    min_ev = float(cfg["selection"]["standard_min_ev"])
    assert haircut == pytest.approx(0.03)
    assert float(cfg["recommend"]["max_run_stake_pct_of_equity"]) == pytest.approx(0.20)

    rows = [
        ("Alpha vs Beta", "Vinner: Alpha", 1.90, "tennis"),
        ("Gamma vs Delta", "Vinner: Gamma", 1.95, "darts"),
        ("Epsilon vs Zeta", "Vinner: Epsilon", 2.00, "basketball"),
    ]
    cands: list[Candidate] = []
    for match, sel, odds, sport in rows:
        # Honest p slightly above the clearability bar after haircut
        p = p_needed_for_min_ev(odds, min_ev=min_ev, haircut=haircut) + 0.02
        raw = ev_after_haircut(p, odds, haircut)
        assert raw + 1e-12 >= min_ev, f"fixture must clear EV: raw={raw} min={min_ev}"
        cands.append(_cand(match, sel, odds, p, sport))

    picked, rejects = build_portfolio(
        cfg, cands, _phase(), _risk(remaining=40.0, equity=500.0, unit=12.0),
        historical_rows=[],
        learning={},
    )
    assert len(picked) == 3, (
        f"T4 soft-pack should place ~3 seats, got {len(picked)}; rejects={rejects!r}"
    )
    stakes = [float(p.stake_nok) for p in picked]
    total = sum(stakes)
    assert total <= 40.0 + 1e-6
    assert total >= 36.0 - 1e-9  # unit-first ~12×3
    assert all(s >= 10.0 for s in stakes)

    audit = getattr(build_portfolio, "_run_stake_audit", {})
    assert audit.get("soft_pack_applied") is True
    assert audit.get("n_picked") == 3
    assert audit.get("run_stake_binding") == "phase_remaining"
    assert float(audit.get("run_stake_equity_cap_nok") or 0) == pytest.approx(100.0)
    assert float(audit.get("run_stake_cap_nok") or 0) == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# T5 — market-mimic honest empty (equal priority to T4)
# ---------------------------------------------------------------------------


def test_t5_market_mimic_p_implied_empty_slip():
    """
    T5: p_model ≈ implied → raw_ev ≈ −haircut×odds < min-EV → empty slip.
    Equal merge-blocking priority with T4 (anti-overclaim).
    """
    cfg = _portfolio_cfg()
    haircut = float(cfg["selection"]["probability_haircut"])
    min_ev = float(cfg["selection"]["standard_min_ev"])

    rows = [
        ("Mimic A vs B", "Vinner: A", 1.90, "tennis"),
        ("Mimic C vs D", "Vinner: C", 1.95, "darts"),
        ("Mimic E vs F", "Vinner: E", 2.00, "basketball"),
    ]
    cands: list[Candidate] = []
    for match, sel, odds, sport in rows:
        p_implied = 1.0 / odds
        raw = ev_after_haircut(p_implied, odds, haircut)
        assert raw < min_ev
        assert abs(raw - (-haircut * odds)) < 1e-9
        cands.append(_cand(match, sel, odds, p_implied, sport))

    picked, rejects = build_portfolio(
        cfg, cands, _phase(), _risk(remaining=40.0, equity=500.0, unit=12.0),
        historical_rows=[],
        learning={},
    )
    assert picked == [], (
        f"T5 market-mimic must not place; got picks={[p.match for p in picked]!r} "
        f"rejects={rejects!r}"
    )
    assert rejects, "expected EV / no-edge rejects"
    # Rejects should be EV-related (not missing_odds_snapshot) — packs dual-wrote
    reasons = " ".join(str(r.get("reason", "")) for r in rejects).lower()
    assert "missing_odds_snapshot" not in reasons
    assert any(
        "ev" in str(r.get("reason", "")).lower()
        or float(r.get("raw_ev") or 0) < min_ev
        for r in rejects
    ), f"expected EV-fail rejects, got {rejects!r}"


# ---------------------------------------------------------------------------
# T12 — EV-fail refresh injects preferred (queue improves)
# ---------------------------------------------------------------------------


def test_t12_ev_fail_refresh_injects_preferred_improves_queue():
    """
    T12: Pre-seed failing packs (p≈implied), inject preferred alts →
    refresh queue improves (injects in, exhausted out).
    """
    cfg = _refresh_cfg()
    haircut = 0.03

    failing: list[LightRecord] = []
    pack_meta: dict[tuple[str, str], dict] = {}
    for i in range(10):
        odds = 1.95 + (i % 5) * 0.05
        p_model = 1.0 / odds  # market-mimic
        raw = ev_after_haircut(p_model, odds, haircut)
        assert raw < -0.05
        r = _rec(
            f"Fail{i} vs Opp",
            f"Vinner: Home{i}",
            odds,
            family="ml",
            prior_p=p_model,
            has_p=True,
            raw_ev=raw,
        )
        failing.append(r)
        pack_meta[r.key()] = {
            "has_pack": True,
            "p_model": p_model,
            "odds": odds,
            "raw_ev": raw,
            "deep_exhausted": True,
        }

    injects: list[LightRecord] = []
    for i in range(5):
        odds = 2.05 + i * 0.05  # preferred mid band
        prior_p = 0.50 + i * 0.01  # better than pure-implied
        injects.append(
            _rec(
                f"Inj{i} vs X",
                f"Handikap +{3 + i}.5: Away",
                odds,
                sport="tennis" if i % 2 else "football",
                family="handicap",
                prior_p=prior_p,
                has_p=False,
                source="inject",
                is_inject=True,
            )
        )

    open_pref = [
        _rec(
            f"Open{i} vs Y",
            "Totalt 3.5: Over 3.5",
            2.10,
            family="totals_over",
            prior_p=0.49,
        )
        for i in range(3)
    ]

    queue = build_deep_queue(
        failing + open_pref,
        cfg,
        mode="refresh",
        inject_records=injects,
        pack_meta_by_key=pack_meta,
        force_requeue_exhausted=False,
    )

    assert queue, "T12 refresh queue must improve (not empty) with injects"
    fail_keys = {r.key() for r in failing}
    q_keys = {r.key() for r in queue}
    assert fail_keys.isdisjoint(q_keys), "exhausted failing packs must not re-enter"

    inject_keys = {r.key() for r in injects}
    n_inject = len(q_keys & inject_keys)
    assert n_inject >= 1, "expected preferred injects in refresh queue"

    # Preferred / survivable composition in the improved queue
    preferred_n = sum(
        1
        for r in queue
        if float(r.decimal_odds) >= 1.85
        or (
            float(r.decimal_odds) >= 1.80
            and (r.market_family or "") not in ("ml", "totals_over", "first_goal")
        )
    )
    assert preferred_n >= 1, "refresh path should surface preferred-band work"

    for r in queue:
        assert r.queue_mode == "refresh"
        assert r.clearability_score is not None

