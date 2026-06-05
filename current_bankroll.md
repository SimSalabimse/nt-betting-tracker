# Current Bankroll Tracker - NT Betting Tracker (Primary Non-CSV Detailed Tracker)

**Maintained by Grok for Simen Jacobsen | Started: 2026-06-04**

**Current Bankroll**: **487.40 NOK** (as of 2026-06-05 after settlement)

**Status**: 4 bets settled this round. 1 bet (Zverev) still pending. Realized P/L this round: -12.60 NOK. Moderate acceleration rules active.

## Bankroll History

| Date       | Action                                      | Change (NOK) | New Balance | Notes                                                                 | Linked to bet_log.csv |
|------------|---------------------------------------------|--------------|-------------|-----------------------------------------------------------------------|-----------------------|
| 2026-06-04 | Starting bankroll (reset for new phase)    | +500        | 500        | Per reset protocol in playbook for transition to moderate acceleration. 5 pending bets @10 NOK each. | All 5 rows            |
| 2026-06-04 | Pending bets logged (no P/L yet)           | 0 (risk only)| 500        | Portfolio EV positive (blended ~5-9%+). Strict daily loss cap and review rules apply. See rounds/ for full analysis. | All rows              |
| 2026-06-05 | Settlement of 4 bets (2 wins, 2 losses)    | -12.60      | 487.40     | Mexico BTTS No: loss (final 4-1, -10 NOK). Mexico HUB: win (payout 12.70 NOK, +2.70 NOK). Minnesota Lynx ML: win (payout 14.70 NOK, +4.70 NOK). Hurricanes U 5.5: loss (final 4-3, -10 NOK). Zverev still pending. Net P/L -12.60 NOK. | Rows 2-5 settled, row 1 pending |

## How This File is Updated (per playbook Fail-Proof Bankroll & Bet Tracking + File Management Rule)
- **Additive only** (or full replace when user explicitly allows for accuracy fixes): After every settlement, append/update with net P/L change from bet_log.csv, updated balance, and reference to specific bet rows.
- **Auto-compute support**: Current Bankroll, ROI, drawdown, streaks derived from bet_log + this history.
- **Validation**: Every update pushed via GitHub tools then immediately re-fetched/validated before confirmation.
- **Pending risk**: 10 NOK at risk (Zverev only) - within conservative Phase 1 targets.

## Settled Bets This Round (with Results & P/L)
**4 bets settled. 2 wins, 2 losses. Net P/L: -12.60 NOK**

**1. Mensik vs Zverev (RG SF, clay)** - *Still Pending*
- Selection: Zverev to Win
- Odds: 1.25
- Est. Prob: 83-86% (0.845)
- Est. EV: +4% to +7.5%
- Key Reasoning (Full Playbook Research): Zverev experience + clay H2H win + Mensik fatigue in best-of-5 after tough run. Consistent form. Form/H2H/motivation (RG SF)/stats/surface all checked - no shortcuts.

**2. Hurricanes vs Golden Knights (NHL SCF G2)** - *Settled: Loss (final score 4-3)*
- Selection: Under 5.5 Total Goals
- Odds: ~1.95
- Est. Prob: 52-55% (0.535)
- Est. EV: +2% to +7%
- P/L: -10 NOK
- Key Reasoning (Full Playbook Research): Game 1 high scoring; Game 2 expects defensive tightening & adjustments. Public bias to Over. Form/trends/motivation/stats/H2H checked.

**3. Minnesota Lynx vs Golden State Valkyries (WNBA)** - *Settled: Win (payout 14.70 NOK)*
- Selection: Lynx Moneyline
- Odds: ~1.50 (confirm live)
- Est. Prob: ~68% (0.68)
- Est. EV: ~+4%
- P/L: +4.70 NOK
- Key Reasoning (Full Playbook Research): Lynx superior recent form, better defense/pace vs Valkyries. Matchup edge. Form/H2H/motivation/stats checked.

**4. Mexico vs Serbia (Intl Friendly)** - *Settled: Loss (final score 4-1)*
- Selection: BTTS - No
- Odds: 1.58
- Est. Prob: 70-73% (0.715)
- Est. EV: +11% to +15% (example +13%)
- P/L: -10 NOK
- Key Reasoning (Full Playbook Research): Mexico strong home form (5W 2D last 7, clean sheets), WC 2026 motivation + home crowd. Serbia poor recent results (L5 of last 8), limited attack. Controlled/low-scoring expected. Form/H2H/motivation/stats checked. High value.

**5. Mexico vs Serbia (Intl Friendly)** - *Settled: Win (payout 12.70 NOK)*
- Selection: Mexico to Win (HUB)
- Odds: 1.25
- Est. Prob: 84-88% (0.86)
- Est. EV: +5% to +10%
- P/L: +2.70 NOK
- Key Reasoning (Full Playbook Research): Same context: Home advantage + form + high motivation vs Serbia struggles. Solid value on the short. Form/H2H/motivation/stats checked.

## Current Position After Settlement
- **Liquid Bankroll (cash)**: 477.40 NOK
- **Pending Stakes (Zverev only)**: 10 NOK
- **Total Bankroll Value**: 487.40 NOK
- **Cumulative Realized P/L**: -12.60 NOK

## Alignment with Playbook & Moderate Acceleration
- Bankroll: Started 500 NOK. Phase 1: Protect & Validate until ~1000 NOK + positive ROI data over 20-40 bets.
- Future: Scale to 15-25 NOK flat per high-conviction bet, allow 4-6 bets/round on good +EV opportunities. Daily risk target ~60-100 NOK.
- Strict rules: Daily/weekly review, reset protocol on significant drawdown, full transparency in logs.

## Notes
- **This .md is the primary NON-CSV detailed narrative tracker** (per user request). No bankroll_tracker.csv in use.
- All changes per user-provided correct info and settlement results. bet_log.csv updated with Result/P_L_NOK (pure data format, no # lines per playbook rule).
- GitHub version history preserves prior states. Playbook followed.
- Next: Monitor Zverev result. Post full settlement updates will append realized P/L and adjust balance.

*File updated 2026-06-05 via GitHub tool + validation. Playbook followed by the letter.*