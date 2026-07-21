"""Analyze results.txt + odds file against ledger (read-only / dry)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.bets_io import fnum, load_bets
from nt.config import load_config, path_from_config
from nt.odds_parse import parse_odds_file
from nt.pl import pl_from_outcome, pl_from_payout, payout_from_outcome
from nt.settle import _match_bet, _parse_results


def main() -> int:
    cfg = load_config()
    rows = load_bets(path_from_config(cfg, "bets"))
    pending = [r for r in rows if r.get("result") == "Pending"]

    print("=== LEDGER SNAPSHOT ===")
    bank = sum(fnum(r.get("p_l_nok")) or 0 for r in rows if r.get("result") != "Pending")
    print(f"total_bets={len(rows)} pending={len(pending)}")
    print()
    print("=== OPEN PENDING ===")
    for r in pending:
        print(
            f"  {r.get('bet_id')}  {r.get('date')}  "
            f"{r.get('match')}  |  {r.get('selection')}  "
            f"@{r.get('decimal_odds')}  stake={r.get('stake_nok')}  {r.get('sport')}"
        )

    results_path = ROOT / "inbox" / "results.txt"
    items = _parse_results(results_path)
    print()
    print("=== RESULTS.TXT PARSED ===")
    print(f"n_items={len(items)}")
    for it in items:
        print(f"  {it}")

    print()
    print("=== SETTLE PREVIEW (no write) ===")
    total_pl = 0.0
    matched = 0
    for item in items:
        bet = _match_bet(rows, item)
        if not bet:
            print(f"  NO MATCH → {item}")
            continue
        if bet.get("result") != "Pending":
            print(f"  ALREADY SETTLED → {bet.get('bet_id')} {item}")
            continue
        stake = fnum(bet.get("stake_nok")) or 0.0
        odds = fnum(bet.get("decimal_odds")) or 0.0
        payout = item.get("payout_nok")
        if payout is not None:
            payout = float(payout)
            pl = pl_from_payout(stake, payout)
            if payout <= 0:
                res = "Loss"
            elif abs(payout - stake) < 0.05:
                res = "Refunded"
            else:
                res = "Win"
        else:
            outcome = str(item.get("outcome") or item.get("result") or "").strip()
            pl = pl_from_outcome(stake, odds, outcome)
            payout = payout_from_outcome(stake, odds, outcome)
            ol = outcome.lower()
            if ol in ("win", "won", "w"):
                res = "Win"
            elif ol in ("loss", "lost", "l"):
                res = "Loss"
            elif ol in ("refund", "refunded", "void", "push"):
                res = "Refunded"
            else:
                res = outcome
        matched += 1
        total_pl += pl
        print(
            f"  {res:8}  PL {pl:+7.2f}  "
            f"id={bet.get('bet_id')}  "
            f"{(bet.get('match') or '')[:48]}  |  {bet.get('selection')}  "
            f"stake={stake} @{odds} payout={payout}"
        )
    print(f"matched={matched}/{len(items)}  preview_PL={total_pl:+.2f} NOK")

    odds_path = ROOT / "inbox" / "odds_17-07.2026.txt"
    print()
    print("=== ODDS FILE STRUCTURE ===")
    cands = parse_odds_file(odds_path)
    print(f"candidates={len(cands)}")
    by_sport: dict[str, int] = {}
    by_market: dict[str, int] = {}
    matches: set[str] = set()
    for c in cands:
        sp = (getattr(c, "sport", None) or (c.get("sport") if isinstance(c, dict) else None) or "?")
        mk = (
            getattr(c, "market_macro", None)
            or getattr(c, "market", None)
            or (c.get("market_macro") if isinstance(c, dict) else None)
            or "?"
        )
        m = getattr(c, "match", None) or (c.get("match") if isinstance(c, dict) else None) or ""
        by_sport[str(sp)] = by_sport.get(str(sp), 0) + 1
        by_market[str(mk)] = by_market.get(str(mk), 0) + 1
        if m:
            matches.add(str(m))
    print(f"unique_matches={len(matches)}")
    print("by_sport:", dict(sorted(by_sport.items(), key=lambda x: -x[1])))
    print("by_market_macro (top):", dict(sorted(by_market.items(), key=lambda x: -x[1])[:12]))
    print("matches:")
    for m in sorted(matches):
        print(f"  - {m}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
