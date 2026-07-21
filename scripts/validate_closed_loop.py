#!/usr/bin/env python3
"""CLI: closed-loop + PhaseState validation over settled book."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.closed_loop_validation import (
    render_validation_markdown,
    replay_closed_loop,
    validate_size_mode_floor_invariant,
)
from nt.bankroll import compute_bankroll
from nt.bets_io import load_bets
from nt.config import load_config, path_from_config
from nt.control_signals import (
    emit_temp_gate_raise,
    load_active_signals,
    revoke_signals,
)
from nt.settlement_review import auto_resolve_learning_proposals, learning_proposals_path


def check_thin_sample(tmp: Path) -> dict:
    """Unit-style: full delta only n>=8 conf>=0.40."""
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    (tmp / "data").mkdir(exist_ok=True)
    bets = tmp / "data" / "bets.csv"
    bets.write_text(
        "bet_id,date,match,selection,decimal_odds,stake_nok,result,p_l_nok,payout_nok,"
        "research_grade,odds_band,sport,market_type,phase,notes,source,created_at,updated_at\n",
        encoding="utf-8",
    )
    learn = state / "learning.json"
    learn.write_text(
        json.dumps({"sports": {"tennis": {"stake_mult": 1.0, "ev_boost": 0.0, "n": 10}}}),
        encoding="utf-8",
    )
    cfg = {
        "paths": {
            "bets": str(bets),
            "state_dir": str(state),
            "learning_json": str(learn),
            "learning_proposals_json": str(state / "learning_proposals.json"),
            "outbox": str(tmp / "outbox"),
        },
        "learning": {"enabled": True, "auto_apply_proposals": True, "min_sample": 12},
        "bankroll": {"baseline_nok": 500},
    }

    def write_prop(n: int, conf: float) -> str:
        path = learning_proposals_path(cfg)
        pid = f"sport:tennis:val-{n}-{conf}"
        path.write_text(
            json.dumps(
                {
                    "proposals": [
                        {
                            "id": pid,
                            "kind": "sport",
                            "name": "tennis",
                            "status": "pending",
                            "current": {"stake_mult": 1.0, "ev_boost": 0.0, "n": n},
                            "proposed": {"stake_mult": 1.05, "ev_boost": 0.01},
                            "layers": {"confidence": conf},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return pid

    p_thin = write_prop(5, 0.50)
    o1 = auto_resolve_learning_proposals(cfg)
    p_full = write_prop(8, 0.45)
    o2 = auto_resolve_learning_proposals(cfg)
    return {
        "thin_n5_not_full_accept": p_thin in o1.get("modified", [])
        or p_thin not in o1.get("accepted", []),
        "full_n8_accepted": p_full in o2.get("accepted", []),
        "o1": o1,
        "o2": o2,
        "ok": (p_thin not in o1.get("accepted", [])) and (p_full in o2.get("accepted", [])),
    }


def check_ttl_revoke(tmp: Path) -> dict:
    state = tmp / "state"
    state.mkdir(parents=True, exist_ok=True)
    cfg = {
        "paths": {
            "state_dir": str(state),
            "control_signals_jsonl": str(state / "control_signals.jsonl"),
        },
        "learning": {
            "control_signals": {
                "enabled": True,
                "min_ev_raise": 0.02,
                "max_raise": 0.05,
                "ttl_days": 10,
                "force_confirmed_lineup": True,
            }
        },
    }
    emit_temp_gate_raise(cfg, sport="tennis", bet_id="v1", source="process_error")
    n1 = len(load_active_signals(cfg))
    revoke_signals(cfg, sport="tennis", actor="validate")
    n2 = len(load_active_signals(cfg))
    return {"after_emit": n1, "after_revoke": n2, "ok": n1 >= 1 and n2 == 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--out",
        default="",
        help="Markdown report path (default artifacts/CLOSED_LOOP_VALIDATION.md)",
    )
    args = ap.parse_args()
    cfg = load_config()
    report = replay_closed_loop(cfg, n=args.n)

    # Extra invariant checks
    import tempfile
    from pathlib import Path as P

    tdir = P(tempfile.mkdtemp())
    thin = check_thin_sample(tdir / "thin")
    ttl = check_ttl_revoke(tdir / "ttl")
    report["thin_sample_check"] = thin
    report["ttl_revoke_check"] = ttl
    report["pass"] = bool(report.get("pass")) and thin.get("ok") and ttl.get("ok")

    md = render_validation_markdown(report)
    md += "\n## Thin-sample protection\n\n"
    md += f"- n=5 conf=0.5 must not full-accept: **{thin.get('thin_n5_not_full_accept')}**\n"
    md += f"- n=8 conf=0.45 full-accept: **{thin.get('full_n8_accepted')}**\n"
    md += "\n## TTL / revoke\n\n"
    md += f"- After emit active≥1: **{ttl.get('after_emit')}** · after revoke 0: **{ttl.get('after_revoke')}**\n"
    md += f"\n**Overall PASS:** {report.get('pass')}\n"

    out = Path(args.out) if args.out else ROOT / "artifacts" / "CLOSED_LOOP_VALIDATION.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(md)
        print(f"\nWrote {out}")
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
