"""market_family NO/EN matrix + hard max_per_market_family in portfolio."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.config import load_config
from nt.market_family import market_family
from nt.portfolio import Candidate, build_portfolio
from nt.portfolio_correlation import market_family as reexport_mf
from nt.recommend import refresh_state


# --- Matrix: real NT selection strings ---


def test_matrix_tennis_totals_over_22_5():
    assert (
        market_family("tennis", "Totalt antall games 22.5: Over 22.5")
        == "tennis_totals"
    )


def test_matrix_tennis_totals_under_22_5():
    assert (
        market_family("tennis", "Totalt antall games 22.5: Under 22.5")
        == "tennis_totals"
    )


def test_matrix_tennis_totals_over_21_5_same_family():
    assert (
        market_family("tennis", "Totalt antall games 21.5: Over 21.5")
        == "tennis_totals"
    )


def test_matrix_tennis_totals_over_23_5_same_family():
    assert (
        market_family("tennis", "Totalt antall games 23.5: Over 23.5")
        == "tennis_totals"
    )


def test_matrix_football_totals_over_2_5():
    assert (
        market_family(
            "football",
            "Totalt antall mål - over/under 2.5: Over 2.5",
        )
        == "football_totals"
    )


def test_matrix_football_totals_under_comma():
    assert (
        market_family(
            "football",
            "Totalt antall mål - over/under 2,5: Under 2,5",
        )
        == "football_totals"
    )


def test_matrix_football_btts():
    assert market_family("football", "Begge lag scorer: Nei") == "football_btts"


def test_matrix_tennis_ml_vinner():
    assert market_family("tennis", "Vinner: Darderi, Luciano") == "tennis_ml"


def test_matrix_tennis_handicap():
    assert (
        market_family("tennis", "Sett handikap: Player A -1.5")
        == "tennis_handicap"
        or market_family(
            "tennis",
            "Parti handikap 1.5: Graham, Liam +1.5",
        )
        == "tennis_handicap"
    )


def test_matrix_football_period_1h():
    fam = market_family("football", "1. omgang hub: Uavgjort")
    assert fam in ("football_period", "football_period_totals")


def test_matrix_football_period_totals():
    fam = market_family(
        "football",
        "1. omgang totalt antall mål over/under 0.5: Over 0.5",
    )
    assert fam == "football_period_totals"


def test_matrix_esports_map_totals():
    assert (
        market_family("esports", "Totalt antall kart over/under 2.5: Over 2.5")
        == "esports_map_totals"
        or market_family("esports", "Maps total Over 2.5") == "esports_map_totals"
    )


def test_matrix_darts_180s():
    assert market_family("darts", "180s Over 4.5") == "darts_180s"


def test_matrix_unknown_sport_games_hint():
    assert market_family("unknown", "Over 22.5 games") == "tennis_totals"


def test_matrix_empty_selection():
    assert market_family("unknown", "") == "other"


def test_reexport_from_portfolio_correlation():
    assert reexport_mf is market_family
    assert reexport_mf("tennis", "Totalt antall games 22.5: Over 22.5") == "tennis_totals"


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


def _tennis_ou_cand(match: str, side: str = "Over", line: str = "22.5") -> Candidate:
    sel = f"Totalt antall games {line}: {side} {line}"
    # p_model high enough for +EV after haircut at ~1.90
    p = 0.62
    return Candidate(
        date="2026-07-25",
        match=match,
        selection=sel,
        decimal_odds=1.90,
        sport="tennis",
        market_type="Totalt antall games",
        p_model=p,
        evidence=_evidence(p),
    )


def _portfolio_cfg_family_test() -> dict:
    """Raise sport/market/script so only max_per_market_family binds."""
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
    learn = dict(cfg.get("learning") or {})
    div = dict(learn.get("diversification") or {})
    div["max_per_sport"] = 5  # isolate family
    div["max_per_market"] = 9
    div["max_per_script_family"] = 9
    div["max_per_band"] = 9
    div["max_per_league"] = 9
    div["max_per_ko_window"] = 99
    div["max_per_market_family"] = 2
    div["max_football_per_round"] = 9
    learn["diversification"] = div
    learn["enabled"] = False
    cfg["learning"] = learn
    # Disable combos so seat fill is singles-only
    combos = dict(cfg.get("combos") or {})
    combos["enabled"] = False
    cfg["combos"] = combos
    return cfg


def test_third_tennis_totals_rejected_by_market_family():
    """
    3× tennis O22.5 with max_per_sport≥3 → 3rd hard-rejects on market_family.
    (Sport/script/market caps raised so family is the binding constraint.)
    """
    cfg = _portfolio_cfg_family_test()
    _, phase, risk = refresh_state(cfg)
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 500.0
    risk["daily_risk_cap_nok"] = 500.0
    risk["stopped"] = False
    phase = dict(phase)
    phase["max_bets_per_round"] = 5
    phase["research_only"] = False

    cands = [
        _tennis_ou_cand("Van Assche vs Gaston", "Over", "22.5"),
        _tennis_ou_cand("Blockx vs Darderi", "Over", "22.5"),
        _tennis_ou_cand("Player X vs Player Y", "Over", "22.5"),
    ]
    picked, rejects = build_portfolio(cfg, cands, phase, risk, [], learning={})
    assert len(picked) == 2, f"expected 2 accepted, got {picked!r} rejects={rejects!r}"
    fam_rejects = [
        r
        for r in rejects
        if "market_family" in str(r.get("reason", "")).lower()
        and "tennis_totals" in str(r.get("reason", ""))
    ]
    assert fam_rejects, f"expected family reject, rejects={rejects!r}"
    reason = str(fam_rejects[0]["reason"])
    assert "max 2" in reason
    assert "tennis_totals" in reason


def test_era_archive_open_rows_do_not_seed_family():
    """era_archive open rows must not consume market_family seats."""
    cfg = _portfolio_cfg_family_test()
    _, phase, risk = refresh_state(cfg)
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 500.0
    risk["daily_risk_cap_nok"] = 500.0
    risk["stopped"] = False
    phase = dict(phase)
    phase["max_bets_per_round"] = 5
    phase["research_only"] = False

    archive_open = [
        {
            "match": f"Archive {i} vs Z",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Pending",
            "decimal_odds": "1.90",
            "odds_band": "1.8-2.2",
            "market_type": "Totalt antall games",
            "source": "era_archive",
        }
        for i in range(5)
    ]
    cands = [
        _tennis_ou_cand("Live A vs B", "Over", "22.5"),
        _tennis_ou_cand("Live C vs D", "Over", "22.5"),
    ]
    picked, rejects = build_portfolio(
        cfg, cands, phase, risk, archive_open, learning={}
    )
    assert len(picked) == 2, (
        f"era_archive should be no-op for seeds; "
        f"picked={picked!r} rejects={rejects!r}"
    )


def test_over_and_under_share_tennis_totals_family():
    """O22.5 and U21.5 both map to tennis_totals; open O+U seeds block a third Over."""
    assert market_family("tennis", "Totalt antall games 22.5: Over 22.5") == "tennis_totals"
    assert market_family("tennis", "Totalt antall games 21.5: Under 21.5") == "tennis_totals"

    cfg = _portfolio_cfg_family_test()
    _, phase, risk = refresh_state(cfg)
    risk = dict(risk)
    risk["can_bet"] = True
    risk["remaining_risk_nok"] = 500.0
    risk["daily_risk_cap_nok"] = 500.0
    risk["stopped"] = False
    phase = dict(phase)
    phase["max_bets_per_round"] = 5
    phase["research_only"] = False

    open_mixed = [
        {
            "match": "Open O vs Z",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "sport": "tennis",
            "result": "Pending",
            "decimal_odds": "1.90",
            "odds_band": "1.8-2.2",
            "market_type": "Totalt antall games",
        },
        {
            "match": "Open U vs Z",
            "selection": "Totalt antall games 21.5: Under 21.5",
            "sport": "tennis",
            "result": "Pending",
            "decimal_odds": "1.90",
            "odds_band": "1.8-2.2",
            "market_type": "Totalt antall games",
        },
    ]
    cands = [_tennis_ou_cand("New O vs Y", "Over", "23.5")]
    picked, rejects = build_portfolio(
        cfg, cands, phase, risk, open_mixed, learning={}
    )
    assert picked == []
    assert any(
        "tennis_totals" in str(r.get("reason", ""))
        and "market_family" in str(r.get("reason", ""))
        for r in rejects
    ), f"rejects={rejects!r}"
