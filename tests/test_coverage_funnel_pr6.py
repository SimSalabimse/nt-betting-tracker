"""PR6: starvation_kind funnel + force_coverage auto-revoke / no-op hygiene."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.control_signals import (
    active_coverage_priority_overlay,
    emit_force_clearability_priority,
    emit_force_coverage_priority,
    load_active_signals,
    maybe_auto_revoke_coverage,
)
from nt.coverage_health import (
    classify_starvation_kind,
    compute_coverage_health,
    compute_funnel_metrics,
    write_coverage_health,
)
from nt.evidence import ev_after_haircut


def _cfg(tmp: Path) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {
            "state_dir": str(state),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
            "coverage_health_json": str(state / "coverage_health.json"),
        },
        "selection": {
            "probability_haircut": 0.03,
            "standard_min_ev": 0.02,
        },
        "research": {
            "coverage_health": {
                "warn_deep_pct": 25,
                "critical_deep_pct": 15,
                "warn_survivable_pct": 45,
                "critical_survivable_pct": 30,
                "critical_mid_unresearched": 5,
                "warn_mid_unresearched": 3,
                "soft_gate": True,
            },
            "tiers": {
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
            },
        },
        "learning": {
            "control_signals": {
                "enabled": True,
                "coverage_priority": {
                    "enabled": True,
                    "auto_revoke_when_ok": True,
                    "ttl_days": 5,
                    "weight_boost": 30.0,
                    "target_odds_band": "1.85-2.60",
                    "prefer": ["alt_totals", "dogs", "handicaps", "period"],
                },
                "clearability_priority": {
                    "enabled": True,
                    "auto_emit": False,
                    "ttl_days": 5,
                },
            }
        },
    }


# ---------------------------------------------------------------------------
# starvation_kind
# ---------------------------------------------------------------------------


def test_starvation_kind_clearability_miss():
    """Deep packs present, mid covered, zero raw EV clears → clearability_miss."""
    kind = classify_starvation_kind(
        level="ok",
        mid_unresearched_n=0,
        shortlist_with_deep_n=8,
        n_raw_ev_pass=0,
        n_picked=0,
        second_pass_completed=False,
    )
    assert kind == "clearability_miss"


def test_starvation_kind_honest_no_edge_after_second_pass():
    kind = classify_starvation_kind(
        level="ok",
        mid_unresearched_n=0,
        shortlist_with_deep_n=8,
        n_raw_ev_pass=0,
        n_picked=0,
        second_pass_completed=True,
    )
    assert kind == "honest_no_edge"


def test_starvation_kind_coverage_critical():
    kind = classify_starvation_kind(
        level="critical",
        mid_unresearched_n=6,
        shortlist_with_deep_n=0,
        n_raw_ev_pass=0,
        n_picked=0,
    )
    assert kind == "coverage_critical"


def test_starvation_kind_research_starvation():
    kind = classify_starvation_kind(
        level="warn",
        mid_unresearched_n=3,
        shortlist_with_deep_n=0,
        n_raw_ev_pass=0,
        n_picked=0,
    )
    assert kind == "research_starvation"


def test_starvation_kind_none_when_clears():
    kind = classify_starvation_kind(
        level="ok",
        mid_unresearched_n=0,
        shortlist_with_deep_n=5,
        n_raw_ev_pass=2,
        n_picked=2,
    )
    assert kind == "none"


def test_funnel_n_raw_ev_pass_from_packs():
    """n_raw_ev_pass uses ev_after_haircut(p, board_odds, 0.03) vs standard_min_ev."""
    haircut = 0.03
    min_ev = 0.02
    # odds 2.0 → need p_adj * 2 - 1 >= 0.02 → p_adj >= 0.51 → p_model >= 0.54
    rows = [
        {"p_model": 0.54, "decimal_odds": 2.0},  # raw ≈ 0.02 → pass
        {"p_model": 0.50, "decimal_odds": 2.0},  # raw ≈ -0.06 → fail
        {"p_model": 0.60, "decimal_odds": 2.2},  # pass
    ]
    for r in rows:
        r["raw"] = ev_after_haircut(r["p_model"], r["decimal_odds"], haircut)

    funnel = compute_funnel_metrics(rows, {"selection": {"probability_haircut": haircut, "standard_min_ev": min_ev}})
    assert funnel["n_packs_with_p"] == 3
    assert funnel["n_raw_ev_pass"] == 2
    assert funnel["median_raw_ev"] is not None
    assert 0.0 < funnel["clearable_track_share"] <= 1.0
    assert funnel["second_pass_ran"] is False


def test_compute_coverage_health_clearability_miss(tmp_path: Path):
    cfg = _cfg(tmp_path)
    # 6 deep mid packs with market-mimic p → raw_ev fail; no mid unresearched
    shortlist = []
    for i in range(6):
        shortlist.append(
            {
                "match": f"M{i}",
                "selection": "Vinner: Home",
                "decimal_odds": 2.0,
                "p_model": 0.50,  # after 3pp → EV -0.06
                "has_p_model": True,
                "has_evidence": True,
                "market_family": "ml",
            }
        )
    health = compute_coverage_health(
        cfg,
        shortlist,
        shortlist=shortlist,
        source="test",
        n_picked=0,
        second_pass_completed=False,
    )
    assert health["mid_unresearched_n"] == 0
    assert health["shortlist_with_deep_n"] == 6
    assert health["n_raw_ev_pass"] == 0
    assert health["starvation_kind"] == "clearability_miss"
    assert health["level"] == "ok"
    assert "funnel" in health
    assert health["funnel"]["n_raw_ev_pass"] == 0


def test_compute_coverage_health_honest_no_edge(tmp_path: Path):
    cfg = _cfg(tmp_path)
    shortlist = [
        {
            "match": "A",
            "selection": "Over 2.5",
            "decimal_odds": 2.1,
            "p_model": 0.48,
            "has_p_model": True,
            "has_evidence": True,
        }
    ]
    health = compute_coverage_health(
        cfg,
        shortlist,
        shortlist=shortlist,
        n_picked=0,
        second_pass_completed=True,
        second_pass_ran=True,
    )
    assert health["starvation_kind"] == "honest_no_edge"
    assert health["second_pass_ran"] is True


# ---------------------------------------------------------------------------
# force_coverage auto-revoke / no-op (T15)
# ---------------------------------------------------------------------------


def test_force_coverage_overlay_noop_when_ok_mid_zero(tmp_path: Path):
    cfg = _cfg(tmp_path)
    emit = emit_force_coverage_priority(cfg, source="research_starvation")
    assert emit["ok"] and emit.get("emitted") is not False

    active = load_active_signals(cfg, kinds=("force_coverage_priority",))
    assert len(active) >= 1

    # Recovered coverage → overlay no-op even though signal still unexpired
    health = {
        "level": "ok",
        "mid_unresearched_n": 0,
    }
    ov = active_coverage_priority_overlay(cfg, coverage_health=health)
    assert ov["force_coverage_emitted"] is True
    assert ov["no_op"] is True
    assert ov["active"] is False
    assert ov["force_coverage_overlay_active"] is False

    # Still mid-unresearched → overlay stays active
    ov2 = active_coverage_priority_overlay(
        cfg, coverage_health={"level": "warn", "mid_unresearched_n": 4}
    )
    assert ov2["active"] is True
    assert ov2["no_op"] is False


def test_auto_revoke_coverage_when_ok(tmp_path: Path):
    cfg = _cfg(tmp_path)
    emit_force_coverage_priority(cfg, source="research_starvation")
    assert load_active_signals(cfg, kinds=("force_coverage_priority",))

    health = {
        "level": "ok",
        "mid_unresearched_n": 0,
        "shortlist_with_deep_n": 8,
        "shortlist_deep_pct": 80.0,
    }
    write_coverage_health(cfg, health)

    out = maybe_auto_revoke_coverage(cfg, coverage_health=health, actor="pytest")
    assert out["revoked"] is True
    assert out["reason"] == "coverage_recovered"
    assert load_active_signals(cfg, kinds=("force_coverage_priority",)) == []

    # Overlay inactive after revoke
    ov = active_coverage_priority_overlay(cfg, coverage_health=health)
    assert ov["active"] is False
    assert ov["force_coverage_emitted"] is False


def test_auto_revoke_skips_when_mid_unresearched(tmp_path: Path):
    cfg = _cfg(tmp_path)
    emit_force_coverage_priority(cfg)
    out = maybe_auto_revoke_coverage(
        cfg,
        coverage_health={"level": "ok", "mid_unresearched_n": 2},
    )
    assert out["revoked"] is False
    assert load_active_signals(cfg, kinds=("force_coverage_priority",))


def test_force_clearability_ops_emit_path(tmp_path: Path):
    """Ops-only emit path works; auto default off."""
    cfg = _cfg(tmp_path)
    out = emit_force_clearability_priority(cfg, source="manual", actor="ops")
    assert out["ok"] and out.get("emitted") is not False
    active = load_active_signals(cfg, kinds=("force_clearability_priority",))
    assert len(active) == 1
    assert active[0]["kind"] == "force_clearability_priority"

    from nt.control_signals import maybe_auto_emit_clearability

    # auto_emit false → no-op even with clearability_miss
    auto = maybe_auto_emit_clearability(
        cfg, starvation_kind="clearability_miss", consecutive_clearability_miss=5
    )
    assert auto.get("emitted") is False
    assert auto.get("reason") == "auto_emit_off"
