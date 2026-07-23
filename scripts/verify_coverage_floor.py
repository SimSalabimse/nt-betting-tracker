#!/usr/bin/env python3
"""
Verify coverage floor (Mechanism A) + temp_ev_relax trigger fail-closed (Mechanism B).

Default path is fully synthetic (no live odds required):

  python scripts/verify_coverage_floor.py --synthetic-large

Optional real odds:

  python scripts/verify_coverage_floor.py --odds inbox/odds_….txt
"""
from __future__ import annotations

import argparse
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.control_signals import maybe_emit_temp_ev_relax
from nt.light_research import (
    LightRecord,
    build_deep_queue,
    coverage_floor_cfg,
    dynamic_deep_target_n,
)


def _cfg(
    *,
    floor_enabled: bool = True,
    dynamic: bool = True,
    state_dir: Path | None = None,
    min_board_matches: int = 15,
) -> dict[str, Any]:
    state = state_dir or Path(tempfile.mkdtemp(prefix="cov_floor_verify_"))
    state.mkdir(parents=True, exist_ok=True)
    return {
        "paths": {
            "state_dir": str(state),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
            "outbox": str(state / "outbox"),
        },
        "research": {
            "tiers": {
                "engine_deep_queue": True,
                "auto_promote_to_deep": False,
                "deep_target_n": 8,
                "deep_max_n": 15,
                "deep_target_dynamic": dynamic,
                "deep_target_min": 8,
                "deep_target_max": 15,
                "deep_target_divisor": 8,
                "deep_min_preferred_share": 0.55,
                "deep_max_short_main_share": 0.25,
                "short_chalk_odds": 1.70,
                "preferred_odds_lo": 1.85,
                "preferred_odds_hi": 2.60,
                "alt_preferred_odds_lo": 1.80,
                "promo_mid_band_boost": 60,
                "promo_alt_boost": 14,
                "promo_short_chalk_penalty": -55,
            },
            "coverage_floor": {
                "enabled": floor_enabled,
                "top_promo_scaffold_pct": 0.20,
                "sport_rotation_min_lines": 5,
                "require_real_pack": True,
                "coverage_pressure_boost": 40.0,
            },
        },
        "selection": {
            "probability_haircut": 0.03,
            "standard_min_ev": 0.03,
            "high_odds_threshold": 2.5,
        },
        "learning": {
            "control_signals": {
                "enabled": True,
                "temp_ev_relax": {
                    "enabled": True,
                    "delta_min": 0.01,
                    "delta_max": 0.02,
                    "ttl_hours": 24,
                    "stake_mult": 0.80,
                    "top_n_survivors": 3,
                    "min_board_matches": min_board_matches,
                    "require_coverage_warn": True,
                    "exclude_high_odds": True,
                    "exclude_grade_c": True,
                },
            }
        },
    }


def _rec(
    match: str,
    selection: str,
    sport: str,
    odds: float,
    *,
    family: str = "handicap",
    verdict: str = "pass",
    has_p_model: bool = False,
) -> LightRecord:
    return LightRecord(
        match=match,
        selection=selection,
        sport=sport,
        decimal_odds=odds,
        odds_band="1.8-2.2",
        market_family=family,
        verdict=verdict,
        has_p_model=has_p_model,
        promote_to_deep=False,
        source="auto",
    )


def synthetic_large_board() -> list[LightRecord]:
    """Multi-sport preferred-heavy board (~40+ lines) for floor checks."""
    recs: list[LightRecord] = []
    for i in range(14):
        recs.append(
            _rec(
                f"FBL {i} vs Opp",
                "Handikap -1.5: Away" if i % 2 == 0 else "Over 3.5",
                "football",
                2.05 + (i % 4) * 0.05,
                family="handicap" if i % 2 == 0 else "totals_over",
            )
        )
    for i in range(8):
        recs.append(
            _rec(
                f"Tennis A{i} vs B{i}",
                f"Vinner: A{i}",
                "tennis",
                1.95 + (i % 3) * 0.08,
                family="ml",
            )
        )
    for i in range(8):
        recs.append(
            _rec(
                f"NBA H{i} vs A{i}",
                "Handikap -4.5: Away" if i < 6 else f"Vinner: H{i}",
                "basketball",
                2.10 + i * 0.03 if i < 6 else 1.55,
                family="handicap" if i < 6 else "ml",
            )
        )
    for i in range(6):
        recs.append(
            _rec(
                f"HB {i}",
                "Over 55.5",
                "handball",
                1.92,
                family="totals_over",
            )
        )
    # chalk noise
    for i in range(4):
        recs.append(
            _rec(
                f"Chalk {i}",
                "Vinner: Fav",
                "football",
                1.45,
                family="ml",
            )
        )
    return recs


def _pass(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"[{status}] {label}{extra}")
    return ok


def run_synthetic_large() -> int:
    failures = 0
    cfg = _cfg(floor_enabled=True, dynamic=True)
    recs = synthetic_large_board()
    n = len(recs)
    print(f"Synthetic board: n={n} sports={{football,tennis,basketball,handball}}")

    # 1) dynamic target
    target = dynamic_deep_target_n(cfg, n)
    # board_lines // 8 clamped to [8, 15]
    expected = max(8, min(15, n // 8))
    if not _pass(
        "dynamic_deep_target_n",
        target == expected and target >= 8,
        f"got {target}, expected {expected} (n={n})",
    ):
        failures += 1

    # 2) scaffold tags on large board
    q = build_deep_queue(list(recs), cfg, board_lines=n)
    scaffolded = [
        r
        for r in recs
        if "coverage_floor:top_promo_scaffold" in (r.rough_ev_note or "")
        and "blocked" not in (r.rough_ev_note or "")
    ]
    # After build, tags are on original recs; recount candidates pass/no-pmodel
    n_cand = sum(
        1
        for r in recs
        if r.verdict == "pass"
        and not r.has_p_model
        and not r.script_conflict
        and not r.base_rate_conflict
    )
    n_scaffold_expect = max(1, math.ceil(0.20 * n_cand)) if n_cand else 0
    # tags include blocked variants; count any scaffold mention
    scaffold_any = sum(
        1 for r in recs if "coverage_floor:top_promo_scaffold" in (r.rough_ev_note or "")
    )
    if not _pass(
        "scaffold_tags_present",
        scaffold_any >= max(1, n_scaffold_expect // 2),
        f"scaffold tags={scaffold_any} (expect ~{n_scaffold_expect} of {n_cand} candidates); queue n={len(q)}",
    ):
        failures += 1

    # 3) sport rotation — handball has ≥5 eligible preferred → at least one handball or rotation tag
    sports_in_q = {(r.sport or "").lower() for r in q}
    rot_tags = sum(1 for r in recs if "coverage_floor:sport_rotation" in (r.rough_ev_note or ""))
    handball_in_q = "handball" in sports_in_q
    if not _pass(
        "sport_rotation_behavior",
        handball_in_q or rot_tags > 0,
        f"handball_in_queue={handball_in_q}, rotation_tags={rot_tags}, sports={sorted(sports_in_q)}",
    ):
        failures += 1

    # 4) temp_ev_relax fail-closed on small board
    small_cfg = _cfg(min_board_matches=15)
    small = maybe_emit_temp_ev_relax(
        small_cfg,
        board_matches=3,  # well below min 15
        coverage_level="critical",
        deep_queue_n=0,
        survivors=[
            {
                "match": "A vs B",
                "selection": "Handikap -1.5: Away",
                "decimal_odds": 2.10,
                "promotion_score": 90.0,
            }
        ],
    )
    if not _pass(
        "temp_ev_relax_fail_closed_small_board",
        small.get("ok") is False and small.get("reason") == "board_matches_below_min",
        f"result={small}",
    ):
        failures += 1

    # Bonus: large board + empty queue + warn can emit (when survivors present)
    large_emit = maybe_emit_temp_ev_relax(
        small_cfg,
        board_matches=20,
        coverage_level="warn",
        deep_queue_n=0,
        survivors=[
            {
                "match": f"M{i}",
                "selection": "Handikap -1.5: Away",
                "decimal_odds": 2.05 + i * 0.02,
                "promotion_score": 80.0 - i,
            }
            for i in range(5)
        ],
    )
    _pass(
        "temp_ev_relax_can_emit_on_large_empty_queue",
        large_emit.get("ok") is True,
        f"result ok={large_emit.get('ok')} reason={large_emit.get('reason')}",
    )
    # do not count bonus as hard failure for overall exit if unexpected — but track
    if not large_emit.get("ok"):
        failures += 1

    cfc = coverage_floor_cfg(cfg)
    print(
        f"\nConfig: coverage_floor.enabled={cfc.get('enabled')} "
        f"scaffold_pct={cfc.get('top_promo_scaffold_pct')} "
        f"sport_rotation_min={cfc.get('sport_rotation_min_lines')}"
    )
    print(f"Deep queue size: {len(q)} (target effective={target})")
    return 1 if failures else 0


def run_odds(odds_path: Path) -> int:
    """Optional real-odds path: parse → light-ish queue build if possible."""
    if not odds_path.is_file():
        print(f"[FAIL] odds file not found: {odds_path}")
        return 1
    print(f"Odds path present: {odds_path} ({odds_path.stat().st_size} bytes)")
    print("[PASS] odds_file_present")
    print("Note: full light research not forced here; use --synthetic-large for unit checks.")
    # Still run synthetic suite so exit code remains meaningful
    return run_synthetic_large()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--synthetic-large",
        action="store_true",
        help="Build multi-sport synthetic board and verify floor + temp_ev_relax fail-closed",
    )
    p.add_argument("--odds", type=Path, default=None, help="Optional real odds file path")
    args = p.parse_args(argv)

    if args.odds is not None:
        return run_odds(args.odds)
    # Default = synthetic-large (also when flag set)
    return run_synthetic_large()


if __name__ == "__main__":
    raise SystemExit(main())
