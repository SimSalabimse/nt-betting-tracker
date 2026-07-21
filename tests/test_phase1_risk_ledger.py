"""Phase 1: settlement-day risk P/L + Abandoned / place-ack ledger states."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import (
    is_open_risk,
    is_performance_settled,
    pending_stake_total,
    settlement_calendar_day,
    settled_count,
    settled_pl_sum,
    validate_bets,
)
from nt.risk import day_pending_risk, day_realized_pl, evaluate_risk


def test_settlement_calendar_day_prefers_updated_at_oslo():
    # 2026-07-20T22:30:00Z = 2026-07-21 00:30 CEST → settlement day 2026-07-21
    row = {
        "date": "2026-07-20",  # match kickoff day (must NOT win)
        "updated_at": "2026-07-20T22:30:00Z",
        "result": "Loss",
        "p_l_nok": "-10",
    }
    assert settlement_calendar_day(row) == "2026-07-21"


def test_day_realized_pl_uses_settlement_day_not_match_date():
    rows = [
        {
            "date": "2026-07-19",  # match day yesterday
            "updated_at": "2026-07-20T10:00:00Z",  # settled today CEST
            "result": "Loss",
            "p_l_nok": "-11",
            "stake_nok": "11",
        },
        {
            "date": "2026-07-20",
            "updated_at": "2026-07-20T12:00:00Z",
            "result": "Win",
            "p_l_nok": "7.2",
            "stake_nok": "10",
        },
        {
            # Match today but settled tomorrow — must NOT count for 2026-07-20
            "date": "2026-07-20",
            "updated_at": "2026-07-21T08:00:00Z",
            "result": "Loss",
            "p_l_nok": "-10",
            "stake_nok": "10",
        },
    ]
    pl = day_realized_pl(rows, day="2026-07-20")
    assert abs(pl - (-11 + 7.2)) < 0.01


def test_day_realized_pl_ignores_abandoned_and_open():
    rows = [
        {
            "date": "2026-07-20",
            "updated_at": "2026-07-20T15:00:00Z",
            "result": "Abandoned",
            "p_l_nok": "0",
            "stake_nok": "12",
        },
        {
            "date": "2026-07-20",
            "updated_at": "2026-07-20T15:00:00Z",
            "result": "Pending",
            "p_l_nok": "",
            "stake_nok": "10",
        },
        {
            "date": "2026-07-20",
            "updated_at": "2026-07-20T15:00:00Z",
            "result": "Loss",
            "p_l_nok": "-10",
            "stake_nok": "10",
        },
    ]
    assert day_realized_pl(rows, day="2026-07-20") == -10.0


def test_pending_risk_includes_confirmed_excludes_abandoned():
    rows = [
        {"result": "Pending", "stake_nok": "10"},
        {"result": "ConfirmedPlaced", "stake_nok": "12"},
        {"result": "Abandoned", "stake_nok": "12", "p_l_nok": "0"},
        {"result": "Win", "stake_nok": "10", "p_l_nok": "8"},
    ]
    assert pending_stake_total(rows) == 22.0
    assert day_pending_risk(rows) == 22.0
    assert is_open_risk("Pending") and is_open_risk("ConfirmedPlaced")
    assert not is_open_risk("Abandoned")


def test_settled_count_and_pl_exclude_open_and_abandoned_from_phase_sample():
    rows = [
        {"result": "Pending", "stake_nok": "10", "p_l_nok": ""},
        {"result": "ConfirmedPlaced", "stake_nok": "10", "p_l_nok": ""},
        {"result": "Abandoned", "stake_nok": "12", "p_l_nok": "0"},
        {"result": "Win", "stake_nok": "10", "p_l_nok": "8"},
        {"result": "Loss", "stake_nok": "10", "p_l_nok": "-10"},
        {"result": "Refunded", "stake_nok": "12", "p_l_nok": "0"},
    ]
    assert settled_count(rows) == 3  # Win, Loss, Refunded
    assert settled_pl_sum(rows) == -2.0  # 8 - 10 + 0
    assert is_performance_settled("Win")
    assert not is_performance_settled("Abandoned")


def test_validate_accepts_new_states():
    rows = [
        {
            "bet_id": "a1",
            "date": "2026-07-20",
            "match": "A vs B",
            "selection": "A",
            "decimal_odds": "1.80",
            "stake_nok": "10",
            "result": "ConfirmedPlaced",
            "p_l_nok": "",
        },
        {
            "bet_id": "a2",
            "date": "2026-07-20",
            "match": "C vs D",
            "selection": "C",
            "decimal_odds": "1.90",
            "stake_nok": "10",
            "result": "Abandoned",
            "p_l_nok": "0",
        },
    ]
    assert validate_bets(rows) == []


def test_validate_rejects_abandoned_nonzero_pl():
    rows = [
        {
            "bet_id": "bad",
            "date": "2026-07-20",
            "match": "A vs B",
            "selection": "A",
            "decimal_odds": "1.80",
            "stake_nok": "10",
            "result": "Abandoned",
            "p_l_nok": "-10",
        }
    ]
    errs = validate_bets(rows)
    assert any("Abandoned" in e for e in errs)


def test_kill_switch_formula_documents_settlement_day():
    phase = {
        "phase_id": "1A",
        "daily_risk_pct": 0.08,
        "daily_risk_floor": 30,
        "daily_risk_ceil": 42,
    }
    rows = [
        {
            "date": "2026-07-19",
            "updated_at": "2026-07-20T14:00:00Z",
            "result": "Loss",
            "p_l_nok": "-50",
            "stake_nok": "50",
        }
    ]
    assert day_realized_pl(rows, day="2026-07-20") == -50.0
    assert day_realized_pl(rows, day="2026-07-19") == 0.0

    cfg = {
        "risk": {"stop_day_loss_pct_of_equity": 0.08, "stop_day_loss_floor_nok": 40},
        "norsk_tipping": {"min_stake_nok": 10},
    }
    risk = evaluate_risk(cfg, equity=500.0, phase=phase, rows=rows)
    assert "today_realized_pl_nok" in risk
    assert "updated_at" in risk["formula"] or "settlement" in risk["formula"]


def test_place_ack_and_abandon_roundtrip(tmp_path, monkeypatch):
    from nt.bets_io import BET_HEADER, write_bets
    from nt.ledger_ops import abandon, place_ack

    bets_path = tmp_path / "bets.csv"
    rows = [
        {
            "bet_id": "abc123pending",
            "date": "2026-07-20",
            "match": "Humphries, Luke vs Menzies, Cameron",
            "selection": "Totalt antall runder 15.5: Over 15.5",
            "decimal_odds": "2.10",
            "stake_nok": "12",
            "result": "Pending",
            "p_l_nok": "",
            "payout_nok": "",
            "sport": "darts",
            "market_type": "Totalt antall runder 15.5",
            "odds_band": "1.8-2.2",
            "research_grade": "B",
            "phase": "1A",
            "notes": "test",
            "source": "recommend",
            "created_at": "2026-07-20T18:00:00Z",
            "updated_at": "2026-07-20T18:00:00Z",
        }
    ]
    write_bets(bets_path, rows, backup=False)

    cfg = {
        "paths": {
            "bets": str(bets_path),
            "state_dir": str(tmp_path / "state"),
            "status": str(tmp_path / "status.md"),
            "bankroll_md": str(tmp_path / "bankroll.md"),
        },
        "bankroll": {"baseline_nok": 500.0, "era_start": "2026-07-19"},
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
        "risk": {"stop_day_loss_pct_of_equity": 0.08, "stop_day_loss_floor_nok": 40},
        "norsk_tipping": {"min_stake_nok": 10},
        "selection": {"high_odds_threshold": 2.5},
        "project": {"root": str(tmp_path)},
    }

    # Minimal path_from_config compatibility via monkeypatch load_config paths
    from nt import config as config_mod

    def _pfc(c, key):
        p = c["paths"].get(key)
        return Path(p) if p else tmp_path / key

    monkeypatch.setattr(config_mod, "path_from_config", _pfc)
    # ledger_ops imports path_from_config from nt.config
    import nt.ledger_ops as lo

    monkeypatch.setattr(lo, "path_from_config", _pfc)
    monkeypatch.setattr(lo, "refresh_state", lambda c: ({}, {"phase_id": "1A"}, {}))

    ack = place_ack(cfg, ids=["abc123pending"])
    assert ack["ok"] and ack["n"] >= 1
    loaded = __import__("nt.bets_io", fromlist=["load_bets"]).load_bets(bets_path)
    assert loaded[0]["result"] == "ConfirmedPlaced"
    assert pending_stake_total(loaded) == 12.0

    ab = abandon(cfg, ids=["abc123pending"], reason="missed_prematch")
    assert ab["ok"] and ab["n"] == 1
    loaded2 = __import__("nt.bets_io", fromlist=["load_bets"]).load_bets(bets_path)
    assert loaded2[0]["result"] == "Abandoned"
    assert loaded2[0]["p_l_nok"] in ("0", "0.0", "0.00")
    assert pending_stake_total(loaded2) == 0.0
    assert "missed_prematch" in (loaded2[0].get("notes") or "")
