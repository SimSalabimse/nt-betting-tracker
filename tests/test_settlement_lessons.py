"""Settlement Lessons v1: auto main_reason, schema load, soft pen, live-only peers."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.settlement_lessons import (
    auto_main_reason,
    build_settlement_lessons,
    empty_lessons_payload,
    infer_outcome_driver,
    lessons_soft_adjustments,
    load_settlement_lessons,
    resolve_main_reason,
    run_settlement_lessons_safe,
)


def _cfg(tmp_path: Path) -> dict:
    state = tmp_path / "state"
    outbox = tmp_path / "outbox"
    state.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    bets = tmp_path / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,"
        "research_grade,odds_band,sport,market_type,phase,source,notes,"
        "created_at,updated_at\n",
        encoding="utf-8",
    )
    return {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "outbox": str(outbox),
            "settlement_lessons_json": str(state / "settlement_lessons.json"),
        },
        "learning": {
            "settlement_lessons": {
                "enabled": True,
                "recent_window": 12,
                "max_soft_notes": 8,
                "soft_ev_penalty_repeat_loss": 0.008,
                "ttl_hours": 72,
                "live_ledger_only": True,
            }
        },
    }


def test_main_reason_non_empty_without_agent_packet():
    """Engine auto-template always fills main_reason when packet is thin."""
    bet = {
        "bet_id": "t1",
        "result": "Loss",
        "sport": "tennis",
        "selection": "Totalt antall games 22.5: Over 22.5",
        "score": "6-4 3-6 4-6",
        # no post_settlement_packet, no main_reason, no notes
    }
    reason = resolve_main_reason(bet, market_family="tennis_totals")
    assert reason
    assert reason.strip()
    assert "Loss" in reason
    assert "tennis_totals" in reason
    assert "22.5" in reason or "line=" in reason

    auto = auto_main_reason(
        result="Loss",
        market_family="tennis_totals",
        actual_score="6-4 3-6 4-6",
        selection="Totalt antall games 22.5: Over 22.5",
    )
    assert auto
    assert "family=tennis_totals" in auto


def test_outcome_driver_totals_line_miss():
    bet = {
        "result": "Loss",
        "selection": "Totalt antall games 22.5: Over 22.5",
        "score": "6-4 3-6 4-6",  # 29 games? 6+4+3+6+4+6 = 29 — wait sets sum
        # 6-4 3-6 4-6 = 29 games total — Over 22.5 would WIN; for miss use under actual
    }
    # Force under-total vs Over selection
    bet["score"] = "6-3 6-2"  # 17 games < 22.5 Over → total_line_miss
    driver = infer_outcome_driver(bet, market_family="tennis_totals")
    assert driver == "total_line_miss"


def test_schema_v1_load_missing_file_empty_no_throw(tmp_path: Path):
    cfg = _cfg(tmp_path)
    # file does not exist
    payload = load_settlement_lessons(cfg)
    assert payload["schema_version"] == 1
    assert payload["bets"] == []
    assert payload["soft_awareness"] == []
    # invalid JSON
    path = Path(cfg["paths"]["settlement_lessons_json"])
    path.write_text("{not json", encoding="utf-8")
    payload2 = load_settlement_lessons(cfg)
    assert payload2["bets"] == []
    # wrong schema version
    path.write_text(
        json.dumps({"schema_version": 99, "bets": [{"bet_id": "x"}]}) + "\n",
        encoding="utf-8",
    )
    payload3 = load_settlement_lessons(cfg)
    assert payload3["bets"] == []


def test_soft_pen_applies_with_similar_count_zero(tmp_path: Path):
    """lessons_soft_adjustments independent of similar-recent hits."""
    cfg = _cfg(tmp_path)
    lessons = empty_lessons_payload()
    lessons["soft_awareness"] = [
        {
            "family": "tennis_totals",
            "note": "temporary caution — 2 recent losses same family; raise evidence bar",
            "pattern_flag": "repeat_type_loss",
            "created_at": "2026-07-25T12:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "expired": False,
        }
    ]
    pen, why = lessons_soft_adjustments("tennis_totals", lessons, cfg)
    assert pen == pytest.approx(0.008)
    assert "lessons_soft:" in why
    assert "tennis_totals" in why
    # different family → no pen
    pen2, why2 = lessons_soft_adjustments("darts_totals", lessons, cfg)
    assert pen2 == 0.0
    assert why2 == ""
    # expired → no pen
    lessons["soft_awareness"][0]["expires_at"] = "2000-01-01T00:00:00Z"
    pen3, _ = lessons_soft_adjustments("tennis_totals", lessons, cfg)
    assert pen3 == 0.0


def test_era_archive_not_used_as_peers(tmp_path: Path):
    """Peers/window drop era_archive so archive losses do not set repeat_type_loss."""
    cfg = _cfg(tmp_path)
    live_rows = [
        {
            "bet_id": "arch1",
            "source": "era_archive",
            "result": "Loss",
            "sport": "tennis",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "updated_at": "2026-07-24T10:00:00Z",
        },
        {
            "bet_id": "arch2",
            "source": "era_archive",
            "result": "Loss",
            "sport": "tennis",
            "selection": "Totalt antall games 21.5: Over 21.5",
            "updated_at": "2026-07-24T11:00:00Z",
        },
        {
            "bet_id": "live_open",
            "source": "recommend",
            "result": "Pending",
            "sport": "darts",
            "selection": "Totalt antall 180s Over 3.5",
            "updated_at": "2026-07-25T09:00:00Z",
        },
    ]
    settled = [
        {
            "bet_id": "new1",
            "result": "Loss",
            "sport": "tennis",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "match": "A vs B",
            "score": "6-3 6-2",
        }
    ]
    payload = build_settlement_lessons(
        cfg, settled, live_rows=live_rows, persist=True
    )
    assert payload["n_settled"] == 1
    entry = payload["bets"][0]
    assert entry["main_reason"]
    # Only archive peers same family → after filter_live_rows, no tennis peers
    assert entry["pattern_flag"] == "none"
    # Soft awareness should not invent repeat_type_loss from archive alone
    sa_flags = {s.get("pattern_flag") for s in payload.get("soft_awareness") or []}
    assert "repeat_type_loss" not in sa_flags


def test_build_writes_json_and_md(tmp_path: Path):
    cfg = _cfg(tmp_path)
    settled = [
        {
            "bet_id": "b1",
            "result": "Loss",
            "sport": "tennis",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "match": "Van Assche vs Gaston",
            "score": "6-3 6-2",
        },
        {
            "bet_id": "b2",
            "result": "Loss",
            "sport": "tennis",
            "selection": "Totalt antall games 22.5: Over 22.5",
            "match": "Blockx vs Darderi",
            "score": "6-4 6-3",
        },
    ]
    # Live peers with prior loss same family → repeat_type_loss
    live_rows = [
        {
            "bet_id": "old1",
            "source": "live",
            "result": "Loss",
            "sport": "tennis",
            "selection": "Totalt antall games 21.5: Under 21.5",
            "updated_at": "2026-07-24T12:00:00Z",
        },
        *settled,
    ]
    payload = build_settlement_lessons(cfg, settled, live_rows=live_rows, persist=True)
    assert payload["schema_version"] == 1
    assert payload["n_settled"] == 2
    for b in payload["bets"]:
        assert b["main_reason"]
        assert b["outcome_driver"]
    jpath = Path(cfg["paths"]["settlement_lessons_json"])
    assert jpath.is_file()
    loaded = json.loads(jpath.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == 1
    md = Path(cfg["paths"]["outbox"]) / "SETTLEMENT_LESSONS.md"
    assert md.is_file()
    body = md.read_text(encoding="utf-8")
    assert "Settlement Lessons" in body
    assert "main reason" in body.lower() or "Main reason" in body


def test_settle_continues_if_lessons_throws(tmp_path: Path):
    """run_settlement_lessons_safe never raises; settle path treats as soft fail."""
    cfg = _cfg(tmp_path)
    with patch(
        "nt.settlement_lessons.build_settlement_lessons",
        side_effect=RuntimeError("boom"),
    ):
        out = run_settlement_lessons_safe(
            cfg,
            [{"bet_id": "x", "result": "Loss", "selection": "Over 2.5", "sport": "football"}],
        )
    assert out.get("ok") is False
    assert "boom" in str(out.get("error") or "")


def test_soft_awareness_cap_keeps_freshest(tmp_path: Path):
    """max_soft_notes retains newest TTL notes, not oldest."""
    cfg = _cfg(tmp_path)
    cfg["learning"]["settlement_lessons"]["max_soft_notes"] = 2
    # Seed three prior families (oldest → newest)
    prev = {
        "schema_version": 1,
        "updated_at": "2026-07-20T10:00:00Z",
        "settled_at": "2026-07-20T10:00:00Z",
        "batch_id": "settle_old",
        "live_ledger_only": True,
        "source": "data/bets.csv",
        "n_settled": 0,
        "bets": [],
        "soft_awareness": [
            {
                "family": "f0_oldest",
                "note": "temporary caution — old",
                "pattern_flag": "cluster_same_family",
                "created_at": "2026-07-20T10:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "expired": False,
            },
            {
                "family": "f1_mid",
                "note": "temporary caution — mid",
                "pattern_flag": "cluster_same_family",
                "created_at": "2026-07-21T10:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "expired": False,
            },
            {
                "family": "f2_newest",
                "note": "temporary caution — new",
                "pattern_flag": "cluster_same_family",
                "created_at": "2026-07-22T10:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "expired": False,
            },
        ],
    }
    Path(cfg["paths"]["settlement_lessons_json"]).write_text(
        json.dumps(prev, indent=2) + "\n", encoding="utf-8"
    )
    # New settle that does not add more families — just rebuilds/caps
    settled = [
        {
            "bet_id": "solo",
            "result": "Win",
            "sport": "darts",
            "selection": "Vinner: Player A",
            "match": "A vs B",
        }
    ]
    payload = build_settlement_lessons(cfg, settled, live_rows=settled, persist=True)
    fams = [s["family"] for s in payload["soft_awareness"]]
    assert len(fams) == 2
    assert "f0_oldest" not in fams
    assert "f2_newest" in fams
    assert "f1_mid" in fams


def test_main_reason_strips_short_settle_blob():
    """Short composite notes must not keep settle{…} in main_reason."""
    bet = {
        "result": "Loss",
        "sport": "tennis",
        "selection": "Totalt antall games 22.5: Over 22.5",
        "notes": "thin | settle{score:0-0}",
    }
    reason = resolve_main_reason(bet, market_family="tennis_totals")
    assert "settle{" not in reason
    # prefix "thin" is < 8 chars → auto-template
    assert "family=tennis_totals" in reason

    bet2 = {
        "result": "Loss",
        "sport": "tennis",
        "selection": "Totalt antall games 22.5: Over 22.5",
        "notes": "line too high late fade | settle{score:6-3 6-2}",
    }
    reason2 = resolve_main_reason(bet2, market_family="tennis_totals")
    assert "settle{" not in reason2
    assert "line too high" in reason2


def test_total_line_miss_requires_explicit_side():
    """Ambiguous totals selection without Over/Under → not total_line_miss."""
    bet = {
        "result": "Loss",
        "selection": "Totalt antall games 22.5",  # no Over/Under token
        "score": "6-3 6-2",  # 17 < 22.5
    }
    driver = infer_outcome_driver(bet, market_family="tennis_totals")
    assert driver != "total_line_miss"


def test_lessons_soft_reason_field_separate_from_similar():
    """PR2-safe: lessons use lessons_soft_reason; soft_demotion_reason merges."""
    from nt.portfolio import Recommendation

    rec = Recommendation(
        match="A vs B",
        selection="Over 22.5",
        decimal_odds=1.9,
        stake_nok=10,
        ev=0.04,
        grade="B",
        odds_band="1.8-2.2",
        sport="tennis",
        market_type="",
        p_model=0.55,
        notes="",
        market_family="tennis_totals",
    )
    rec.similar_recent_reason = "similar_recent: tennis_totals (2 in last 12)"
    rec.lessons_soft_reason = "lessons_soft: tennis_totals (repeat_type_loss)"
    parts = [
        x
        for x in (rec.similar_recent_reason, rec.lessons_soft_reason)
        if x and str(x).strip()
    ]
    rec.soft_demotion_reason = "; ".join(parts)
    assert "similar_recent" in rec.soft_demotion_reason
    assert "lessons_soft" in rec.soft_demotion_reason
    assert rec.similar_recent_reason.startswith("similar_recent")
    assert rec.lessons_soft_reason.startswith("lessons_soft")
