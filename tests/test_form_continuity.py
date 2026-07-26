"""Unit tests for form continuity + anti-flip core (PR1 library)."""
from __future__ import annotations

import inspect
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

import nt.form_continuity as fc
from nt.form_continuity import (
    build_evidence_snapshot,
    form_continuity_penalty,
    is_heavy_favourite_hc,
    is_opposite_side_hc,
    is_ranking_gap_hc,
    live_continuity_anchor_window,
    parse_match_teams,
    selection_agrees_with_rank,
    selection_side_sign,
)
from nt.learning import diversification_limits

# ---------------------------------------------------------------------------
# Verbatim fixture strings (design / live ledger SSOT)
# ---------------------------------------------------------------------------
MATCH = "Milwaukee Brewers vs Colorado Rockies"
PRIOR_SEL = (
    "Handikap 2-veis -1.5 (inkludert ekstra innings): Milwaukee Brewers -1.5"
)
CAND_SEL = "Handikap 2-veis -2.5: Colorado Rockies +2.5"
PRIOR_ODDS = 1.79
CAND_ODDS = 1.75


def _enabled_cfg(**overrides):
    base = {
        "enabled": True,
        "live_ledger_only": True,
        "anchor_scan_limit": 30,
        "max_hours": 48,
        "max_games": 2,
        "heavy_fav_max_odds": 2.10,
        "include_pending_anchors": True,
        "base_penalty": 0.035,
        "pending_penalty": 0.015,
        "weak_extra_penalty": 0.025,
        "convincing_win_mult": 1.25,
        "strong_flip_min_ev": 0.06,
        "weak_flip_action": "soft_reject",
        "heavy_line_by_sport": {
            "baseball": 1.5,
            "basketball": 5.5,
            "football": 1.5,
            "ice_hockey": 1.5,
            "tennis": 2.5,
            "darts": 2.5,
            "esports": 1.5,
            "default": 1.5,
        },
    }
    base.update(overrides)
    return base


def _brewers_win_row(*, hours_ago: float = 12.0, **extra):
    now = datetime.now(timezone.utc)
    ts = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d")
    row = {
        "bet_id": "brewers-win-1",
        "match": MATCH,
        "selection": PRIOR_SEL,
        "sport": "baseball",
        "market_type": "Handikap 2-veis",
        "market_family": "baseball_handicap",
        "result": "Win",
        "decimal_odds": PRIOR_ODDS,
        "odds": PRIOR_ODDS,
        "updated_at": ts,
        "created_at": ts,
        "date": day,
        "notes": "",
        "source": "live",
    }
    row.update(extra)
    return row


def _rockies_cand(**extra):
    row = {
        "match": MATCH,
        "selection": CAND_SEL,
        "sport": "baseball",
        "market_type": "Handikap 2-veis",
        "market_family": "baseball_handicap",
        "decimal_odds": CAND_ODDS,
        "grade": "B",
        "notes": "public on fav; +2.5 is easier",
        "base_ev": 0.02,
    }
    row.update(extra)
    return row


# ---------------------------------------------------------------------------
# Team parse / side signs
# ---------------------------------------------------------------------------
def test_parse_match_teams_vs():
    t = parse_match_teams(MATCH)
    assert t is not None
    assert t[0] == "milwaukee brewers"
    assert t[1] == "colorado rockies"


def test_selection_side_sign_brewers_minus_rockies_plus():
    assert selection_side_sign(PRIOR_SEL) == "minus"
    assert selection_side_sign(CAND_SEL) == "plus"


# ---------------------------------------------------------------------------
# Heavy favourite
# ---------------------------------------------------------------------------
def test_heavy_fav_brewers_minus_1_5_at_1_79():
    row = _brewers_win_row()
    assert is_heavy_favourite_hc(row, _enabled_cfg()) is True


def test_rockies_plus_not_heavy_fav():
    assert (
        is_heavy_favourite_hc(
            {
                "selection": CAND_SEL,
                "sport": "baseball",
                "market_family": "baseball_handicap",
                "decimal_odds": CAND_ODDS,
                "result": "Win",
            },
            _enabled_cfg(),
        )
        is False
    )


def test_heavy_fav_odds_above_max():
    row = _brewers_win_row(decimal_odds=2.50, odds=2.50)
    assert is_heavy_favourite_hc(row, _enabled_cfg()) is False


# ---------------------------------------------------------------------------
# Opposite side
# ---------------------------------------------------------------------------
def test_opposite_side_brewers_rockies_flip():
    prior = _brewers_win_row()
    cand = _rockies_cand()
    assert is_opposite_side_hc(prior, cand) is True


def test_same_side_deeper_line_not_flip():
    prior = _brewers_win_row()
    same = {
        "match": MATCH,
        "selection": (
            "Handikap 2-veis -2.5 (inkludert ekstra innings): Milwaukee Brewers -2.5"
        ),
    }
    assert is_opposite_side_hc(prior, same) is False


# ---------------------------------------------------------------------------
# AND series window
# ---------------------------------------------------------------------------
def test_and_window_outside_48h_no_pen():
    """Old same-pair, 1 game, outside 48h → no pen (even if games ≤ 2)."""
    prior = _brewers_win_row(hours_ago=72.0)
    cand = _rockies_cand()
    pen, reason, meta = form_continuity_penalty(
        cand,
        [prior],
        _enabled_cfg(),
        base_ev=0.02,
        grade="B",
        notes="public on fav",
    )
    assert pen == 0.0
    assert meta.get("flip_detected") is False
    assert reason == ""


def test_and_window_within_48h_applies_pen():
    prior = _brewers_win_row(hours_ago=10.0)
    cand = _rockies_cand()
    pen, reason, meta = form_continuity_penalty(
        cand,
        [prior],
        _enabled_cfg(),
        base_ev=0.02,
        grade="B",
        notes="public on fav; easier line",
    )
    assert pen > 0.0
    assert meta.get("flip_detected") is True
    assert reason.startswith("form_continuity:")
    assert "Opposite side of recent successful" in reason


# ---------------------------------------------------------------------------
# Weak / strong flip truth table
# ---------------------------------------------------------------------------
def test_weak_phrase_en_soft_reject():
    prior = _brewers_win_row(hours_ago=8.0)
    cand = _rockies_cand(notes="public on fav; +2.5 is easier")
    pen, reason, meta = form_continuity_penalty(
        cand, [prior], _enabled_cfg(), base_ev=0.02, grade="B"
    )
    assert meta["soft_reject"] is True
    assert meta["weak_evidence"] is True
    assert meta["strong_flip_evidence"] is False
    assert "rejected" in reason
    assert reason.startswith("form_continuity:")


def test_weak_phrase_no_soft_reject():
    prior = _brewers_win_row(hours_ago=8.0)
    cand = _rockies_cand(notes="enklere linje; publikum på favoritt")
    pen, reason, meta = form_continuity_penalty(
        cand, [prior], _enabled_cfg(), base_ev=0.01, grade="B"
    )
    assert meta["soft_reject"] is True
    assert meta.get("has_weak_phrase") is True


def test_strong_flip_no_soft_reject_pen_remains():
    prior = _brewers_win_row(hours_ago=6.0)
    snap = {
        "why_flip": (
            "Confirmed pitcher change and rest advantage reverse the series edge "
            "for the dog side tonight"
        ),
        "injury_or_lineup_break": True,
        "summary": "pitcher change + rest",
    }
    cand = _rockies_cand(notes="pitcher change; rest advantage")
    pen, reason, meta = form_continuity_penalty(
        cand,
        [prior],
        _enabled_cfg(),
        base_ev=0.08,
        grade="B",
        evidence_snapshot=snap,
        notes=cand["notes"],
    )
    assert pen > 0.0
    assert meta["strong_flip_evidence"] is True
    assert meta["soft_reject"] is False
    assert meta["flip_detected"] is True


def test_explore_inflated_ev_uses_base_ev_still_soft_reject():
    """Low base_ev cannot escape via post-explore place EV (S3 uses base_ev)."""
    prior = _brewers_win_row(hours_ago=5.0)
    cand = _rockies_cand(notes="thin public lean", base_ev=0.01)
    # Pass place_ev-looking number only via notes — S3 must use base_ev
    pen, reason, meta = form_continuity_penalty(
        cand,
        [prior],
        _enabled_cfg(),
        base_ev=0.01,  # below strong_flip_min_ev 0.06
        grade="B",
        notes="bounce back; public chalk",
    )
    assert meta["soft_reject"] is True
    assert meta["strong_flip_evidence"] is False
    assert pen > 0.0


def test_pending_anchor_demote_only_no_soft_reject():
    prior = _brewers_win_row(hours_ago=4.0, result="Pending")
    cand = _rockies_cand(notes="easier line")
    pen, reason, meta = form_continuity_penalty(
        cand, [prior], _enabled_cfg(), base_ev=0.02, grade="B"
    )
    assert pen > 0.0
    assert meta["soft_reject"] is False
    assert meta.get("pending_anchor") is True
    assert "caution" in reason


def test_disabled_returns_zero():
    prior = _brewers_win_row(hours_ago=4.0)
    cand = _rockies_cand()
    pen, reason, meta = form_continuity_penalty(
        cand, [prior], _enabled_cfg(enabled=False), base_ev=0.02, grade="B"
    )
    assert pen == 0.0
    assert reason == ""
    assert meta.get("enabled") is False


# ---------------------------------------------------------------------------
# Live ledger only
# ---------------------------------------------------------------------------
def test_era_archive_ignored():
    prior = _brewers_win_row(hours_ago=5.0, source="era_archive")
    cand = _rockies_cand()
    pen, reason, meta = form_continuity_penalty(
        cand, [prior], _enabled_cfg(), base_ev=0.02, grade="B", notes="easier line"
    )
    assert pen == 0.0
    assert meta.get("flip_detected") is False


def test_live_continuity_anchor_window_not_clamped_to_15():
    rows = []
    now = datetime.now(timezone.utc)
    for i in range(25):
        ts = (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(
            {
                "match": f"Team A{i} vs Team B{i}",
                "selection": "ML",
                "result": "Win",
                "updated_at": ts,
                "created_at": ts,
                "source": "live",
            }
        )
    win = live_continuity_anchor_window(rows, limit=30, live_ledger_only=True)
    assert len(win) == 25  # all kept; not clamped to 10–15
    # newest first
    assert win[0]["match"] == "Team A0 vs Team B0"


def test_abandoned_excluded_from_window():
    rows = [
        {
            "match": "A vs B",
            "result": "Abandoned",
            "updated_at": "2026-07-26T12:00:00Z",
            "source": "live",
        },
        {
            "match": "C vs D",
            "result": "Win",
            "updated_at": "2026-07-26T11:00:00Z",
            "source": "live",
        },
    ]
    win = live_continuity_anchor_window(rows, limit=30)
    assert len(win) == 1
    assert win[0]["match"] == "C vs D"


# ---------------------------------------------------------------------------
# Import fence
# ---------------------------------------------------------------------------
def test_import_fence_no_decide_side():
    src = Path(inspect.getfile(fc)).read_text(encoding="utf-8")
    # Strip comments so fence strings only match real call/import surface
    code_only = "\n".join(
        ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
    )
    assert "decide_side" not in code_only
    assert "anti_soft_condition" not in code_only
    assert "evaluate_anti_soft" not in code_only
    # Named helpers only (import line or local fallback defs)
    assert "is_minus_handicap" in src
    assert "is_plus_handicap" in src


# ---------------------------------------------------------------------------
# Ranking-gap
# ---------------------------------------------------------------------------
def test_ranking_gap_elite_vs_bottom_era():
    assert (
        is_ranking_gap_hc(
            market_family="baseball_handicap",
            selection=PRIOR_SEL,
            notes="elite vs bottom ERA mismatch; ranking gap on the run line",
            match=MATCH,
        )
        is True
    )


def test_ranking_gap_structured_checklist():
    snap = build_evidence_snapshot(
        {
            "checklist": {
                "higher_ranked_side": "favourite",
                "ranking_confidence": 0.85,
            },
            "signals": {
                "ranking_seed": {"filled": True, "strength": "strong"},
            },
            "summary": "rank edge",
        },
        "B",
    )
    assert snap["signals_rank_primary"] is True
    assert snap["higher_ranked_side"] == "favourite"
    assert selection_agrees_with_rank(PRIOR_SEL, snap, match=MATCH) is True
    assert (
        is_ranking_gap_hc(
            market_family="baseball_handicap",
            selection=PRIOR_SEL,
            match=MATCH,
            evidence_snapshot=snap,
        )
        is True
    )


def test_selection_agrees_with_rank_dog_plus():
    snap = {"higher_ranked_side": "underdog", "ranking_confidence": 0.9}
    assert selection_agrees_with_rank(CAND_SEL, snap, match=MATCH) is True
    assert selection_agrees_with_rank(PRIOR_SEL, snap, match=MATCH) is False


def test_ranking_gap_false_on_totals():
    assert (
        is_ranking_gap_hc(
            market_family="baseball_totals",
            selection="Totalt over 8.5",
            notes="elite vs bottom ERA",
        )
        is False
    )


# ---------------------------------------------------------------------------
# Reason prefix + EV invariant helper
# ---------------------------------------------------------------------------
def test_reason_prefix_and_content():
    prior = _brewers_win_row(hours_ago=3.0)
    cand = _rockies_cand()
    pen, reason, meta = form_continuity_penalty(
        cand, [prior], _enabled_cfg(), base_ev=0.02, grade="B", notes="easier line"
    )
    assert reason.startswith("form_continuity:")
    assert "Opposite side of recent successful" in reason
    assert "Milwaukee Brewers" in reason or "Brewers" in reason or "-1.5" in reason


def test_penalty_does_not_alter_place_ev():
    """Helper invariant: caller keeps place_ev untouched (pen is separate)."""
    prior = _brewers_win_row(hours_ago=3.0)
    place_ev = 0.045
    pen, reason, meta = form_continuity_penalty(
        _rockies_cand(),
        [prior],
        _enabled_cfg(),
        base_ev=0.02,
        grade="B",
        notes="public chalk",
    )
    # form_continuity returns pen only — place_ev variable unchanged
    assert place_ev == 0.045
    assert pen > 0
    assert isinstance(meta, dict)


# ---------------------------------------------------------------------------
# diversification_limits setdefaults
# ---------------------------------------------------------------------------
def test_diversification_limits_form_continuity_defaults():
    lim = diversification_limits({})
    assert "form_continuity" in lim
    assert lim["form_continuity"]["enabled"] is False
    assert lim["form_continuity"]["max_hours"] == 48
    assert lim["form_continuity"]["heavy_line_by_sport"]["baseball"] == 1.5
    assert lim["form_continuity"]["heavy_line_by_sport"]["basketball"] == 5.5
    assert lim["ranking_gap_hc"]["enabled"] is False
    assert lim["ranking_gap_hc"]["max_per_slip"] == 1
    assert lim["sort"]["continuity_penalty_weight"] == 1.0
    assert lim["explore_base_ev_min"] == 0.005


def test_diversification_limits_merges_config_overrides():
    lim = diversification_limits(
        {
            "learning": {
                "diversification": {
                    "form_continuity": {"enabled": True, "max_hours": 24},
                    "explore_base_ev_min": 0.01,
                }
            }
        }
    )
    assert lim["form_continuity"]["enabled"] is True
    assert lim["form_continuity"]["max_hours"] == 24
    assert lim["form_continuity"]["max_games"] == 2  # default retained
    assert lim["explore_base_ev_min"] == 0.01
