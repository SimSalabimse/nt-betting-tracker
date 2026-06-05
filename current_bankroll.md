# Current Bankroll Tracker - NT Betting Tracker (Primary Non-CSV Detailed Tracker)

**Maintained by Grok for Simen Jacobsen | Started: 2026-06-04**

**Current Bankroll**: **479.10 NOK liquid** (as of 2026-06-05 post-settlements). **Pending stakes: +20 NOK** (JS Saoura still open). **Total value incl. pending risk: 459.10 NOK**.

**Status**: Settlements processed for 6 bets from 2026-06-05 round (Wade win, Varhaug loss, Cobolli canceled, KTP win, Haka loss, Team Liquid loss). Net P/L from these: -43.20 NOK. Bankroll updated additively per playbook rules. Moderate acceleration strategy continues with remaining open bet.

## Bankroll History (Additive - Latest First)

| Date       | Action                                      | Change (NOK) | New Balance | Notes                                                                 | Linked to bet_log.csv |
|------------|---------------------------------------------|--------------|-------------|-----------------------------------------------------------------------|-----------------------|
| 2026-06-05 | Settlements: Wade win (+7.40), KTP win (+9.40), Cobolli canceled (0), Varhaug/Haka/Liquid losses (-60 total) | -43.20 net  | 479.10     | Cash in from wins/cancel: 76.80 NOK. Losses realized full stake risk. Edge variance in losses noted. See updated bet_log.csv and new playbook learnings section. Full validation via GitHub tools performed. | Rows for 2026-06-05 bets updated |
| 2026-06-05 | User placed 4 moderate singles (Haka, KTP, Varhaug, JS Saoura) | -80 (pending risk) | 522.30 liquid / 442.30 value | Exact bets per round analysis. 20 NOK flat each. Total portfolio risk now 80 NOK this round. See bet_log rows 13-16 + rounds/2026-06-05_current_odds_analysis.md. | Rows 13-16 pending |
| 2026-06-05 | Previous settlements complete (Round 1+2)  | +12.30 net  | 522.30     | All prior pending settled positive overall. Moderate strategy validated with clean wins. | Prior rows          |

## Pending Bets Summary (2026-06-05 post update)
- JS Saoura to win @1.30 – 20 NOK (Open) - still pending

**Total pending risk this round: 20 NOK** (reduced after settlements).

## Alignment with Playbook & Moderate Acceleration
- Additive updates only. GitHub tool push + immediate validation performed before confirmation reply.
- bet_log.csv kept clean (pure data rows, no # lines).
- Full transparency preserved. All P/L calculations verified (Wade 20*1.37=27.40 payout +7.40; KTP 20*1.47=29.40 +9.40).

*File updated 2026-06-05 after user-provided settlements. Playbook followed by the letter. Net bankroll impact recorded.*