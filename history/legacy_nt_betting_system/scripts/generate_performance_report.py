#!/usr/bin/env python3
"""
Generate easy-to-read performance statistics.
This will be run after settlements to keep stats up to date.
"""
import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "bets.db")
REPORT_PATH = os.path.join(BASE_DIR, "performance_report.md")

def generate_report():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    report = []
    report.append("# NT Betting Performance Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Overall stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_bets,
            SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) as losses,
            COALESCE(SUM(p_l_nok), 0) as total_pl,
            COALESCE(AVG(CASE WHEN result IN ('Win','Loss') THEN decimal_odds END), 0) as avg_odds
        FROM bets 
        WHERE result IN ('Win', 'Loss')
    """)
    row = cursor.fetchone()
    total, wins, losses, total_pl, avg_odds = row

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    roi = (total_pl / 500 * 100) if total_pl else 0

    report.append("## Overall Performance")
    report.append(f"- Total Settled Bets: {total}")
    report.append(f"- Wins: {wins} | Losses: {losses}")
    report.append(f"- Win Rate: {win_rate:.1f}%")
    report.append(f"- Total P/L: {total_pl:.2f} NOK")
    report.append(f"- Average Odds: {avg_odds:.2f}")
    report.append(f"- Approx. ROI: {roi:.1f}%\n")

    # By Sport
    report.append("## Performance by Sport")
    cursor.execute("""
        SELECT sport, 
               COUNT(*) as bets,
               SUM(CASE WHEN result='Win' THEN 1 ELSE 0 END) as wins,
               COALESCE(SUM(p_l_nok),0) as pl
        FROM bets 
        WHERE result IN ('Win','Loss') AND sport IS NOT NULL
        GROUP BY sport
        ORDER BY pl DESC
    """)
    for sport, bets, wins, pl in cursor.fetchall():
        wr = (wins / bets * 100) if bets > 0 else 0
        report.append(f"- **{sport}**: {bets} bets | {wins}W | P/L: {pl:.2f} NOK | Win Rate: {wr:.1f}%")

    report.append("\n## Recent Activity (Last 30 days)")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(p_l_nok),0)
        FROM bets 
        WHERE result IN ('Win','Loss') AND date >= ?
    """, (thirty_days_ago,))
    recent_bets, recent_pl = cursor.fetchone()
    report.append(f"- Bets settled in last 30 days: {recent_bets}")
    report.append(f"- P/L last 30 days: {recent_pl:.2f} NOK\n")

    conn.close()

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(report))

    print(f"Performance report updated: {REPORT_PATH}")

if __name__ == "__main__":
    generate_report()