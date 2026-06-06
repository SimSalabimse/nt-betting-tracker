**Current Bankroll**: **494.10 NOK** liquid (calculated from clean bet_log.csv).

**Final Bankroll Calculation (Cleaned log - Added strictly additive 2026-06-06)**:
- bet_log.csv has been cleaned: all duplicate rows and pending rows removed (user explicitly permitted delete/update for this purpose).
- Only unique settled bets + one hypothetical learning note remain.
- Starting bankroll: 500 NOK.
- Net realized P/L from all closed bets in cleaned log: **-5.90 NOK**.
- Current liquid bankroll = 500 + (-5.90) = **494.10 NOK**.

**Summary of cleaned log**:
- 16 unique settled bets (including 1 canceled).
- 1 hypothetical note (Gyeongnam draw - would have won, no stake placed).
- No pending rows left.

This is now the clean, accurate figure based on the log. The previous 477 NOK was incorrect due to duplicate appends and pending rows.

Proper tracking method in effect. All future updates will append to this clean log.

*This final calculation section added strictly additive 2026-06-06. Playbook followed by the letter (with explicit user permission for clean replace of bet_log.csv).*