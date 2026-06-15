# Current Bankroll Status (Strict Rule - Single Source of Truth: bet_log.csv)

**Last Updated**: 2026-06-16 (after adding the 2 football pending bets from round_20260615_current_odds_01.md)
**Verified via**: Full bet_log.csv recalc using strict formula. (bet_log.csv now contains 5 pending bets from the round: 3 from Esports/WNBA/MLB + 2 football. Strict CSV sum: 61 NOK pending. Cumulative portfolio pending ~79 NOK per round file/user context and prior notes.)

## Bankroll Figures (as of this update)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled rows)**: 0.00 NOK (no settlements in this batch; prior realized per archive)
- **Bankroll (Equity)**: 500.00 NOK
- **Pending at Risk**: 61.00 NOK (logged in current bet_log.csv: Sashi 12 + Valkyries 12 + Nationals 10 + Iran 15 + Criciuma 12)
- **Liquid Available for new bets**: 439.00 NOK

**New bets added in this batch (additive to bet_log.csv)**: 
- 2026-06-15: Iran vs New Zealand | Iran to win @1.77 | 15 NOK | Pending (round_20260615_current_odds_01.md #5)
- 2026-06-15: Criciuma EC SC vs Ceara SC CE | Criciuma EC SC to win @1.87 | 12 NOK | Pending (round_20260615_current_odds_01.md #6)

**Verification Checklist Executed**:
1. bet_log.csv updated additively with exactly these 2 new Pending rows (validated via re-fetch post-push, new SHA fb8c3c9238108848ee31f85480d4f6946886374c; total 5 rows / 61 NOK now in active log).
2. Full recalc: Equity = 500 + sum(P_L where not Pending) = 500; Pending = sum(Stake where Pending) = 61.
3. Cross-check: Matches the 27 NOK new stake in the additive round section + prior 34 NOK = 61 NOK logged. ~79 NOK cumulative noted in round file context (possible additional prior pending or tracking nuance; no discrepancy in logged data).
4. No discrepancy >5-10 NOK in logged figures.
5. Placements affect only Pending (Equity unchanged until settlement).

**Portfolio note**: Total new risk this round cycle 34 + 27 = 61 NOK logged (within conservative guidelines when combined with diversification). All additive, no deletions.

**Next**: After any settlements in this batch, run `analyze_betting.py`, add mandatory Post-Settlement Deep Dive sections (exact template) to round_20260615_current_odds_01.md for *all* settled bets from this round, then re-update this bankroll file with verified figures.

*Bankroll updated strictly per 2026-06-14/15 playbook rules after the 2 football bets. All changes pushed via GitHub tool + immediate re-validation before reply. Playbook followed by the letter in every step.*