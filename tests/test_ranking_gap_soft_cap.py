"""PR4: ranking-gap HC soft max 1 with EV-slack peers (Rule 3.2)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.portfolio import Candidate, build_portfolio


def _phase(**kw):
    base = {
        "phase_id": "1A",
        "stake_min": 10,
        "stake_max": 12,
        "max_bets_per_round": 3,
        "max_doubles_per_round": 0,
        "daily_risk_pct": 0.08,
        "daily_risk_floor": 30,
        "daily_risk_ceil": 42,
    }
    base.update(kw)
    return base


def _risk(remaining: float = 100.0):
    return {
        "can_bet": True,
        "remaining_risk_nok": remaining,
        "reasons": [],
    }


def _cfg(*, rg_enabled: bool = True, max_bets_phase: int = 3):
    return {
        "norsk_tipping": {"min_stake_nok": 10},
        "selection": {
            "probability_haircut": 0.05,
            "standard_min_ev": 0.02,
            "strong_min_ev": 0.015,
            "absolute_min_ev": 0.01,
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
            "min_research_sources": {"default": 4, "grade_A": 8, "high_odds": 10},
            "grade_c_placeable": True,
            "grade_c_require_core_reason": True,
            "grade_c_min_sources": 4,
        },
        "learning": {
            "enabled": True,
            "diversification": {
                "max_per_sport": 4,
                "max_per_market": 4,
                "max_per_band": 4,
                "max_per_match": 1,
                "max_football_per_round": 2,
                "min_non_football_per_round": 0,
                "prefer_explore_first": False,
                "explore_min_n": 0,
                "explore_max_n": 14,
                "explore_ev_boost": 0.0,
                "explore_virgin_ev_boost": 0.0,
                "explore_stake_floor": 0.92,
                "explore_min_roi": -0.15,
                "explore_min_ev": 0.012,
                "explore_base_ev_min": 0.005,
                "max_per_league": 4,
                "max_per_script_family": 4,
                "max_per_ko_window": 4,
                "sort": {
                    "similar_penalty_weight": 1.0,
                    "macro_underrep_bonus": 0.0,
                    "explore_tiebreak": False,
                    "continuity_penalty_weight": 1.0,
                },
                "form_continuity": {"enabled": False},
                "ranking_gap_hc": {
                    "enabled": rg_enabled,
                    "max_per_slip": 1,
                    "ev_slack": 0.015,
                },
            },
        },
        "risk": {"loss_streak_grade_a_only": 99},
        "combos": {"enabled": False},
    }


def _pack(
    p: float,
    *,
    summary: str = "solid research edge with multi-source confirmation",
    market_family: str = "",
) -> dict:
    sources = [
        {
            "url": f"https://example.com/{i}",
            "takeaway": "stats edge note for unit test pack",
            "kind": "stats",
        }
        for i in range(8)
    ]
    out: dict = {
        "p_model": p,
        "summary": summary if len(summary) >= 20 else (summary + " supporting research text"),
        "failure_modes": "test",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "expected full strength for unit test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": sources,
    }
    if market_family:
        out["market_family"] = market_family
    return out


def _rg_hc(
    match: str,
    team_side: str,
    *,
    p: float = 0.68,
    odds: float = 1.80,
    line: str = "-1.5",
) -> Candidate:
    """Ranking-gap handicap candidate (tagged via rank idioms in notes/summary)."""
    sel = f"Handikap 2-veis {line} (inkludert ekstra innings): {team_side} {line}"
    notes = "elite vs bottom ranking gap; clear strength gap on the run line"
    return Candidate(
        date="2026-07-26",
        match=match,
        selection=sel,
        decimal_odds=odds,
        sport="baseball",
        market_type="Handikap 2-veis",
        p_model=p,
        evidence=_pack(
            p,
            summary=notes + " multi-source confirmation of the mismatch",
            market_family="baseball_handicap",
        ),
        notes=notes,
    )


def _non_hc_ml(
    match: str,
    team: str,
    *,
    p: float = 0.66,
    odds: float = 1.75,
) -> Candidate:
    return Candidate(
        date="2026-07-26",
        match=match,
        selection=f"{team} to Win",
        decimal_odds=odds,
        sport="baseball",
        market_type="HUB",
        p_model=p,
        evidence=_pack(p, market_family="baseball_moneyline"),
        notes="moneyline lean from form and matchup research",
    )


def _mature_learning():
    """Avoid virgin explore boosts distorting sort order."""
    return {
        "enabled": True,
        "sports": {
            "baseball": {
                "n": 40,
                "stake_mult": 1.0,
                "ev_boost": 0.0,
                "roi": 0.02,
            }
        },
        "markets": {
            "Handicap": {"n": 40, "stake_mult": 1.0, "ev_boost": 0.0, "roi": 0.01},
            "Match result": {"n": 40, "stake_mult": 1.0, "ev_boost": 0.0, "roi": 0.01},
        },
        "bands": {},
        "updated_at": "2026-07-26T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Gate (A): same-match competitive non-HC always soft-skips RG (even first seat)
# ---------------------------------------------------------------------------
def test_gate_a_higher_sort_ev_rg_skipped_for_same_match_non_hc():
    """
    Same match: RG HC has higher sort_ev; non-HC within ev_slack.
    Pass 1/2 soft-skips RG with prefer same-match non-HC and accepts non-HC.

    EV math (haircut 0.05): RG p=0.64@1.80 → ~0.094; non p=0.635@1.80 → ~0.085
    delta ≈ 0.009 < ev_slack 0.015 so non is competitive.
    """
    match = "Milwaukee Brewers vs Colorado Rockies"
    # Higher p → higher EV / sort_ev for RG, but non-HC stays inside slack
    rg = _rg_hc(match, "Milwaukee Brewers", p=0.64, odds=1.80, line="-1.5")
    non = _non_hc_ml(match, "Milwaukee Brewers", p=0.635, odds=1.80)

    cfg = _cfg()
    phase = _phase(max_bets_per_round=2)
    picked, rejects = build_portfolio(
        cfg, [rg, non], phase, _risk(), [], learning=_mature_learning()
    )

    assert len(picked) == 1, f"max_per_match=1 → one seat: {[p.selection for p in picked]}"
    assert picked[0].ranking_gap_hc is False, (
        f"expected non-HC preferred over RG, got RG={picked[0].ranking_gap_hc} "
        f"sel={picked[0].selection} sort_evs="
        f"picked={picked[0].sort_ev}"
    )
    assert "to Win" in picked[0].selection
    reasons = [str(r.get("reason") or "") for r in rejects]
    assert any(
        "ranking_gap_hc: prefer same-match non-HC" in x for x in reasons
    ), f"expected gate A soft-skip reject, got: {reasons}"


def test_gate_a_disabled_when_rg_cfg_off():
    """With ranking_gap_hc.enabled=false, higher-EV RG can take the match seat."""
    match = "Milwaukee Brewers vs Colorado Rockies"
    rg = _rg_hc(match, "Milwaukee Brewers", p=0.64, odds=1.80, line="-1.5")
    non = _non_hc_ml(match, "Milwaukee Brewers", p=0.635, odds=1.80)

    cfg = _cfg(rg_enabled=False)
    phase = _phase(max_bets_per_round=2)
    picked, rejects = build_portfolio(
        cfg, [rg, non], phase, _risk(), [], learning=_mature_learning()
    )

    assert len(picked) == 1
    assert picked[0].ranking_gap_hc is True
    reasons = [str(r.get("reason") or "") for r in rejects]
    assert not any("ranking_gap_hc: prefer same-match non-HC" in x for x in reasons)


# ---------------------------------------------------------------------------
# Gate (B): soft max 1 RG when competitive non-RG remains
# ---------------------------------------------------------------------------
def test_gate_b_two_rg_plus_non_rg_at_most_one_rg_when_seats_filled_pass12():
    """
    Two RG (different matches) + one non-RG; max_bets=2.
    Pass 1/2: at most 1 RG (gate B soft-skips 2nd when non-RG peer remains).
    Final slip: 1 RG + 1 non-RG (no Pass 3 room for 2nd RG).

    Keep sort_ev of non-RG within 0.015 of both RGs so peer compare fires.
    """
    rg1 = _rg_hc(
        "Milwaukee Brewers vs Colorado Rockies",
        "Milwaukee Brewers",
        p=0.64,
        odds=1.80,
    )
    rg2 = _rg_hc(
        "New York Mets vs Los Angeles Dodgers",
        "Los Angeles Dodgers",
        p=0.638,
        odds=1.80,
        line="-1.5",
    )
    non = _non_hc_ml(
        "Texas Rangers vs Seattle Mariners",
        "Seattle Mariners",
        p=0.635,
        odds=1.80,
    )

    cfg = _cfg()
    phase = _phase(max_bets_per_round=2)
    picked, rejects = build_portfolio(
        cfg, [rg1, rg2, non], phase, _risk(), [], learning=_mature_learning()
    )

    assert len(picked) == 2, [p.selection for p in picked]
    n_rg = sum(1 for p in picked if p.ranking_gap_hc)
    n_non = sum(1 for p in picked if not p.ranking_gap_hc)
    assert n_rg == 1, f"expected exactly 1 RG on full Pass1/2 slip: {[(p.selection, p.ranking_gap_hc) for p in picked]}"
    assert n_non == 1, f"expected non-RG seat: {[p.selection for p in picked]}"
    reasons = [str(r.get("reason") or "") for r in rejects]
    assert any("soft cap 1 per slip" in x for x in reasons), reasons


# ---------------------------------------------------------------------------
# Pass 3 force-accept: 2nd RG when only RG left / no competitive non-RG
# ---------------------------------------------------------------------------
def test_pass3_can_take_second_rg_when_only_rg_remain():
    """
    Two ranking-gap HCs only (different matches), max_bets=2.
    Gate B has no competitive non-RG peer → both can place (Pass 1 takes first;
    second is not soft-skipped because no non-RG peer; also Pass 3 force path).
    """
    rg1 = _rg_hc(
        "Milwaukee Brewers vs Colorado Rockies",
        "Milwaukee Brewers",
        p=0.69,
        odds=1.80,
    )
    rg2 = _rg_hc(
        "New York Mets vs Los Angeles Dodgers",
        "Los Angeles Dodgers",
        p=0.67,
        odds=1.82,
    )

    cfg = _cfg()
    phase = _phase(max_bets_per_round=2)
    picked, rejects = build_portfolio(
        cfg, [rg1, rg2], phase, _risk(), [], learning=_mature_learning()
    )

    assert len(picked) == 2, f"never leave empty seats for soft RG cap: {[p.selection for p in picked]}"
    assert all(p.ranking_gap_hc for p in picked)
    reasons = [str(r.get("reason") or "") for r in rejects]
    # No gate-B soft skip without non-RG peers
    assert not any("soft cap 1 per slip" in x for x in reasons), reasons


def test_pass3_force_accepts_second_rg_when_non_rg_exhausted_by_match_cap():
    """
    max_bets=3 with 2 RG + 1 non-RG: Pass 1 takes 1 RG + non-RG (gate B soft-skips
    2nd RG). Seat remains → Pass 3 force-accepts 2nd RG (soft_ranking_gap_cap=False).
    """
    rg1 = _rg_hc(
        "Milwaukee Brewers vs Colorado Rockies",
        "Milwaukee Brewers",
        p=0.64,
        odds=1.80,
    )
    rg2 = _rg_hc(
        "New York Mets vs Los Angeles Dodgers",
        "Los Angeles Dodgers",
        p=0.638,
        odds=1.80,
    )
    non = _non_hc_ml(
        "Texas Rangers vs Seattle Mariners",
        "Seattle Mariners",
        p=0.635,
        odds=1.80,
    )

    cfg = _cfg()
    phase = _phase(max_bets_per_round=3)
    picked, rejects = build_portfolio(
        cfg,
        [rg1, rg2, non],
        phase,
        _risk(),
        [],
        learning=_mature_learning(),
    )

    assert len(picked) == 3, [p.selection for p in picked]
    n_rg = sum(1 for p in picked if p.ranking_gap_hc)
    n_non = sum(1 for p in picked if not p.ranking_gap_hc)
    assert n_rg == 2, f"Pass 3 should force 2nd RG: {[(p.selection, p.ranking_gap_hc) for p in picked]}"
    assert n_non == 1
    reasons = [str(r.get("reason") or "") for r in rejects]
    # Gate B soft-skipped the 2nd RG during Pass 1/2 before Pass 3 took it
    assert any("soft cap 1 per slip" in x for x in reasons), reasons


def test_ranking_gap_tag_present_on_scored_rg():
    """Sanity: is_ranking_gap_hc tags our fixtures at score time."""
    match = "Milwaukee Brewers vs Colorado Rockies"
    rg = _rg_hc(match, "Milwaukee Brewers", p=0.68)
    non = _non_hc_ml("Team A vs Team B", "Team A", p=0.65)
    cfg = _cfg()
    phase = _phase(max_bets_per_round=2)
    picked, _ = build_portfolio(
        cfg, [rg, non], phase, _risk(), [], learning=_mature_learning()
    )
    # One of each match → both placeable
    assert len(picked) == 2
    tags = {p.match: p.ranking_gap_hc for p in picked}
    assert tags[match] is True
    assert tags["Team A vs Team B"] is False
