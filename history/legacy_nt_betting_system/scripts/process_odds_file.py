#!/usr/bin/env python3
"""
Main entry point for processing an odds file.
This is the script Grok will primarily use when you provide an odds file.
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from recommend_from_odds_file import analyze_odds_file
from add_pending_bets import add_pending_bet

def process_odds_file(odds_list):
    """
    Main function to process a list of odds and log recommended bets.
    odds_list: list of dictionaries with match details.
    """
    recommendations, mode = analyze_odds_file(odds_list)

    logged_bets = []
    for rec in recommendations:
        bet_id = add_pending_bet(
            date=datetime.now().date().isoformat(),
            match=rec["match"],
            selection=rec["selection"],
            decimal_odds=rec["odds"],
            stake_nok=rec.get("recommended_stake", 10),
            notes=f"Mode: {rec['mode_used']}. {rec.get('rationale', '')}"
        )
        logged_bets.append(bet_id)

    return recommendations, logged_bets, mode

if __name__ == "__main__":
    print("process_odds_file.py - Main entry point for new odds files.")