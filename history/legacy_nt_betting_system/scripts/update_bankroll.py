#!/usr/bin/env python3
"""
Update bankroll after settlements.
This script calculates new equity based on P/L from settled bets.

BASELINE LOCK RULE (2026-07-03 per user request):
- LOCKED_BASELINE is fixed at clean restart value.
- NEVER auto-reset or re-anchor equity to 500 (or baseline) without explicit user instruction.
- Only adjust baseline if user says e.g. "reset baseline to X" or "adjust baseline for deposit/withdrawal/profit lock-in".
- See current_bankroll.md for full NO AUTO-RESET RULE and locked status.
"""
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "bets.db")

# LOCKED BASELINE - DO NOT CHANGE unless user EXPLICITLY requests baseline adjustment
LOCKED_BASELINE = 500.0  # 2026-06-28 Full Clean Restart - Locked In per user NO AUTO-RESET rule

def get_current_equity():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT equity_nok FROM bankroll_history ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    last_equity = row[0] if row else LOCKED_BASELINE
    
    cursor.execute("SELECT COALESCE(SUM(stake_nok), 0) FROM bets WHERE result = 'Pending'")
    pending = cursor.fetchone()[0]
    
    conn.close()
    return last_equity, pending

def update_bankroll_after_settlement(note=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COALESCE(SUM(p_l_nok), 0) FROM bets WHERE result IN ('Win', 'Loss')")
    total_pl = cursor.fetchone()[0]
    
    new_equity = LOCKED_BASELINE + total_pl
    
    cursor.execute("SELECT COALESCE(SUM(stake_nok), 0) FROM bets WHERE result = 'Pending'")
    pending_at_risk = cursor.fetchone()[0]
    
    cursor.execute('''
        INSERT INTO bankroll_history (date, equity_nok, pending_at_risk, note)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().date().isoformat(), new_equity, pending_at_risk, note))
    
    conn.commit()
    conn.close()
    
    return new_equity, pending_at_risk

if __name__ == "__main__":
    print("Bankroll update script - meant to be called by Grok. Baseline locked per user NO AUTO-RESET rule.")