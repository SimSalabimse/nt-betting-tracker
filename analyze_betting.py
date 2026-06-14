#!/usr/bin/env python3
"""
NT Betting Tracker Analysis Script
- Computes exact Bankroll, Pending at Risk, Liquid per strict rule
- Per-sport ROI, volume, hit rate
- Flags low-volume high-ROI or exploration priority sports
- Run after every settlement batch for verification

Usage: python analyze_betting.py [path_to_bet_log.csv]
"""

import pandas as pd
import sys
from datetime import datetime

def analyze_bet_log(csv_path="bet_log.csv"):
    df = pd.read_csv(csv_path)
    
    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    # Ensure numeric
    df['Stake_NOK'] = pd.to_numeric(df['Stake_NOK'], errors='coerce').fillna(0)
    df['P_L_NOK'] = pd.to_numeric(df['P_L_NOK'], errors='coerce').fillna(0)
    
    # Bankroll Calculation (Strict Rule)
    settled_mask = df['Result'].str.lower() != 'pending'
    pending_mask = df['Result'].str.lower() == 'pending'
    
    initial_bankroll = 500.0
    realized_pl = df.loc[settled_mask, 'P_L_NOK'].sum()
    bankroll_equity = initial_bankroll + realized_pl
    
    pending_at_risk = df.loc[pending_mask, 'Stake_NOK'].sum()
    liquid_available = bankroll_equity - pending_at_risk
    
    print("=" * 60)
    print("NT BETTING TRACKER - STRICT BANKROLL VERIFICATION")
    print(f"Run at: {datetime.now().isoformat()}")
    print("=" * 60)
    print(f"Initial Bankroll: {initial_bankroll:.2f} NOK")
    print(f"Realized P/L (all settled): {realized_pl:+.2f} NOK")
    print(f"**Bankroll (Equity): {bankroll_equity:.2f} NOK**")
    print(f"Pending at Risk: {pending_at_risk:.2f} NOK")
    print(f"**Liquid Available for new bets: {liquid_available:.2f} NOK**")
    print("=" * 60)
    
    # Per-Sport Analysis
    print("\nPER-SPORT PERFORMANCE (Settled bets only):")
    sport_summary = []
    for sport in ['Fotball', 'Darts', 'Snooker', 'Tennis', 'Ishockey', 'Handball', 'Esports', 'Basketball', 'MLB', 'F1', 'Sjakk', 'Golf']:
        mask = df['Match'].str.contains(sport, case=False, na=False) | df['Selection'].str.contains(sport, case=False, na=False)
        settled_sport = df[mask & settled_mask]
        if len(settled_sport) > 0:
            wins = len(settled_sport[settled_sport['P_L_NOK'] > 0])
            total = len(settled_sport)
            hit_rate = wins / total * 100 if total > 0 else 0
            roi = settled_sport['P_L_NOK'].sum() / settled_sport['Stake_NOK'].sum() * 100 if settled_sport['Stake_NOK'].sum() > 0 else 0
            sport_summary.append({
                'Sport': sport,
                'Bets': total,
                'Wins': wins,
                'Hit_Rate_%': round(hit_rate, 1),
                'ROI_%': round(roi, 1),
                'Total_Stake': settled_sport['Stake_NOK'].sum(),
                'Net_P/L': round(settled_sport['P_L_NOK'].sum(), 2)
            })
    
    if sport_summary:
        summary_df = pd.DataFrame(sport_summary)
        print(summary_df.to_string(index=False))
    
    # Exploration Flags
    print("\nEXPLORATION & LEARNING FLAGS:")
    low_volume_positive = [s for s in sport_summary if s['Bets'] < 15 and s['ROI_%'] > 5]
    if low_volume_positive:
        print("Sports with LOW VOLUME but POSITIVE ROI (prioritize testing):")
        for s in low_volume_positive:
            print(f"  - {s['Sport']}: {s['Bets']} bets, {s['ROI_%']}% ROI, {s['Hit_Rate_%']}% hit rate")
    else:
        print("No strong low-volume positive signals currently (or insufficient data).")
    
    # Pending bets detail
    if pending_mask.any():
        print("\nCURRENT PENDING BETS:")
        pending_df = df[pending_mask][['Date', 'Match', 'Selection', 'Odds', 'Stake_NOK']]
        print(pending_df.to_string(index=False))
    
    print("\n" + "=" * 60)
    print("VERIFICATION CHECKLIST (run this after every settlement):")
    print("1. Does Liquid = Equity - Pending? (Yes if script ran cleanly)")
    print("2. Cross-check against your actual Norsk Tipping balance.")
    print("3. If discrepancy > 5-10 NOK: Investigate specific bet Notes or payout variance.")
    print("4. Update current_bankroll.md with these figures + verification note.")
    print("5. Run deep dive on any new settled bets per protocol.")
    print("=" * 60)
    
    return {
        'bankroll_equity': bankroll_equity,
        'pending_at_risk': pending_at_risk,
        'liquid_available': liquid_available,
        'realized_pl': realized_pl
    }

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "bet_log.csv"
    analyze_bet_log(csv_file)
