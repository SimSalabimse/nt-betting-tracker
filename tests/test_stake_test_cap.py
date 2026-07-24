"""PR4: FEH 10 NOK test stake cap after all stake mutations."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.portfolio import Recommendation, rebalance_stakes
from nt.stake_test_cap import (
    CONSTRAINT_TAG,
    annotate_notes_for_cap,
    apply_test_stake_cap_to_picked,
    assert_stakes_within_cap,
    clip_stake_nok,
    fail_closed_hook_error,
    inject_seat_max,
    is_test_cap_active,
    load_state,
    max_stake_when_active,
    notes_have_system_tag,
    record_placed_bet,
    run_absolute_last_stake_cap,
    save_state,
    should_tag_pending,
    stake_test_cap_cfg,
    system_tag_note,
)


def _cfg(tmp: Path, **tsc_over) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    tsc = {
        "enabled": True,
        "max_bets": 10,
        "max_stake_nok": 10.0,
        "system_tag": "feh_v1",
        "state_path": str(state / "feh_test_cap.json"),
    }
    tsc.update(tsc_over)
    return {
        "paths": {
            "state_dir": str(state),
            "bets": str(tmp / "bets.csv"),
        },
        "norsk_tipping": {"min_stake_nok": 10},
        "selection": {
            "test_stake_cap": tsc,
            "evidence": {
                "enabled": True,
                "shadow_mode": False,
                "forced_hierarchy": {"enabled": True},
            },
        },
    }


def _rec(
    stake: float = 12.0,
    *,
    unit_size: float = 12.0,
    grade_mult: float = 1.4,
    notes: str = "EXPLORE_REGIME; p_model=0.55",
    ev: float = 0.05,
) -> Recommendation:
    return Recommendation(
        match="A vs B",
        selection="A +1.5",
        decimal_odds=1.90,
        stake_nok=stake,
        ev=ev,
        grade="B",
        odds_band="1.8-2.2",
        sport="darts",
        market_type="handicap",
        p_model=0.55,
        notes=notes,
        stake_decision={
            "schema_version": 1,
            "rule_bundle_version": "test",
            "match": "A vs B",
            "selection": "A +1.5",
            "recommended_stake_nok": stake,
            "final_stake_nok": stake,
            "reject_reason": None,
            "size_mode": "NORMAL",
            "unit_size_nok": unit_size,
            "active_unit_nok": unit_size,
            "remaining_room_nok": 100.0,
            "min_stake_nok": 10.0,
            "constraints_applied": [],
            "inputs": {"grade_mult": grade_mult, "unit_size_nok": unit_size},
        },
    )


def test_cfg_defaults(tmp_path: Path):
    cfg = _cfg(tmp_path)
    tsc = stake_test_cap_cfg(cfg)
    assert tsc["enabled"] is True
    assert tsc["max_bets"] == 10
    assert tsc["max_stake_nok"] == 10.0
    assert tsc["system_tag"] == "feh_v1"


def test_missing_state_fail_closed_active(tmp_path: Path):
    """Missing state file → n_placed=0, cap active."""
    cfg = _cfg(tmp_path)
    st = load_state(cfg)
    assert st["n_placed"] == 0
    assert is_test_cap_active(cfg, st) is True
    assert max_stake_when_active(cfg, st) == 10.0


def test_explore_unit_12_final_10(tmp_path: Path):
    """regime_explore unit 12 → absolute-last clip to 10; unit_size/grade_mult unchanged."""
    cfg = _cfg(tmp_path)
    rec = _rec(stake=12.0, unit_size=12.0, grade_mult=1.4, notes="EXPLORE_REGIME; explore")
    unit_before = rec.stake_decision["unit_size_nok"]
    grade_before = rec.stake_decision["inputs"]["grade_mult"]
    rec_before = rec.stake_decision["recommended_stake_nok"]

    n = apply_test_stake_cap_to_picked([rec], cfg)
    assert n == 1
    assert rec.stake_nok == 10.0
    assert rec.stake_decision["final_stake_nok"] == 10.0
    assert CONSTRAINT_TAG in rec.stake_decision["constraints_applied"]
    # capital fields UNCHANGED
    assert rec.stake_decision["unit_size_nok"] == unit_before == 12.0
    assert rec.stake_decision["inputs"]["grade_mult"] == grade_before == 1.4
    # recommended may stay at pre-cap for audit
    assert rec.stake_decision["recommended_stake_nok"] == rec_before


def test_rebalance_cannot_exceed_10(tmp_path: Path):
    """Seat max inject + absolute last: rebalance top-up cannot leave stake > 10."""
    cfg = _cfg(tmp_path)
    picks = [
        _rec(stake=10.0, notes="p_model=0.6", ev=0.10),
        _rec(stake=10.0, notes="p_model=0.55", ev=0.08),
    ]
    for p in picks:
        p.match = f"{p.ev} vs X"
    # rebalance with large budget and seat maxes capped at 10
    maxes = [inject_seat_max(24.0, cfg) for _ in picks]
    assert maxes == [10.0, 10.0]
    rebalance_stakes(picks, budget=100.0, min_stake=10.0, max_stake=24.0, max_stakes=maxes)
    for p in picks:
        assert p.stake_nok <= 10.0 + 1e-9
    # Simulate EXPLORE_REGIME post-rebalance clamp raising to unit 12
    for p in picks:
        p.stake_nok = 12.0
        p.notes = "EXPLORE_REGIME; " + p.notes
    apply_test_stake_cap_to_picked(picks, cfg)
    for p in picks:
        assert p.stake_nok == 10.0


def test_tag_on_pending_notes(tmp_path: Path):
    """Pending notes include FEH_TEST_CAP:feh_v1 and display when active."""
    cfg = _cfg(tmp_path)
    rec = _rec(stake=12.0, notes="p_model=0.55; EV=0.04")
    apply_test_stake_cap_to_picked([rec], cfg)
    assert notes_have_system_tag(rec.notes, "feh_v1")
    assert "FEH_TEST_CAP:10NOK (0/10)" in rec.notes
    # annotate path also idempotent
    again = annotate_notes_for_cap(rec.notes, cfg)
    assert again.count("FEH_TEST_CAP:feh_v1") == 1


def test_untagged_place_ack_excluded(tmp_path: Path):
    """Pre-FEH Smith-like ack without tag does not increment n_placed."""
    cfg = _cfg(tmp_path)
    st0 = load_state(cfg)
    assert st0["n_placed"] == 0

    # Untagged (Smith-like 16 NOK pending)
    evt = record_placed_bet(cfg, "smith_like_3959", "EXPLORE; grade=B; stake was 16")
    assert evt["excluded"] is True
    assert evt["counted"] is False
    st = load_state(cfg)
    assert st["n_placed"] == 0
    assert "smith_like_3959" in st["excluded_bet_ids"]

    # Tagged counts
    notes = system_tag_note("feh_v1") + "; p_model=0.55"
    evt2 = record_placed_bet(cfg, "bet_tagged_001", notes)
    assert evt2["counted"] is True
    assert evt2["n_placed"] == 1
    st2 = load_state(cfg)
    assert st2["n_placed"] == 1
    assert "bet_tagged_001" in st2["bet_ids"]

    # Idempotent re-ack
    evt3 = record_placed_bet(cfg, "bet_tagged_001", notes)
    assert evt3["already_counted"] is True
    assert load_state(cfg)["n_placed"] == 1


def test_cap_inactive_after_max_bets(tmp_path: Path):
    cfg = _cfg(tmp_path, max_bets=2)
    notes = system_tag_note("feh_v1")
    record_placed_bet(cfg, "b1", notes)
    record_placed_bet(cfg, "b2", notes)
    st = load_state(cfg)
    assert st["n_placed"] == 2
    assert is_test_cap_active(cfg, st) is False
    assert max_stake_when_active(cfg, st) is None
    rec = _rec(stake=18.0)
    apply_test_stake_cap_to_picked([rec], cfg)
    # Cap inactive: stake not clipped (still tagged with system tag if place-owning)
    assert rec.stake_nok == 18.0


def test_system_tag_change_resets_counter(tmp_path: Path):
    cfg = _cfg(tmp_path, system_tag="feh_v1")
    record_placed_bet(cfg, "b1", system_tag_note("feh_v1"))
    assert load_state(cfg)["n_placed"] == 1

    cfg2 = _cfg(tmp_path, system_tag="feh_v2")
    # same state path under tmp_path/state
    st = load_state(cfg2)
    assert st["system_tag"] == "feh_v2"
    assert st["n_placed"] == 0
    assert is_test_cap_active(cfg2, st) is True


def test_assert_stakes_within_cap(tmp_path: Path):
    cfg = _cfg(tmp_path)
    ok = _rec(stake=10.0)
    apply_test_stake_cap_to_picked([ok], cfg)
    assert_stakes_within_cap([ok], cfg)  # no raise

    bad = _rec(stake=16.0)
    # Bypass apply to simulate violation
    with pytest.raises(RuntimeError, match="test stake cap"):
        assert_stakes_within_cap([bad], cfg)


def test_disabled_no_clip(tmp_path: Path):
    cfg = _cfg(tmp_path, enabled=False)
    rec = _rec(stake=16.0)
    apply_test_stake_cap_to_picked([rec], cfg)
    assert rec.stake_nok == 16.0
    assert not notes_have_system_tag(rec.notes, "feh_v1")


def test_clip_stake_helper(tmp_path: Path):
    cfg = _cfg(tmp_path)
    assert clip_stake_nok(16.0, cfg) == 10.0
    assert clip_stake_nok(8.0, cfg) == 8.0


def test_place_ack_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """ledger_ops.place_ack increments only for tagged Pending rows."""
    from nt.bets_io import write_bets
    from nt.ledger_ops import place_ack

    cfg = _cfg(tmp_path)
    cfg["bankroll"] = {"baseline_nok": 500.0, "current_nok": 500.0}
    monkeypatch.setattr("nt.ledger_ops.refresh_state", lambda _cfg: None)
    bets_path = Path(cfg["paths"]["bets"])
    rows = [
        {
            "bet_id": "tagged1",
            "date": "2026-07-24",
            "match": "A vs B",
            "selection": "A",
            "decimal_odds": "1.90",
            "stake_nok": "10.00",
            "result": "Pending",
            "p_l_nok": "",
            "payout_nok": "",
            "sport": "darts",
            "market_type": "hc",
            "odds_band": "1.8-2.2",
            "research_grade": "B",
            "phase": "1A",
            "notes": "FEH_TEST_CAP:feh_v1; FEH_TEST_CAP:10NOK (0/10); p_model=0.55",
            "source": "recommend",
            "created_at": "2026-07-24T10:00:00Z",
            "updated_at": "2026-07-24T10:00:00Z",
        },
        {
            "bet_id": "untagged_smith",
            "date": "2026-07-24",
            "match": "Smith vs Price",
            "selection": "Smith +2.5",
            "decimal_odds": "1.85",
            "stake_nok": "16.00",
            "result": "Pending",
            "p_l_nok": "",
            "payout_nok": "",
            "sport": "darts",
            "market_type": "hc",
            "odds_band": "1.8-2.2",
            "research_grade": "B",
            "phase": "1A",
            "notes": "EXPLORE; virgin sport",
            "source": "recommend",
            "created_at": "2026-07-24T10:00:00Z",
            "updated_at": "2026-07-24T10:00:00Z",
        },
    ]
    write_bets(bets_path, rows)

    out = place_ack(cfg, ids=["tagged1", "untagged_smith"])
    assert out["ok"] is True
    events = {e["bet_id"]: e for e in out.get("test_cap_events") or []}
    assert events["tagged1"]["counted"] is True
    assert events["untagged_smith"]["excluded"] is True
    st = load_state(cfg)
    assert st["n_placed"] == 1
    assert "tagged1" in st["bet_ids"]
    assert "untagged_smith" in st["excluded_bet_ids"]


def test_nothing_raises_stake_after_clip(tmp_path: Path):
    """Invariant: after apply_test_stake_cap_to_picked, all stakes ≤ 10 when active."""
    cfg = _cfg(tmp_path)
    picks = [
        _rec(stake=12.0, notes="EXPLORE_REGIME"),
        _rec(stake=24.0, notes="grade A"),
        _rec(stake=10.0, notes="already floor"),
        _rec(stake=11.0, notes="just over"),
    ]
    apply_test_stake_cap_to_picked(picks, cfg)
    for p in picks:
        assert p.stake_nok <= 10.0 + 1e-9
    assert_stakes_within_cap(picks, cfg)


def test_tag_and_clip_when_enabled_without_place_owning(tmp_path: Path):
    """O2: tag + clip share enabled gate — no place-owning required."""
    cfg = _cfg(tmp_path)
    # FEH place-owning OFF (shadow / hierarchy disabled)
    cfg["selection"]["evidence"] = {
        "enabled": True,
        "shadow_mode": True,
        "forced_hierarchy": {"enabled": False},
    }
    assert should_tag_pending(cfg) is True
    rec = _rec(stake=16.0, notes="p_model=0.55")
    n = apply_test_stake_cap_to_picked([rec], cfg)
    assert n == 1
    assert rec.stake_nok == 10.0
    assert notes_have_system_tag(rec.notes, "feh_v1")
    # Counter can advance on tagged place-ack even without place-owning
    evt = record_placed_bet(cfg, "no_feh_own_1", rec.notes)
    assert evt["counted"] is True
    assert load_state(cfg)["n_placed"] == 1


def test_run_absolute_last_fail_closed_on_apply_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """O1: when enabled, apply failure must re-raise (never silent drop of ceiling)."""
    cfg = _cfg(tmp_path)

    def _boom(*_a, **_k):
        raise OSError("state disk full")

    monkeypatch.setattr(
        "nt.stake_test_cap.apply_test_stake_cap_to_picked",
        _boom,
    )
    rec = _rec(stake=12.0)
    with pytest.raises(RuntimeError, match="failed closed"):
        run_absolute_last_stake_cap([rec], cfg)


def test_fail_closed_hook_when_enabled(tmp_path: Path):
    cfg = _cfg(tmp_path, enabled=True)
    with pytest.raises(RuntimeError, match="failed closed"):
        fail_closed_hook_error(cfg, RuntimeError("import boom"), where="test")


def test_fail_closed_hook_swallows_when_disabled(tmp_path: Path):
    cfg = _cfg(tmp_path, enabled=False)
    # Must not raise when cap disabled
    fail_closed_hook_error(cfg, RuntimeError("import boom"), where="test")
