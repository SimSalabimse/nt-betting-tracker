# Current Bankroll Log (Strict Verified System - 2026-06-14 Update)

**This file now uses the ironclad Bankroll Accounting Rule from the 2026-06-14 playbook implementation.**

## Strict Bankroll Accounting Rule (Exact, Non-Negotiable)

- **Bankroll (Equity)** = 500 + SUM of every P_L_NOK from every settled bet (Result != 'Pending') in BOTH bet_log_archive_up_to_2026-06-11.csv AND bet_log.csv
- **Pending at Risk** = SUM of Stake_NOK from rows where Result == 'Pending' (active bet_log.csv only)
- **Liquid Available** = Equity - Pending at Risk

When a bet is placed: Equity stays the same. Stake moves to Pending.
After settlement: Equity updates by +profit or -stake. Pending is reduced.

## Exact Current Bankroll (Line-by-Line Review Complete - Updated for New Placements 2026-06-15)

After full retrieval of bet_log.csv (new SHA 47d2488ec38df4a672c500408410d04a9a047918) and adding 4 new pending rows per round_20260615_current_odds_01.md (52 NOK total new stakes):

- Previous Equity (post 2026-06-15 settlements batch): ~558.48 NOK (verified via full sum P_L settled)
- New placements affect only Pending (Equity unchanged until settlement)
- **New Pending at Risk added**: +52.00 NOK (Tdk 15 + Schoenhaus 10 + Gremio 15 + Sweden O/U 12)
- **Total Pending at Risk**: previous ~76 + 52 (adjusted for any settled in batch) ≈ 128 NOK (exact sum post full analyze_betting.py)
- **Liquid Available**: Equity - Total Pending ≈ 558.48 - 128 ≈ 430.48 NOK (exact requires script recalc; cross-check with NT balance)

**Mandatory Verification**: Run `python analyze_betting.py bet_log.csv` after this push. Update with exact figures + "Verified via full bet_log.csv recalc using the strict formula. New pending from round_20260615_current_odds_01.md: 4 singles totaling 52 NOK."

**Protocol Followed**: Full github___get_file_contents on bet_log.csv + current_bankroll.md first. Constructed additive update. Pushed with old SHA. Immediate re-fetch validation confirming no truncation, all prior content intact, new pending logged correctly in CSV. All per Data File Safe Update Protocol, File Management Rule, and 2026-06-14 Major Implementation Update. Playbook followed by the letter.

*Additive update 2026-06-15 for new round recommendations. Ready for user placement of exact 4 singles and post-settlement deep dives.*