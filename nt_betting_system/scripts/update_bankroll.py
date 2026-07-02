#!/usr/bin/env python3
"""
Update bankroll after settlements.
This script calculates new equity based on P/L from settled bets.
"""
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "bets.db")

def get_current_equity():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT equity_nok FROM bankroll_history ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    last_equity = row[0] if row else 500.0
    
    cursor.execute("SELECT COALESCE(SUM(stake_nok), 0) FROM bets WHERE result = 'Pending'")
    pending = cursor.fetchone()[0]
    
    conn.close()
    return last_equity, pending

def update_bankroll_after_settlement(note=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COALESCE(SUM(p_l_nok), 0) FROM bets WHERE result IN ('Win', 'Loss')")
    total_pl = cursor.fetchone()[0]
    
    new_equity = 500.0 + total_pl
    
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
    print("Bankroll update script - meant to be called by Grok")