from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nt.bankroll import compute_bankroll
from nt.bets_io import load_bets, validate_bets
from nt.config import load_config, path_from_config
from nt.phase import evaluate_phase, load_phase_state
from nt.recommend import refresh_state, run_recommend
from nt.risk import evaluate_risk
from nt.settle import run_settle


def cmd_status(_: argparse.Namespace) -> int:
    cfg = load_config()
    bankroll, phase, risk = refresh_state(cfg)
    print(f"Equity:     {bankroll['equity_nok']:.2f} NOK")
    print(f"Pending:    {bankroll['pending_at_risk_nok']:.2f} NOK")
    print(f"Phase:      {phase['phase_id']} ({phase.get('label','')})")
    print(f"Daily cap:  {risk['daily_risk_cap_nok']:.2f} NOK (remaining {risk['remaining_risk_nok']:.2f})")
    print(f"Can bet:    {risk['can_bet']}")
    print(f"Status:     {path_from_config(cfg, 'status')}")
    return 0


def cmd_validate(_: argparse.Namespace) -> int:
    cfg = load_config()
    rows = load_bets(path_from_config(cfg, "bets"))
    errors = validate_bets(rows)
    bankroll = compute_bankroll(cfg)
    print(f"Rows: {len(rows)} | Errors: {len(errors)}")
    print(f"Equity: {bankroll['equity_nok']:.2f} (baseline {bankroll['baseline_nok']} + PL {bankroll['realized_pl_nok']:+.2f})")
    for e in errors[:20]:
        print(" ERROR:", e)
    return 1 if errors else 0


def cmd_recommend(args: argparse.Namespace) -> int:
    cfg = load_config()
    odds = Path(args.odds)
    if not odds.exists():
        print(f"Odds file not found: {odds}", file=sys.stderr)
        return 2
    result = run_recommend(cfg, odds, log_pending=not args.dry_run)
    print(json.dumps(result, indent=2))
    print(f"\nPlace slip: {result['place_path']}")
    if args.dry_run:
        print("(dry-run: pending bets not logged)")
    return 0


def cmd_settle(args: argparse.Namespace) -> int:
    cfg = load_config()
    path = Path(args.results)
    if not path.exists():
        print(f"Results file not found: {path}", file=sys.stderr)
        return 2
    result = run_settle(cfg, path)
    print(json.dumps(result, indent=2, default=str))
    return 0 if not result["errors"] else 1


def cmd_refresh(_: argparse.Namespace) -> int:
    cfg = load_config()
    bankroll, phase, risk = refresh_state(cfg)
    print(json.dumps({"bankroll": bankroll, "phase": phase, "risk": risk}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nt", description="NT Betting Tracker CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show equity, phase, daily risk").set_defaults(func=cmd_status)
    sub.add_parser("validate", help="Validate bets ledger").set_defaults(func=cmd_validate)
    sub.add_parser("refresh", help="Recompute state files").set_defaults(func=cmd_refresh)

    p_rec = sub.add_parser("recommend", help="Odds file → place slip")
    p_rec.add_argument("--odds", required=True, help="Path to odds csv/md")
    p_rec.add_argument("--dry-run", action="store_true", help="Do not append Pending rows")
    p_rec.set_defaults(func=cmd_recommend)

    p_set = sub.add_parser("settle", help="Results file → settle + update phase/risk")
    p_set.add_argument("--results", required=True, help="Path to results yaml/json/txt")
    p_set.set_defaults(func=cmd_settle)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
