"""
Secure bucket Variant A — soft/hard skim, liquid floor, unlock rules.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.capital_runtime import (
    apply_secure_transfer_to_segments,
    manual_unlock_secure,
    maybe_auto_unlock_secure,
    release_secure_to_working,
    sync_capital_v2_state,
)
from nt.capital_segments import load_segments, save_segments, segments_path
from nt.capital_v2 import (
    capital_v2_cfg,
    compute_secure_transfer,
    compute_secure_transfer_variant_a,
    empty_segments,
)


def _v2_a(**sb_extra) -> dict:
    return capital_v2_cfg(
        {
            "norsk_tipping": {"min_stake_nok": 10.0},
            "capital_v2": {
                "enabled": True,
                "secure_bucket": {
                    "enabled": True,
                    "variant": "A",
                    "soft_trigger_multiple_of_ref": 1.25,
                    "soft_transfer_fraction": 0.15,
                    "hard_trigger_multiple_of_ref": 1.50,
                    "hard_transfer_fraction": 0.30,
                    "min_working_frac_of_equity": 0.55,
                    "min_working_units": 8.0,
                    "unlock_after_settled": 25,
                    "manual_unlock_cooldown_days": 7,
                    **sb_extra,
                },
            },
        }
    )


# ── Soft / hard tiers ─────────────────────────────────────────────────────


def test_soft_trigger_15pct():
    # ref 500, soft 625, hard 750; equity 700 → soft only
    r = compute_secure_transfer_variant_a(
        ledger_equity=700.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
    )
    assert r.triggered is True
    assert r.tier == "soft"
    assert r.transferred == 30.0  # whole_krone(0.15 * 200)
    assert r.secure_after == 30.0
    assert r.working_equity_after == 670.0
    assert r.ref_hwm_after == 670.0


def test_hard_trigger_30pct_not_stacked():
    # equity 800 ≥ 1.50×500=750 → hard only (not soft 15% + hard 30%)
    r = compute_secure_transfer_variant_a(
        ledger_equity=800.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
    )
    assert r.triggered is True
    assert r.tier == "hard"
    assert r.transferred == 90.0  # whole_krone(0.30 * 300)
    assert r.secure_after == 90.0
    assert r.working_equity_after == 710.0
    # stacked would be 0.15*300 + 0.30*300 = 135 — must not happen
    assert r.transferred != 135.0


def test_below_soft_no_transfer():
    # soft trigger 1.25×500 = 625; equity 620 → no skim
    r = compute_secure_transfer_variant_a(
        ledger_equity=620.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
    )
    assert r.triggered is False
    assert r.tier is None
    assert r.transferred == 0.0
    assert r.reason == "below_trigger"
    assert r.ref_hwm_after == 500.0


def test_exactly_at_soft_trigger():
    r = compute_secure_transfer_variant_a(
        ledger_equity=625.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
    )
    assert r.triggered is True
    assert r.tier == "soft"
    assert r.transferred == whole_krone_15pct(125.0)  # 18


def whole_krone_15pct(profit: float) -> float:
    return float(int(0.15 * profit))


def test_exactly_at_hard_trigger():
    r = compute_secure_transfer_variant_a(
        ledger_equity=750.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
    )
    assert r.triggered is True
    assert r.tier == "hard"
    assert r.transferred == 75.0  # 0.30 * 250


# ── Liquid floor via daily_risk_ceil ──────────────────────────────────────


def test_liquid_floor_blocks_skim():
    """
    Never skim if post-skim liquid (equity − secure_after − open) < daily_risk_ceil.
    equity=700, open=650, ceil=42 → liquid before = 50; any skim would leave < 42
    if transfer large — with open so high max secure = 700-650-42=8.
    """
    # Working 700; floor requires liquid ≥ 42 with open 660 → max secure 700-660-42=-2 → block
    r = compute_secure_transfer_variant_a(
        ledger_equity=700.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
        phase_daily_risk_ceil=42.0,
        open_risk=660.0,
    )
    assert r.triggered is False
    assert r.reason == "liquid_floor_blocks_skim"
    assert r.transfer_capped_by_liquid_floor is True


def test_liquid_floor_caps_transfer():
    # equity 700, open 0, ceil 650 → max secure = 50; soft raw = 30 → 30 OK
    r = compute_secure_transfer_variant_a(
        ledger_equity=700.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
        phase_daily_risk_ceil=650.0,
        open_risk=0.0,
    )
    assert r.triggered is True
    assert r.transferred == 30.0
    assert r.working_equity_after - 0.0 >= 650.0 - 1e-9

    # ceil 680 → max secure = 20; soft raw 30 → capped to 20
    r2 = compute_secure_transfer_variant_a(
        ledger_equity=700.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
        phase_daily_risk_ceil=680.0,
        open_risk=0.0,
    )
    assert r2.triggered is True
    assert r2.transferred == 20.0
    assert r2.transfer_capped_by_liquid_floor is True
    assert r2.working_equity_after >= 680.0 - 1e-9


# ── Min working buffer still applies ──────────────────────────────────────


def test_min_working_buffer_still_applies():
    # Aggressive hard fraction with low min buffer relative to huge profit
    r = compute_secure_transfer(
        ledger_equity=1000.0,
        secure_nok=0.0,
        ref_hwm=100.0,
        soft_trigger_multiple=1.25,
        soft_transfer_fraction=0.15,
        hard_trigger_multiple=1.50,
        hard_transfer_fraction=0.90,  # aggressive
        unit_size_nok=10.0,
        min_working_frac=0.55,
        min_working_units=8.0,
    )
    # hard fires: raw 0.9*(1000-100)=810; buffer max = 1000-550=450
    assert r.triggered is True
    assert r.tier == "hard"
    assert r.transferred == 450.0
    assert r.transfer_capped_by_buffer is True
    assert r.working_equity_after >= 550.0 - 1e-9


# ── Defaults are Variant A ────────────────────────────────────────────────


def test_capital_v2_cfg_defaults_variant_a():
    v2 = capital_v2_cfg({})
    sb = v2["secure_bucket"]
    assert sb["variant"] == "A"
    assert float(sb["soft_trigger_multiple_of_ref"]) == pytest.approx(1.25)
    assert float(sb["soft_transfer_fraction"]) == pytest.approx(0.15)
    assert float(sb["hard_trigger_multiple_of_ref"]) == pytest.approx(1.50)
    assert float(sb["hard_transfer_fraction"]) == pytest.approx(0.30)
    assert int(sb["unlock_after_settled"]) == 25
    assert int(sb["manual_unlock_cooldown_days"]) == 7


def test_runtime_apply_uses_variant_a():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["unit_hwm_reset_equity_nok"] = 500.0
    v2 = _v2_a()
    out, info = apply_secure_transfer_to_segments(
        segs, ledger_equity=700.0, v2=v2, settled_count=10
    )
    assert info["triggered"] is True
    assert info["tier"] == "soft"
    assert info["transferred"] == 30.0
    assert out["secure_lock_settled_count"] == 10


def test_runtime_hard_tier():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["unit_hwm_reset_equity_nok"] = 500.0
    out, info = apply_secure_transfer_to_segments(
        segs, ledger_equity=800.0, v2=_v2_a(), phase_daily_risk_ceil=42.0
    )
    assert info["tier"] == "hard"
    assert info["transferred"] == 90.0


# ── Unlock: auto after 25 settled / manual cooldown ───────────────────────


def test_auto_unlock_after_25_settled():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["secure_nok"] = 80.0
    segs["secure_lock_settled_count"] = 10
    # 10 + 24 = 34 → still short of 25 since lock
    out, info = maybe_auto_unlock_secure(segs, settled_count=34, v2=_v2_a())
    assert info["unlocked"] is False
    assert out["secure_nok"] == 80.0

    out2, info2 = maybe_auto_unlock_secure(segs, settled_count=35, v2=_v2_a())
    assert info2["unlocked"] is True
    assert info2["released_nok"] == 80.0
    assert out2["secure_nok"] == 0.0
    assert out2["secure_lock_settled_count"] == 35
    assert len(out2.get("secure_unlocks") or []) == 1
    assert out2["secure_unlocks"][0]["kind"] == "auto"


def test_release_secure_to_working_pure():
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["secure_nok"] = 50.0
    segs["unit_hwm_reset_equity_nok"] = 600.0
    out, info = release_secure_to_working(
        segs, reason="test", actor="pytest", settled_count=5, kind="manual"
    )
    assert info["unlocked"] is True
    assert out["secure_nok"] == 0.0
    # ref HWM left unchanged (working expands; ref stays for next skim cycle)
    assert out["unit_hwm_reset_equity_nok"] == 600.0
    assert out["last_manual_unlock_at"] is not None


def test_manual_unlock_cooldown(tmp_path: Path):
    state = tmp_path / "state"
    state.mkdir()
    cfg = {
        "paths": {
            "state_dir": str(state),
            "capital_segments": str(state / "capital_segments.json"),
            "bets": str(tmp_path / "bets.csv"),
        },
        "bankroll": {"baseline_nok": 500.0},
        "capital_v2": {
            "enabled": True,
            "secure_bucket": {
                "enabled": True,
                "variant": "A",
                "manual_unlock_cooldown_days": 7,
            },
        },
        "norsk_tipping": {"min_stake_nok": 10},
    }
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["secure_nok"] = 100.0
    # Recent manual unlock → cooldown active
    segs["last_manual_unlock_at"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    save_segments(cfg, segs)

    blocked = manual_unlock_secure(cfg, reason="too_soon", actor="pytest")
    assert blocked["ok"] is False
    assert blocked["reason"] == "manual_unlock_cooldown"
    assert load_segments(cfg)["secure_nok"] == 100.0

    # force bypasses cooldown
    forced = manual_unlock_secure(cfg, reason="ops_force", actor="pytest", force=True)
    assert forced["ok"] is True
    assert forced["released_nok"] == 100.0
    assert load_segments(cfg)["secure_nok"] == 0.0


def test_manual_unlock_ok_after_cooldown(tmp_path: Path):
    state = tmp_path / "state"
    state.mkdir()
    cfg = {
        "paths": {
            "state_dir": str(state),
            "capital_segments": str(state / "capital_segments.json"),
            "bets": str(tmp_path / "bets.csv"),
        },
        "bankroll": {"baseline_nok": 500.0},
        "capital_v2": {
            "enabled": True,
            "secure_bucket": {"enabled": True, "manual_unlock_cooldown_days": 7},
        },
        "norsk_tipping": {"min_stake_nok": 10},
    }
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["secure_nok"] = 40.0
    old = (datetime.now(timezone.utc) - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    segs["last_manual_unlock_at"] = old
    save_segments(cfg, segs)

    out = manual_unlock_secure(cfg, reason="ok", actor="pytest")
    assert out["ok"] is True
    assert out["released_nok"] == 40.0
    assert load_segments(cfg)["secure_nok"] == 0.0


# ── Variant B legacy single-trigger still parses ──────────────────────────


def test_variant_b_legacy_params_still_work():
    r = compute_secure_transfer(
        ledger_equity=700.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        trigger_multiple=1.30,
        transfer_fraction=0.27,
        unit_size_nok=12.0,
    )
    assert r.triggered is True
    assert r.tier == "legacy"
    assert r.transferred == 54.0


def test_runtime_variant_b_config():
    """variant=B uses single-tier even when soft/hard keys remain populated."""
    v2 = capital_v2_cfg(
        {
            "capital_v2": {
                "secure_bucket": {
                    "variant": "B",
                    "trigger_multiple_of_ref": 1.30,
                    "transfer_fraction_of_profit_above_ref": 0.27,
                    # soft/hard still present (defaults merge) — must be ignored
                    "soft_trigger_multiple_of_ref": 1.25,
                    "soft_transfer_fraction": 0.15,
                    "hard_trigger_multiple_of_ref": 1.50,
                    "hard_transfer_fraction": 0.30,
                }
            }
        }
    )
    assert v2["secure_bucket"]["variant"] == "B"
    assert v2["secure_bucket"]["soft_trigger_multiple_of_ref"] == 1.25
    segs = empty_segments(baseline_nok=500.0, oslo_date="2026-07-21")
    segs["unit_hwm_reset_equity_nok"] = 500.0
    out, info = apply_secure_transfer_to_segments(segs, ledger_equity=700.0, v2=v2)
    assert info["triggered"] is True
    assert info["tier"] == "legacy"
    assert info["transferred"] == 54.0  # 0.27 * 200, not soft 0.15 * 200 = 30
    assert out["secure_nok"] == 54.0


def test_legacy_pure_default_transfer_fraction_is_027():
    """Bare legacy call (no soft/hard) uses 0.27, not old 0.40."""
    r = compute_secure_transfer(
        ledger_equity=700.0,
        secure_nok=0.0,
        ref_hwm=500.0,
        unit_size_nok=12.0,
    )
    assert r.triggered is True
    assert r.tier == "legacy"
    assert r.transferred == 54.0


# ── Issue 1: migration fail-closed for missing lock epoch ─────────────────


def test_pre_pr_segments_missing_lock_do_not_auto_unlock(tmp_path: Path):
    """
    Pre-PR capital_segments with secure_nok > 0 and no lock key must NOT
    auto-release on first load when settled_count ≥ 25.
    """
    state = tmp_path / "state"
    state.mkdir()
    path = state / "capital_segments.json"
    # Minimal pre-PR shape (no secure_lock_settled_count)
    path.write_text(
        """{
  "schema_version": 1,
  "secure_nok": 80.0,
  "secure_transfers": [],
  "unit_hwm_reset_equity_nok": 620.0,
  "freeze": {"active": false, "reason": null, "activated_at": null, "unfreeze_requires": "manual"}
}
""",
        encoding="utf-8",
    )
    cfg = {
        "paths": {
            "state_dir": str(state),
            "capital_segments": str(path),
            "bets": str(tmp_path / "bets.csv"),
        },
        "bankroll": {"baseline_nok": 500.0},
        "capital_v2": {"enabled": True},
        "norsk_tipping": {"min_stake_nok": 10},
    }
    segs = load_segments(cfg)
    assert segs["secure_nok"] == 80.0
    assert segs.get("secure_lock_epoch_untrusted") is True

    # High settled count would unlock if lock defaulted to 0
    out, info = maybe_auto_unlock_secure(segs, settled_count=100, v2=_v2_a())
    assert info["unlocked"] is False
    assert info["reason"] == "seeded_lock_epoch_migration"
    assert out["secure_nok"] == 80.0
    assert out["secure_lock_settled_count"] == 100
    assert "secure_lock_epoch_untrusted" not in out

    # Still need 25 more after seed
    out2, info2 = maybe_auto_unlock_secure(out, settled_count=124, v2=_v2_a())
    assert info2["unlocked"] is False
    out3, info3 = maybe_auto_unlock_secure(out, settled_count=125, v2=_v2_a())
    assert info3["unlocked"] is True
    assert out3["secure_nok"] == 0.0


def test_pre_pr_migration_sticky_across_save_without_seed(tmp_path: Path):
    """Saving untrusted segments must not write lock=0 (would break next load)."""
    state = tmp_path / "state"
    state.mkdir()
    path = state / "capital_segments.json"
    path.write_text(
        '{"secure_nok": 50.0, "unit_hwm_reset_equity_nok": 500.0, "freeze": {"active": false}}\n',
        encoding="utf-8",
    )
    cfg = {
        "paths": {"state_dir": str(state), "capital_segments": str(path)},
        "bankroll": {"baseline_nok": 500.0},
    }
    segs = load_segments(cfg)
    assert segs.get("secure_lock_epoch_untrusted") is True
    save_segments(cfg, segs)
    # Disk must omit lock key so migration re-detects
    disk = path.read_text(encoding="utf-8")
    assert "secure_lock_settled_count" not in disk
    segs2 = load_segments(cfg)
    assert segs2.get("secure_lock_epoch_untrusted") is True
    assert segs2["secure_nok"] == 50.0


# ── Issue 3 + 6: sync e2e unlock, liquid floor, same-tick skim skip ────────


def _settled_row(i: int, pl: float = 5.0) -> dict[str, str]:
    return {
        "bet_id": f"b{i}",
        "date": "2026-07-01",
        "match": f"M{i}",
        "selection": "X",
        "decimal_odds": "2.0",
        "stake_nok": "10",
        "result": "Win",
        "p_l_nok": str(pl),
        "payout_nok": "20",
        "sport": "darts",
        "market_type": "Vinner",
        "odds_band": "1.8-2.2",
        "research_grade": "B",
        "phase": "1A",
        "notes": "",
        "source": "test",
        "created_at": "2026-07-01T12:00:00Z",
        "updated_at": "2026-07-01T18:00:00Z",
    }


def _pending_row(stake: float = 30.0) -> dict[str, str]:
    return {
        "bet_id": "pending1",
        "date": "2026-07-21",
        "match": "Open",
        "selection": "Y",
        "decimal_odds": "2.0",
        "stake_nok": str(stake),
        "result": "Pending",
        "p_l_nok": "",
        "payout_nok": "",
        "sport": "darts",
        "market_type": "Vinner",
        "odds_band": "1.8-2.2",
        "research_grade": "B",
        "phase": "1A",
        "notes": "",
        "source": "test",
        "created_at": "2026-07-21T10:00:00Z",
        "updated_at": "2026-07-21T10:00:00Z",
    }


def test_sync_auto_unlock_at_25_and_defers_skim(tmp_path: Path, monkeypatch):
    import nt.capital_runtime as cr
    import nt.capital_v2 as cv

    fixed_day = "2026-07-21"
    monkeypatch.setattr(cv, "oslo_today", lambda: fixed_day)
    monkeypatch.setattr(cr, "oslo_today", lambda: fixed_day)

    state = tmp_path / "state"
    state.mkdir()
    cfg = {
        "paths": {
            "state_dir": str(state),
            "capital_segments": str(state / "capital_segments.json"),
            "bets": str(tmp_path / "bets.csv"),
        },
        "bankroll": {"baseline_nok": 500.0},
        "capital_v2": {
            "enabled": True,
            "secure_bucket": {
                "enabled": True,
                "variant": "A",
                "soft_trigger_multiple_of_ref": 1.25,
                "soft_transfer_fraction": 0.15,
                "hard_trigger_multiple_of_ref": 1.50,
                "hard_transfer_fraction": 0.30,
                "unlock_after_settled": 25,
            },
        },
        "norsk_tipping": {"min_stake_nok": 10},
    }
    segs = empty_segments(baseline_nok=500.0, oslo_date=fixed_day)
    segs["secure_nok"] = 80.0
    segs["unit_hwm_reset_equity_nok"] = 620.0  # post-prior skim ref
    segs["secure_lock_settled_count"] = 10
    save_segments(cfg, segs)

    # 25 settles since lock (10+25=35) — unlock; equity still ≥ soft vs ref 620
    rows = [_settled_row(i) for i in range(35)]
    # equity 1500 would re-soft-skim if not deferred (0.15*(1500-620)=132)
    out = sync_capital_v2_state(
        cfg, 1500.0, rows, persist=True, phase_daily_risk_ceil=42.0
    )
    assert out["secure_nok"] == 0.0
    sync = out.get("_last_sync") or {}
    assert (sync.get("secure_unlock") or {}).get("unlocked") is True
    assert (sync.get("secure_transfer") or {}).get("reason") == (
        "skipped_same_tick_after_unlock"
    )
    assert (sync.get("secure_transfer") or {}).get("triggered") is False

    # Next sync without unlock can skim again
    out2 = sync_capital_v2_state(
        cfg, 1500.0, rows, persist=True, phase_daily_risk_ceil=42.0
    )
    assert out2["secure_nok"] > 0
    assert (out2.get("_last_sync") or {}).get("secure_transfer", {}).get("triggered")


def test_sync_liquid_floor_with_open_pending(tmp_path: Path, monkeypatch):
    import nt.capital_runtime as cr
    import nt.capital_v2 as cv

    fixed_day = "2026-07-21"
    monkeypatch.setattr(cv, "oslo_today", lambda: fixed_day)
    monkeypatch.setattr(cr, "oslo_today", lambda: fixed_day)

    state = tmp_path / "state"
    state.mkdir()
    cfg = {
        "paths": {
            "state_dir": str(state),
            "capital_segments": str(state / "capital_segments.json"),
            "bets": str(tmp_path / "bets.csv"),
        },
        "bankroll": {"baseline_nok": 500.0},
        "capital_v2": {"enabled": True},
        "norsk_tipping": {"min_stake_nok": 10},
    }
    segs = empty_segments(baseline_nok=500.0, oslo_date=fixed_day)
    segs["unit_hwm_reset_equity_nok"] = 500.0
    segs["secure_nok"] = 0.0
    save_segments(cfg, segs)

    # open_risk 660 + ceil 42 → max secure room negative → block soft skim at eq 700
    rows = [_pending_row(660.0)]
    out = sync_capital_v2_state(
        cfg, 700.0, rows, persist=True, phase_daily_risk_ceil=42.0
    )
    assert out["secure_nok"] == 0.0
    xfer = (out.get("_last_sync") or {}).get("secure_transfer") or {}
    assert xfer.get("triggered") is False
    assert xfer.get("reason") == "liquid_floor_blocks_skim"
