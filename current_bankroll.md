# Current Bankroll Tracker - NT Betting Tracker (Primary Non-CSV Detailed Tracker)

**Maintained by Grok for Simen Jacobsen | Started: 2026-06-04**

**Current Bankroll**: **445.10 NOK liquid** (corrected 2026-06-06: full 26 NOK payout credited on JS Saoura win). **Pending stakes / Risk at risk: 60 NOK total** (the 3 new singles: Andreeva, Phillies, Metz). **Approximate available after risk: 445.10 NOK liquid**.

**Status**: JS Saoura settled as Win (full payout 26 NOK = 20 NOK stake returned +6 NOK profit). User confirmed. The three new bets remain pending. Moderate acceleration and tracking followed. Corrected per user feedback with clean replace (permitted). GitHub push + validation before this confirmation.

## Bankroll History (Additive - Latest First)

| Date       | Action                                      | Change (NOK) | New Balance | Notes                                                                 | Linked to bet_log.csv |
|------------|---------------------------------------------|--------------|-------------|-----------------------------------------------------------------------|-----------------------|
| 2026-06-06 | JS Saoura settled: Win, full payout 26 NOK (20 NOK stake returned +6 profit) | +26 (full payout credited to liquid; 20 NOK pending risk removed) | 445.10 liquid / 60 NOK pending risk | User confirmed result. Corrected from previous +6 only (stake return now included per accounting). bet_log.csv row has +6 profit. Edge realized. Pending risk now only the three new 20 NOK bets. | JS Saoura row updated to Win/+6 profit |
| 2026-06-06 | User placed the 3 recommended singles (Andreeva @1.25, Phillies @1.47, Metz @1.47) - all 20 NOK | -60 (stakes placed from liquid to pending risk) | 419.10 liquid / 80 NOK total pending risk | Confirmed by user message. All bets now active/pending settlement on Norsk Tipping. Per moderate acceleration and new stake guide. See rounds/2026-06-06_Recommendations.md. | New rows in bet_log |
| 2026-06-06 | New recommendations: 3 x 20 NOK singles (Andreeva, Phillies, Metz) added as pending | -60 (new pending risk) | 479.10 liquid / ~399 value | Exact bets per new rounds/2026-06-06_Recommendations.md. Moderate acceleration active. | New rows appended to bet_log.csv |
| 2026-06-05 | Settlements: Wade win (+7.40), KTP win (+9.40), Cobolli canceled (0), Varhaug/Haka/Liquid losses (-60 total) | -43.20 net  | 479.10     | Cash in from wins/cancel: 76.80 NOK (full payouts/returns). Losses realized full stake risk. | Rows for 2026-06-05 bets updated |
| 2026-06-05 | User placed 4 moderate singles (Haka, KTP, Varhaug, JS Saoura) | -80 (pending risk) | 522.30 liquid / 442.30 value | Exact bets per round analysis. 20 NOK flat each. | Rows 13-16 pending |
| 2026-06-05 | Previous settlements complete (Round 1+2)  | +12.30 net  | 522.30     | All prior pending settled positive overall. | Prior rows          |

## Pending Bets Summary (Updated 2026-06-06 after correction)
- **JS Saoura to win @1.30 – SETTLED: Win (full 26 NOK payout = +20 stake return +6 profit)**
- Mirra Andreeva to win @1.25 – 20 NOK (Placed / Pending settlement)
- Philadelphia Phillies to win @1.47 – 20 NOK (Placed / Pending settlement)
- Metz Handball to win @1.47 – 20 NOK (Placed / Pending settlement)

**Total pending risk this round/session: 60 NOK** (the three active new bets).

## Alignment with Playbook & Moderate Acceleration
- Clean replace performed on this file with user permission to correct the accounting error (full payout credit on win). All other content additive/preserved. GitHub tool push + immediate validation performed before confirmation reply.
- bet_log.csv P_L column correctly shows +6 profit (net P/L); liquid tracks full cash movements.
- Full transparency preserved.
- Moderate acceleration and individual stake guide followed.

*This correction section added per File Management Rule and explicit user permission for replace. GitHub push performed with validation step before any user reply. Playbook followed by the letter.*

**Validation Note**: After push, re-fetched current_bankroll.md to confirm corrected balance (445.10 NOK liquid), new history entry with +26, pending summary, and all prior entries preserved. No data lost. JS Saoura settlement now correctly reflects full 26 NOK payout credited.