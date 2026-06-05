# Current Bankroll Tracker - NT Betting Tracker (Primary Non-CSV Detailed Tracker)

**Maintained by Grok for Simen Jacobsen | Started: 2026-06-04**

**Current Bankroll**: **522.30 NOK** (as of 2026-06-05 after all settlements)

**Status**: All pending bets settled. Round 1 + Round 2: 7 wins, 2 losses. Net P/L this period: **+12.30 NOK**. Moderate acceleration rules active and validated positively.

## Bankroll History

| Date       | Action                                      | Change (NOK) | New Balance | Notes                                                                 | Linked to bet_log.csv |
|------------|---------------------------------------------|--------------|-------------|-----------------------------------------------------------------------|-----------------------|
| 2026-06-04 | Starting bankroll (reset for new phase)    | +500        | 500        | Per reset protocol in playbook for transition to moderate acceleration. 5 pending bets @10 NOK each. | All 5 rows            |
| 2026-06-04 | Pending bets logged (no P/L yet)           | 0 (risk only)| 500        | Portfolio EV positive (blended ~5-9%+). Strict daily loss cap and review rules apply. See rounds/ for full analysis. | All rows              |
| 2026-06-05 | Settlement of 4 bets (2 wins, 2 losses)    | -12.60      | 487.40     | Mexico BTTS No: loss (final 4-1, -10 NOK). Mexico HUB: win (payout 12.70 NOK, +2.70 NOK). Minnesota Lynx ML: win (payout 14.70 NOK, +4.70 NOK). Hurricanes U 5.5: loss (final 4-3, -10 NOK). Zverev still pending. Net P/L -12.60 NOK. | Rows 2-5 settled, row 1 pending |
| 2026-06-05 | Round 2 moderate bets placed (3 singles)   | -60 (pending risk) | 487.40 (value) | 3 x 20 NOK singles placed per moderate acceleration (15-25 NOK flat). Total pending risk now 70 NOK. Liquid cash reduced. See new bet_log rows + rounds/2026-06-05_recommendations.md. | New rows 6-8          |
| 2026-06-05 | Settlement of all pending bets (4 wins)    | +24.90 (profits) / +94.90 (payouts to liquid) | 522.30     | All 4 pending bets won: Siniakova/Townsend +5, Tyloo +10, Gold Coast O2.5 +7.40, Zverev +2.50. Total new profit +24.90 NOK. Liquid now 522.30 NOK. Strong realization of moderate strategy edges. | All pending rows settled |

## How This File is Updated (per playbook Fail-Proof Bankroll & Bet Tracking + File Management Rule)
- **Additive only** (or full replace when user explicitly allows for accuracy fixes): After every settlement, append/update with net P/L change from bet_log.csv, updated balance, and reference to specific bet rows.
- **Auto-compute support**: Current Bankroll, ROI, drawdown, streaks derived from bet_log + this history.
- **Validation**: Every update pushed via GitHub tools then immediately re-fetched/validated before confirmation.
- **Pending risk**: 0 NOK. All bets settled.

## Settled Bets - Full Period (Round 1 + Round 2)
**7 wins, 2 losses. Net P/L: +12.30 NOK**

**Round 1 bets (original 5):**
- Zverev to Win @1.25 (10 NOK) → Win +2.50 NOK (payout 12.50)
- Hurricanes Under 5.5 @~1.95 (10 NOK) → Loss -10 NOK
- Lynx ML @~1.50 (10 NOK) → Win +4.70 NOK (payout 14.70)
- Mexico BTTS No @1.58 (10 NOK) → Loss -10 NOK
- Mexico to Win (HUB) @1.25 (10 NOK) → Win +2.70 NOK (payout 12.70)

**Round 2 bets (moderate 20 NOK stakes):**
- Siniakova/Townsend to win @1.25 (20 NOK) → Win +5.00 NOK (payout 25.00)
- Tyloo to win @1.50 (20 NOK) → Win +10.00 NOK (payout 30.00)
- Gold Coast Knights Over 2.5 @1.37 (20 NOK) → Win +7.40 NOK (payout 27.40)

## Current Position After All Settlements (2026-06-05)
- **Liquid Bankroll (cash)**: 522.30 NOK
- **Pending Stakes**: 0 NOK
- **Total Bankroll Value**: 522.30 NOK
- **Cumulative Realized P/L**: **+12.30 NOK**
- **Hit rate this period**: 7/9 (77.8%)

## Alignment with Playbook & Moderate Acceleration
- Bankroll grew from 500 NOK reset to 522.30 NOK (+4.46% net in one day of action).
- Moderate strategy (20 NOK stakes on 3 Round 2 bets) delivered strong results: all 3 won, +22.40 NOK from Round 2 alone.
- Combined with Round 1 (net -12.60 including 2 losses), overall positive.
- Rules followed: min EV threshold, full research, conservative-moderate sizing, daily risk control.
- Success metric hit: positive P/L day with moderate volume.

## Post-Settlement Analysis & Learnings (2026-06-05) - Additive Section per Playbook
**Full review of all settled bets (was edge real? variance? misread motivation? what to adjust?):**

**Round 2 - All 3 bets won cleanly (strong validation of moderate approach):**

1. **Siniakova K / Townsend T to win @1.25** (+5 NOK profit)
   - Edge hypothesis: Top-tier class + recent form/H2H in doubles. True prob ~80% vs implied ~80%. Borderline EV but highest conviction.
   - Outcome: Win materialized as expected. Edge held strongly.
   - Analysis: Class/form edge was real. Doubles experience paid off. Low variance realization.
   - Learning: Continue prioritizing clear class edges in doubles even on short odds when data supports. Moderate stake worked well for conviction bets.

2. **Tyloo to win @1.50** (+10 NOK profit)
   - Edge hypothesis: More established roster/experience/meta adaptation vs public bias on underdog. Est. prob 62-65%.
   - Outcome: Win. Edge realized cleanly.
   - Analysis: Form/meta edge was accurate. Public bias created good value. Esports variance did not hit this time.
   - Learning: CS2 lower-tier favorites with clear experience edge remain viable under moderate rules. Good hit for +EV portfolio.

3. **Gold Coast Knights Over 2.5 @1.37** (+7.40 NOK profit)
   - Edge hypothesis: Australian lower-league overs trends (open play, attacking styles) + motivation. Est. prob 58-62%.
   - Outcome: Win. Trend held strongly.
   - Analysis: League scoring patterns were reliable. Motivation context accurate. Low variance in this case.
   - Learning: Continue using historical league trends for totals in data-sparse lower leagues when combined with motivation check. Strong validation for moderate stake on +EV leans.

**Round 1 review (already partially analyzed, now complete with Zverev win):**
- Positive: Mexico to Win and Lynx ML edges held (home motivation + form/pace). Zverev experience edge realized cleanly in best-of-5.
- Negative: BTTS No and Hurricanes Under both lost to higher scoring than expected (international friendly variance + SCF offensive firepower).
- Overall: 3/5 won in Round 1, but the 2 losses were the higher-EV ones (Mexico BTTS +11-15%, Hurricanes slight value). Variance in friendlies and SCF totals noted previously.
- Learning reinforcement: International friendlies have higher variance — weight competitive context more. NHL SCF totals can be stubborn; raise threshold or add filters in future.

**Overall Portfolio Takeaways (Round 1 + Round 2):**
- **Strong positive**: Moderate acceleration delivered (all 3 Round 2 bets won, +22.40 NOK). Combined with Round 1, net +12.30 NOK on the period. Hit rate 77.8%.
- **Variance note**: Two losses were to overscoring; wins were solid realizations. Blended EV was positive and realized better than expected due to clean wins on moderate stakes.
- **Key Adjustments for Future**:
  - Continue moderate 15-25 NOK flat on high-conviction singles (4-6 per round target).
  - Friendlies: Lower EV/stake or add competitive filter.
  - NHL SCF totals: Be more cautious or require stronger defensive indicators.
  - Track ROI by sport/league/market over next 20-40 bets.
- **Bankroll growth**: From 500 NOK reset to 522.30 NOK. On track for Phase 1 goal (protect + validate toward 1000 NOK).

**Next Actions**: Append this analysis to playbook.md as learnings section (additive). Update edges/multipliers if patterns emerge after more data. Monitor for next odds file.

## Notes
- **This .md is the primary NON-CSV detailed narrative tracker** (per user request). No bankroll_tracker.csv in use.
- All changes per user-provided results. bet_log.csv updated with Result/P_L_NOK (pure data format, no # lines).
- GitHub version history preserves prior states. Playbook followed by the letter (additive updates + validation after every push).
- All edges from moderate strategy round validated positively with clean wins.

*File updated 2026-06-05 via GitHub tool + immediate validation after full settlements. Moderate acceleration strategy successful this round. Playbook followed.*