#!/usr/bin/env python3
"""
Full settlement flow - runs after user provides settlement results.
This will:
1. Settle the bets
2. Update bankroll
3. Generate updated performance report
"""
import sys
import os

# Add parent to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settle_bets import settle_bet
from update_bankroll import update_bankroll_after_settlement
from generate_performance_report import generate_report

def run_full_settlement(settlements, note=""):
    """
    settlements: list of dicts with bet_id, result, p_l_nok, notes
    """
    settled_count = 0
    for s in settlements:
        success = settle_bet(s["bet_id"], s["result"], s["p_l_nok"], s.get("notes"))
        if success:
            settled_count += 1

    new_equity, pending = update_bankroll_after_settlement(note)
    generate_report()

    print(f"Settled {settled_count} bets.")
    print(f"New Equity: {new_equity:.2f} NOK | Pending at Risk: {pending:.2f} NOK")
    print("Performance report updated.")

if __name__ == "__main__":
    print("Full settlement orchestrator - to be called by Grok with data.")