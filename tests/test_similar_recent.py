"""Similar-recent soft demotion + composite sort_ev (ESR PR2)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.portfolio import Candidate, Recommendation, build_portfolio
from nt.recommend import refresh_state
from nt.similar_recent import (
    bet_type_macro,
    live_recent_window,
    parse_line,
    similar_recent_hits,
    similar_recent_penalty,
)
from nt.sport_taxonomy import normalize_sport


# --- Unit: parse_line / similarity ---


def test_parse_line_over_22_5():
    assert parse_line("Totalt antall games 22.5: Over 22.5") == 22.5
    assert parse_line("Over 22.5") == 22.5


def test_parse_line_comma_decimal():
    assert parse_line("Totalt antall mål - over/under 2,5: Under 2,5") == 2.5


def test_parse_line_ml_none():
    assert parse_line("Vinner: Darderi, Luciano") is None


def test_parse_line_1x2_market_type_not_phantom_line():
    """Digits inside 1X2 / Kampresultat must never become a phantom line."""
    assert parse_line("Hjemmeseier", "Kampresultat - 1X2") is None
    assert parse_line("Uavgjort", "1X2") is None
    assert parse_line("Borte", "Kampresultat - 1X2") is None
    assert parse_line("1", "Kampresultat - 1X2") is None
    assert parse_line("2", "1X2") is None
    assert parse_line("X", "1X2") is None


def test_include_ml_false_skips_ml():
    recent = [
        {
            "match": "A vs B",
            "selection": "Vinner: Player A",
            "sport": "tennis",
            "result": "Loss",
            "market_type": "Vinner",
            "date": "2026-07-24",
        }
    ]
    hits = similar_recent_hits(
        sport="tennis",
        selection="Vinner: Player C",
        market_type="Vinner",
        market_family_key="tennis_ml",
        match="C vs D",
        recent_rows=recent,
        include_ml=False,
    )
    assert hits == []


def test_include_ml_false_skips_football_1x2_kampresultat():
    """Realistic NT football 1X2 must not demote under include_ml=false (Issue 1)."""
    recent = [
        {
            "match": "Old FC vs Rival",
            "selection": "Hjemmeseier",
            "sport": "football",
            "result": "Loss",
            "market_type": "Kampresultat - 1X2",
            "date": "2026-07-24",
        }
    ]
    hits = similar_recent_hits(
        sport="football",
        selection="Borte",
        market_type="Kampresultat - 1X2",
        market_family_key="football_1x2",
        match="New FC vs Other",
        recent_rows=recent,
        include_ml=False,
    )
    assert hits == []
    # parse_line alone must not invent 2.0 from 1X2
    from nt.similar_recent import parse_line as pl

    assert pl("Hjemmeseier", "Kampresultat - 1X2") is None


def test_line_tolerance_tennis_21_5_vs_22_5():
    recent = [
        {
            "match": "Van Assche vs Gaston",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "market_type": "Totalt antall games",
            "date": "2026-07-24",
        }
    ]
    hits = similar_recent_hits(
        sport="tennis",
        selection="Totalt antall games 21.5: Over 21.5",
        market_type="Totalt antall games",
        market_family_key="tennis_totals",
        recent_rows=recent,
        line_tolerance=1.0,
        include_ml=False,
    )
    assert len(hits) == 1


def test_different_sport_not_similar():
    recent = [
        {
            "match": "Foo vs Bar",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "date": "2026-07-24",
        }
    ]
    hits = similar_recent_hits(
        sport="football",
        selection="Totalt antall mål - over/under 2.5: Over 2.5",
        market_family_key="football_totals",
        recent_rows=recent,
        line_tolerance=1.0,
        include_ml=False,
    )
    assert hits == []


def test_era_archive_not_in_similar_window():
    rows = [
        {
            "match": "Archive vs Z",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "source": "era_archive",
            "date": "2026-07-25",
        },
        {
            "match": "Live vs Y",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "date": "2026-07-24",
        },
    ]
    window = live_recent_window(rows, window=12, include_pending=True)
    assert len(window) == 1
    assert window[0]["match"] == "Live vs Y"
    hits = similar_recent_hits(
        sport="tennis",
        selection="Totalt antall games 22.5: Over 22.5",
        market_family_key="tennis_totals",
        recent_rows=window,
        include_ml=False,
    )
    assert len(hits) == 1
    assert hits[0]["match"] == "Live vs Y"


def test_penalty_reason_string_style():
    recent = [
        {
            "match": "Van Assche vs Gaston",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "date": "2026-07-24",
        },
        {
            "match": "Blockx vs Darderi",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "date": "2026-07-23",
        },
    ]
    pen, reason, hits = similar_recent_penalty(
        sport="tennis",
        selection="Totalt antall games 21.5: Under 21.5",
        market_type="Totalt antall games",
        market_family_key="tennis_totals",
        recent_rows=recent,
        cfg={
            "enabled": True,
            "window": 12,
            "include_ml": False,
            "line_tolerance": 1.0,
            "soft_ev_penalty": 0.012,
            "loss_pattern_extra_penalty": 0.010,
        },
    )
    assert len(hits) == 2
    # Scaled soft pen: soft*min(n,3) + loss_extra*min(n_loss,3) = 0.012*2 + 0.010*2
    assert pen == 0.044
    assert reason.startswith(
        "similar_recent: similar to recent tennis_totals – demoted"
    )
    assert "2 in last 12" in reason
    assert "Loss" in reason


def test_reason_window_uses_clamped_value():
    """Reason string must report the same clamped window as the search (Issue 2)."""
    recent = [
        {
            "match": f"M{i} vs Z",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "date": f"2026-07-{10 + i:02d}",
            "market_type": "Totalt antall games",
        }
        for i in range(5)
    ]
    # Config asks for 20 → clamp to 15 in reason
    pen, reason, hits = similar_recent_penalty(
        sport="tennis",
        selection="Totalt antall games 22.5: Over 22.5",
        market_type="Totalt antall games",
        market_family_key="tennis_totals",
        recent_rows=recent,
        cfg={
            "enabled": True,
            "window": 20,
            "include_ml": False,
            "line_tolerance": 1.0,
            "soft_ev_penalty": 0.012,
            "loss_pattern_extra_penalty": 0.010,
        },
    )
    assert hits
    assert "in last 15" in reason
    assert "in last 20" not in reason
    # Config asks for 5 → clamp to 10
    _, reason5, _ = similar_recent_penalty(
        sport="tennis",
        selection="Totalt antall games 22.5: Over 22.5",
        market_type="Totalt antall games",
        market_family_key="tennis_totals",
        recent_rows=recent,
        cfg={
            "enabled": True,
            "window": 5,
            "include_ml": False,
            "line_tolerance": 1.0,
            "soft_ev_penalty": 0.012,
            "loss_pattern_extra_penalty": 0.010,
        },
    )
    assert "in last 10" in reason5
    assert "in last 5)" not in reason5


def test_bet_type_macro_buckets():
    assert bet_type_macro(market_family_key="tennis_totals") == "total"
    assert bet_type_macro(market_family_key="tennis_ml") == "ml"
    assert bet_type_macro(market_family_key="football_handicap") == "handicap"
    assert bet_type_macro(market_family_key="player_props") == "prop"


# --- Portfolio integration ---


def _evidence(p: float = 0.62) -> dict:
    return {
        "p_model": p,
        "summary": (
            "Clear core: form edge and matchup history support this selection; "
            "H2H checked and recent form favours the line."
        ),
        "h2h": "H2H 3-1 last meetings; matchup assessed",
        "form": "Won last 4; ranking/seed gap supports edge",
        "failure_modes": "test",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "expected full strength for unit test",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "sources": [
            {"url": f"https://example.com/{i}", "takeaway": "t"} for i in range(7)
        ],
    }


def _cand(
    match: str,
    selection: str,
    sport: str,
    *,
    odds: float = 1.90,
    p: float = 0.62,
    market_type: str = "",
) -> Candidate:
    return Candidate(
        date="2026-07-25",
        match=match,
        selection=selection,
        decimal_odds=odds,
        sport=sport,
        market_type=market_type,
        p_model=p,
        evidence=_evidence(p),
    )


def _portfolio_cfg(**div_overrides) -> dict:
    cfg = load_config()
    cfg = dict(cfg)
    sel = dict(cfg.get("selection") or {})
    ev = dict(sel.get("evidence") or {})
    fh = dict(ev.get("forced_hierarchy") or {})
    fh["enabled"] = False
    ev["forced_hierarchy"] = fh
    ev["shadow_mode"] = True
    sel["evidence"] = ev
    sel["odds_confidence"] = {"enabled": False}
    cfg["selection"] = sel
    # Avoid grade-A-only after loss streaks in hist fixtures
    risk = dict(cfg.get("risk") or {})
    risk["loss_streak_grade_a_only"] = 0
    cfg["risk"] = risk
    learn = dict(cfg.get("learning") or {})
    div = dict(learn.get("diversification") or {})
    div["max_per_sport"] = 5
    div["max_per_market"] = 9
    div["max_per_script_family"] = 9
    div["max_per_band"] = 9
    div["max_per_league"] = 9
    div["max_per_ko_window"] = 99
    div["max_per_market_family"] = 5
    div["max_football_per_round"] = 1
    div["prefer_explore_first"] = True
    div["prefer_bet_type_spread"] = True
    sr = dict(div.get("similar_recent") or {})
    sr.update(
        {
            "enabled": True,
            "window": 12,
            "include_pending": True,
            "include_ml": False,
            "line_tolerance": 1.0,
            "soft_ev_penalty": 0.012,
            "loss_pattern_extra_penalty": 0.010,
            "hard_reject_if_count": None,
        }
    )
    div["similar_recent"] = sr
    sort = dict(div.get("sort") or {})
    sort.update(
        {
            "similar_penalty_weight": 1.0,
            "macro_underrep_bonus": 0.0,  # isolate similar in demotion tests
            "explore_tiebreak": True,
        }
    )
    div["sort"] = sort
    div.update(div_overrides)
    learn["diversification"] = div
    learn["enabled"] = False
    cfg["learning"] = learn
    combos = dict(cfg.get("combos") or {})
    combos["enabled"] = False
    cfg["combos"] = combos
    return cfg


def _risk_phase(cfg: dict, *, max_bets: int = 4):
    _, phase, risk = refresh_state(cfg)
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 500.0
    risk["daily_risk_cap_nok"] = 500.0
    risk["stopped"] = False
    phase = dict(phase)
    phase["max_bets_per_round"] = max_bets
    phase["research_only"] = False
    phase["stake_min"] = 10
    phase["stake_max"] = 20
    return phase, risk


def test_cross_run_demotion_after_tennis_totals_losses():
    """
    After 2 settled tennis_totals losses, same-shape candidate is soft-demoted
    (visible reason + lower sort_ev) so a different-family +EV is preferred.
    """
    cfg = _portfolio_cfg()
    phase, risk = _risk_phase(cfg, max_bets=1)

    hist = [
        {
            "match": "Van Assche vs Gaston",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "decimal_odds": "1.90",
            "odds_band": "1.8-2.2",
            "market_type": "Totalt antall games",
            "date": "2026-07-24",
            "p_l_nok": "-10",
            "stake_nok": "10",
        },
        {
            "match": "Blockx vs Darderi",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "decimal_odds": "1.90",
            "odds_band": "1.8-2.2",
            "market_type": "Totalt antall games",
            "date": "2026-07-23",
            "p_l_nok": "-10",
            "stake_nok": "10",
        },
    ]
    # haircut 0.03: p=0.58 → EV≈0.069; p=0.57 → EV≈0.051; after pen tennis sort_ev≈0.047
    tennis = _cand(
        "New Tennis vs Z",
        "Totalt antall games 22.5: Over 22.5",
        "tennis",
        odds=1.90,
        p=0.58,
        market_type="Totalt antall games",
    )
    darts = _cand(
        "Darts Ace vs King",
        "Handikap: Ace -1.5",
        "darts",
        odds=1.90,
        p=0.57,
        market_type="Handikap",
    )

    picked, rejects = build_portfolio(
        cfg, [tennis, darts], phase, risk, hist, learning={}
    )
    assert len(picked) == 1, f"picked={picked!r} rejects={rejects!r}"
    assert picked[0].sport == "darts", (
        f"expected demotion to prefer darts; got "
        f"sport={picked[0].sport} fam={picked[0].market_family} "
        f"sort_ev={picked[0].sort_ev} notes={picked[0].notes}"
    )
    # Inspect annotations with more seats
    phase2, risk2 = _risk_phase(cfg, max_bets=4)
    picked2, _ = build_portfolio(
        cfg, [tennis, darts], phase2, risk2, hist, learning={}
    )
    tennis_pick = next(
        (p for p in picked2 if "games" in (p.selection or "").lower()), None
    )
    assert tennis_pick is not None
    assert "similar_recent" in (tennis_pick.similar_recent_reason or tennis_pick.notes)
    assert "similar to recent" in (
        tennis_pick.similar_recent_reason or tennis_pick.notes
    )
    assert tennis_pick.ev > 0
    if tennis_pick.sort_ev is not None:
        assert tennis_pick.sort_ev < tennis_pick.ev


def test_sort_polarity_equal_sort_ev_non_football_before_football():
    """equal sort_ev → non-football before football under reverse=True."""
    t = Recommendation(
        match="T vs U",
        selection="Over 22.5",
        decimal_odds=1.9,
        stake_nok=10,
        ev=0.05,
        grade="B",
        odds_band="1.8-2.2",
        sport="tennis",
        market_type="",
        p_model=0.55,
        notes="",
        sort_ev=0.05,
        explore=False,
    )
    f = Recommendation(
        match="F vs G",
        selection="Over 2.5",
        decimal_odds=1.9,
        stake_nok=10,
        ev=0.05,
        grade="B",
        odds_band="1.8-2.2",
        sport="football",
        market_type="",
        p_model=0.55,
        notes="",
        sort_ev=0.05,
        explore=False,
    )
    scored = [f, t]
    scored.sort(
        key=lambda r: (
            float(r.sort_ev if r.sort_ev is not None else r.ev),
            1 if r.explore else 0,
            1 if normalize_sport(r.sport, default="unknown") != "football" else 0,
            float(r.ev),
        ),
        reverse=True,
    )
    assert scored[0].sport == "tennis"
    assert scored[1].sport == "football"


def test_multi_pass_soft_football_fill():
    """
    1 non-football + 3 football all +EV, max_bets≥2, max_football_per_round=1
    → Pass 1 takes NF; Pass 2 ≤1 FB soft; Pass 3 fill-up may take more FB.
    Never empty seats solely because football was deferred.
    """
    cfg = _portfolio_cfg()
    div = cfg["learning"]["diversification"]
    div["similar_recent"] = dict(div["similar_recent"], enabled=False)
    div["max_football_per_round"] = 1
    div["max_per_sport"] = 4
    div["max_per_market_family"] = 4
    phase, risk = _risk_phase(cfg, max_bets=4)

    nf = _cand(
        "Tennis A vs B",
        "Totalt antall games 22.5: Over 22.5",
        "tennis",
        p=0.60,
        market_type="Totalt antall games",
    )
    fbs = [
        _cand(
            f"FB{i} vs Opp",
            "Begge lag scorer: Nei",
            "football",
            p=0.60,
            market_type="BTTS",
        )
        for i in range(3)
    ]
    picked, rejects = build_portfolio(
        cfg, [nf] + fbs, phase, risk, [], learning={}
    )
    assert len(picked) >= 2, (
        f"multi-pass should fill seats; picked={picked!r} rejects={rejects!r}"
    )
    sports = [normalize_sport(p.sport, default="unknown") for p in picked]
    assert "tennis" in sports, f"Pass 1 should take non-football: {sports}"
    n_fb = sum(1 for s in sports if s == "football")
    assert n_fb >= 1, f"expected football fill-up seats: {sports}"
    assert len(picked) >= 3, (
        f"fill-up should not leave empty seats; picked={len(picked)} sports={sports}"
    )


def test_include_ml_false_portfolio_no_demote_on_ml_loss():
    """ML loss in window must not demote another ML when include_ml=false."""
    cfg = _portfolio_cfg()
    phase, risk = _risk_phase(cfg, max_bets=2)
    hist = [
        {
            "match": "Old vs Z",
            "selection": "Vinner: Old Player",
            "sport": "tennis",
            "result": "Loss",
            "decimal_odds": "1.80",
            "market_type": "Vinner",
            "date": "2026-07-24",
            "p_l_nok": "-10",
            "stake_nok": "10",
        }
    ]
    ml = _cand(
        "New vs Y",
        "Vinner: New Player",
        "tennis",
        p=0.62,
        market_type="Vinner",
    )
    picked, _ = build_portfolio(cfg, [ml], phase, risk, hist, learning={})
    assert len(picked) == 1
    assert not (picked[0].similar_recent_reason or "").strip(), (
        f"ML should not get similar_recent demotion: {picked[0].similar_recent_reason!r}"
    )
    if picked[0].sort_ev is not None:
        assert abs(picked[0].sort_ev - picked[0].ev) < 0.001


def test_include_ml_false_portfolio_football_1x2_no_demote():
    """Football Hjemmeseier + Kampresultat - 1X2 loss must not demote next 1X2."""
    cfg = _portfolio_cfg()
    phase, risk = _risk_phase(cfg, max_bets=2)
    hist = [
        {
            "match": "Old FC vs Rival",
            "selection": "Hjemmeseier",
            "sport": "football",
            "result": "Loss",
            "decimal_odds": "1.85",
            "market_type": "Kampresultat - 1X2",
            "date": "2026-07-24",
            "p_l_nok": "-10",
            "stake_nok": "10",
        }
    ]
    ml = _cand(
        "New FC vs Other",
        "Hjemmeseier",
        "football",
        p=0.62,
        market_type="Kampresultat - 1X2",
    )
    picked, _ = build_portfolio(cfg, [ml], phase, risk, hist, learning={})
    assert len(picked) == 1, f"picked={picked!r}"
    assert not (picked[0].similar_recent_reason or "").strip(), (
        f"1X2 must not demote under include_ml=false: "
        f"reason={picked[0].similar_recent_reason!r} notes={picked[0].notes!r}"
    )
    if picked[0].sort_ev is not None:
        assert abs(picked[0].sort_ev - picked[0].ev) < 0.001


def test_era_archive_does_not_demote_via_similar():
    """era_archive losses must not appear in similar window / demote live candidates."""
    cfg = _portfolio_cfg()
    phase, risk = _risk_phase(cfg, max_bets=1)
    hist = [
        {
            "match": f"Arch {i} vs Z",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "source": "era_archive",
            "date": f"2026-07-{20 + i:02d}",
            "p_l_nok": "-10",
            "stake_nok": "10",
        }
        for i in range(5)
    ]
    tennis = _cand(
        "Live vs Y",
        "Totalt antall games 22.5: Over 22.5",
        "tennis",
        p=0.62,
        market_type="Totalt antall games",
    )
    picked, _ = build_portfolio(cfg, [tennis], phase, risk, hist, learning={})
    assert len(picked) == 1
    assert not (picked[0].similar_recent_reason or "").strip(), (
        f"era_archive must not demote: reason={picked[0].similar_recent_reason!r} "
        f"notes={picked[0].notes!r}"
    )


def test_explore_cannot_override_sort_ev_primary():
    """
    Within a pass: higher sort_ev beats explore flag on a demoted same-family line.
    """
    cfg = _portfolio_cfg()
    div = cfg["learning"]["diversification"]
    div["max_per_market_family"] = 5
    div["max_per_sport"] = 5
    phase, risk = _risk_phase(cfg, max_bets=1)

    hist = [
        {
            "match": "Old1 vs Z",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Loss",
            "date": "2026-07-24",
            "market_type": "Totalt antall games",
            "p_l_nok": "-10",
            "stake_nok": "10",
        },
        {
            "match": "Old2 vs Z",
            "selection": "Totalt antall games 22.5: Under 22.5",
            "sport": "tennis",
            "result": "Loss",
            "date": "2026-07-23",
            "market_type": "Totalt antall games",
            "p_l_nok": "-10",
            "stake_nok": "10",
        },
    ]
    tennis = _cand(
        "Tennis Clone vs Z",
        "Totalt antall games 22.5: Over 22.5",
        "tennis",
        p=0.58,
        market_type="Totalt antall games",
    )
    darts = _cand(
        "Darts Pro vs Am",
        "Handikap: Pro -1.5",
        "darts",
        p=0.57,
        market_type="Handikap",
    )
    picked, _ = build_portfolio(
        cfg, [tennis, darts], phase, risk, hist, learning={}
    )
    assert len(picked) == 1
    assert picked[0].sport == "darts", (
        f"sort_ev demotion should prefer darts over demoted tennis; "
        f"got {picked[0].sport} sort_ev={picked[0].sort_ev} notes={picked[0].notes}"
    )
