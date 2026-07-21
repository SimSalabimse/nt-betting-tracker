from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.analytics import (
    band_stats,
    date_range_bounds,
    deep_dive,
    equity_series,
    group_stats,
    infer_market,
    max_drawdown,
    overall_stats,
    slice_rows_by_date,
    weekday_stats,
)
from nt.bankroll import compute_bankroll
from nt.bets_io import band_roi_stats, load_bets
from nt.config import load_config


def test_equity_series_ends_at_bankroll():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    series = equity_series(rows, b["baseline_nok"])
    assert series
    assert abs(series[-1]["equity"] - b["equity_nok"]) < 0.02
    assert abs(series[-1]["cum_pl"] - b["realized_pl_nok"]) < 0.02


def test_band_stats_matches_bets_io():
    rows = load_bets(ROOT / "data/bets.csv")
    a = band_stats(rows)
    b = band_roi_stats(rows)
    assert set(a.keys()) == set(b.keys())
    for k in a:
        assert abs(a[k]["roi"] - b[k]["roi"]) < 1e-9
        assert a[k]["n"] == b[k]["n"]


def test_overall_stats_settled_count():
    rows = load_bets(ROOT / "data/bets.csv")
    s = overall_stats(rows)
    assert s["n_settled"] + s["n_pending"] == len(rows)
    assert s["wins"] + s["losses"] + s["refunds"] == s["n_settled"]
    assert s["n_settled"] >= 193


def test_group_stats_sport_sums():
    rows = load_bets(ROOT / "data/bets.csv")
    settled = [r for r in rows if r.get("result") != "Pending"]
    by_sport = group_stats(rows, "sport")
    total_n = sum(v["n"] for v in by_sport.values())
    assert total_n == len(settled)


def test_max_drawdown_non_negative():
    cfg = load_config()
    rows = load_bets(ROOT / "data/bets.csv")
    series = equity_series(rows, cfg["bankroll"]["baseline_nok"])
    assert max_drawdown(series) >= 0


def test_infer_market_totals():
    assert infer_market("Totalt antall mål Over 2.5") == "Totals Over"
    assert infer_market("Under 2.5 Goals") == "Totals Under"
    assert infer_market("Over 2.5", "Totalt antall mål - over/under 2.5") == "Totals Over"
    assert infer_market("Begge lag scorer Ja") == "BTTS"
    assert infer_market("Canada to Win") == "Match result"
    assert infer_market("Japan +1") == "Handicap"
    assert infer_market("Nakashima -1.5 sets") == "Set handicap"
    assert infer_market("Faze Clan -1.5 (maps)") == "Map handicap"
    assert infer_market("Argentina holder nullen Ja") == "Clean sheet"
    assert infer_market("Draw") == "Match result"
    assert infer_market("Jasper Philipsen top 3") == "Place / outright"
    assert infer_market("Blir det Safety Car Periode? Ja") == "Motorsport"


def test_weekday_stats_has_days():
    rows = load_bets(ROOT / "data/bets.csv")
    settled = [r for r in rows if r.get("result") != "Pending"]
    wd = weekday_stats(rows)
    assert sum(v["n"] for v in wd.values()) == len(settled)
    assert wd


def test_deep_dive_payload():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    dive = deep_dive(
        rows,
        b["baseline_nok"],
        cfg=cfg,
        phase={"phase_id": "1A", "next": "1B", "equity_nok": b["equity_nok"], "settled_count": b["settled_count"]},
    )
    assert dive["overall"]["n_settled"] == b["settled_count"]
    assert dive["by_market"]
    assert dive["by_weekday"]
    assert dive["rolling_20"]
    assert dive["best_worst"]["best"]
    assert dive["concentration"]["football_pct"] > 0.4


def test_date_range_bounds_1w():
    from datetime import date

    d_from, d_to, label = date_range_bounds("1w", today=date(2026, 7, 13), era_start="2026-06-28")
    assert label == "1 week"
    assert d_to == "2026-07-13"
    assert d_from == "2026-07-07"


def test_deep_dive_range_filters():
    cfg = load_config()
    b = compute_bankroll(cfg)
    rows = load_bets(ROOT / "data/bets.csv")
    d_from, d_to, lab = date_range_bounds("2w", era_start=cfg["bankroll"].get("era_start"))
    dive = deep_dive(
        rows,
        b["baseline_nok"],
        cfg=cfg,
        phase=b and {"phase_id": "1A", "equity_nok": b["equity_nok"], "settled_count": b["settled_count"]},
        date_from=d_from,
        date_to=d_to,
        range_key="2w",
        range_label=lab,
    )
    assert dive["range_key"] == "2w"
    assert dive["period_n"] <= b["settled_count"]
    sliced = slice_rows_by_date(rows, d_from, d_to)
    assert dive["period_n"] == len(sliced)
