#!/usr/bin/env python3
"""
Verify reasoning-chain residuals (near-miss SSOT, light join, blocked emit).

Default path is fully synthetic (no live odds required):

  python scripts/verify_chain_residuals.py

Prints chain counts for picks / near_misses / rejected_prefilter and asserts
promo fields present when light is joined.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.portfolio import Recommendation
from nt.reasoning_chain import (
    build_recommend_chains,
    dump_reasoning_for_recommend,
    format_reasoning_md,
)


def _cfg(state: Path) -> dict[str, Any]:
    outbox = state / "outbox"
    light = outbox / "light_research"
    light.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {
            "state_dir": str(state),
            "outbox": str(outbox),
            "reasoning_chains_jsonl": str(state / "reasoning_chains.jsonl"),
        },
        "selection": {"probability_haircut": 0.03},
        "reasoning": {
            "enabled": True,
            "jsonl": str(state / "reasoning_chains.jsonl"),
            "max_near_miss": 8,
            "near_miss_ev_slack": 0.04,
            "place_md_section": True,
            "join_light": True,
        },
        "research": {
            "tiers": {
                "short_chalk_odds": 1.70,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "soft_value_min_rel": 0.03,
                "promo_mid_band_boost": 60,
                "promo_alt_boost": 14,
                "promo_short_chalk_penalty": -55,
            }
        },
    }


def _write_light(cfg: dict[str, Any]) -> None:
    outbox = Path(cfg["paths"]["outbox"])
    light_dir = outbox / "light_research"
    payload = {
        "records": [
            {
                "match": "Verify vs Light",
                "selection": "Over 3.5",
                "sport": "football",
                "decimal_odds": 2.05,
                "odds_band": "1.85-2.20",
                "market_family": "totals_over",
                "verdict": "pass",
                "promote_to_deep": True,
                "has_p_model": False,
                "has_deep_pack": False,
                "reason": "engine deep queue",
                "rough_ev_note": "need p",
            },
            {
                "match": "Verify vs Prefilter",
                "selection": "ML",
                "sport": "football",
                "decimal_odds": 1.95,
                "market_family": "ml",
                "verdict": "fail",
                "has_p_model": False,
                "prefilter_stage1": "fail: noise",
                "discarded": True,
                "reason": "prefilter discard",
            },
        ],
        "deep_queue": [
            {
                "match": "Verify vs Light",
                "selection": "Over 3.5",
                "decimal_odds": 2.05,
                "reason": "deep queue",
            }
        ],
        "shortlist_n": 2,
    }
    (light_dir / "LATEST.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _count_kinds(chains: list[dict[str, Any]]) -> dict[str, int]:
    out = {"pick": 0, "near_miss": 0, "rejected_prefilter": 0, "other": 0}
    for c in chains:
        k = str(c.get("kind") or "other")
        if k in out:
            out[k] += 1
        else:
            out["other"] += 1
    return out


def run_verify(*, verbose: bool = True) -> dict[str, Any]:
    state = Path(tempfile.mkdtemp(prefix="chain_residuals_"))
    cfg = _cfg(state)
    _write_light(cfg)

    errors: list[str] = []

    # 1) Empty picks + rejects → near-miss section
    rejects = [
        {
            "match": "Verify vs Light",
            "selection": "Over 3.5",
            "reason": "EV 0.01 < min_ev 0.03",
            "ev": 0.01,
            "odds": 2.05,
            "p_model": 0.50,
            "grade": "B",
        }
    ]
    chains_empty = build_recommend_chains(cfg, [], rejects, phase_id="1A")
    counts_empty = _count_kinds(chains_empty)
    md_empty = format_reasoning_md(chains_empty)
    if "## Near-miss / Rejected" not in md_empty:
        errors.append("empty picks missing ## Near-miss / Rejected")
    if counts_empty["near_miss"] + counts_empty["rejected_prefilter"] < 1:
        errors.append(f"empty picks expected near-miss chains, got {counts_empty}")

    # 2) Blocked emit
    place = "# blocked\n"
    updated, chains_blocked, _path = dump_reasoning_for_recommend(
        cfg,
        [],
        [
            {
                "match": "Verify vs Light",
                "selection": "Over 3.5",
                "odds": 2.05,
                "reason": "no p_model / blocked recommend",
                "near_miss": True,
                "rejected_at_stage": "blocked_no_research",
                "source": "blocked",
            }
        ],
        place_md=place,
        phase_id="1A",
        blocked=True,
        block_reason="no_research",
    )
    counts_blocked = _count_kinds(chains_blocked)
    if not chains_blocked:
        errors.append("blocked recommend emitted zero chains")
    if "## Near-miss / Rejected" not in updated:
        errors.append("blocked PLACE_THESE missing Near-miss section")

    # 3) Light join promo on pick
    pick = Recommendation(
        match="Verify vs Light",
        selection="Over 3.5",
        decimal_odds=2.05,
        stake_nok=12.0,
        ev=0.05,
        grade="B",
        odds_band="1.85-2.20",
        sport="football",
        market_type="total",
        p_model=0.53,
        notes="p_model=0.5300 only",
    )
    chains_pick = build_recommend_chains(cfg, [pick], [], phase_id="1A")
    counts_pick = _count_kinds(chains_pick)
    pick_chain = next((c for c in chains_pick if c.get("kind") == "pick"), None)
    if pick_chain is None:
        errors.append("pick chain missing")
    else:
        light = pick_chain.get("light") or {}
        if light.get("promotion_score") is None:
            errors.append("light join missing promotion_score on pick chain")
        comps = light.get("promotion_score_components") or (
            (light.get("promotion_score_breakdown") or {}).get("components")
        )
        if not comps:
            errors.append("light join missing promotion_score_components on pick chain")

    report = {
        "ok": not errors,
        "errors": errors,
        "counts_empty_picks": counts_empty,
        "counts_blocked": counts_blocked,
        "counts_with_pick": counts_pick,
        "state_dir": str(state),
        "n_chains_empty": len(chains_empty),
        "n_chains_blocked": len(chains_blocked),
        "n_chains_with_pick": len(chains_pick),
        "pick_promo": (pick_chain or {}).get("light", {}).get("promotion_score")
        if pick_chain
        else None,
        "pick_promo_components": bool(
            ((pick_chain or {}).get("light") or {}).get("promotion_score_components")
            or ((pick_chain or {}).get("light") or {}).get("promotion_score_breakdown")
        )
        if pick_chain
        else False,
    }
    if verbose:
        print("=== verify_chain_residuals ===")
        print(json.dumps(report, indent=2, default=str))
        if errors:
            print("\nFAIL:", "; ".join(errors), file=sys.stderr)
        else:
            print("\nOK: picks/near_misses/rejected counts + light promo join")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    rep = run_verify(verbose=not args.quiet)
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
