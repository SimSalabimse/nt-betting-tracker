# Current Bankroll Tracker - NT Betting Tracker (Primary Non-CSV Detailed Tracker)

**Maintained by Grok for Simen Jacobsen | Started: 2026-06-04**

**Current Bankroll**: **500 NOK** (as of 2026-06-04)

**Status**: Transition round complete under moderate acceleration rules. All 5 tracked bets pending settlement (no realized P/L yet). 50 NOK total at risk (5 x 10 NOK Singles). Correct info applied per user table.

## Bankroll History

| Date       | Action                                      | Change (NOK) | New Balance | Notes                                                                 | Linked to bet_log.csv |
|------------|---------------------------------------------|--------------|-------------|-----------------------------------------------------------------------|-----------------------|
| 2026-06-04 | Starting bankroll (reset for new phase)    | +500        | 500        | Per reset protocol in playbook for transition to moderate acceleration. 5 pending bets @10 NOK each. | All 5 rows            |
| 2026-06-04 | Pending bets logged (no P/L yet)           | 0 (risk only)| 500        | Portfolio EV positive (blended ~5-9%+). Strict daily loss cap and review rules apply. See rounds/ for full analysis. | All rows              |

## How This File is Updated (per playbook Fail-Proof Bankroll & Bet Tracking + File Management Rule)
- **Additive only** (or full replace when user explicitly allows for accuracy fixes): After every settlement, append/update with net P/L change from bet_log.csv, updated balance, and reference to specific bet rows.
- **Auto-compute support**: Current Bankroll, ROI, drawdown, streaks derived from bet_log + this history.
- **Validation**: Every update pushed via GitHub tools then immediately re-fetched/validated before confirmation.
- **Pending risk**: 50 NOK at risk (~10% of bankroll) - within conservative Phase 1 targets.

## Pending Bets Risk Summary (Correct Info - 5 Singles @10 NOK Each)
**All 5 pending, Singles, 10 NOK stake each. Total at risk 50 NOK. Liquid after stakes: 450 NOK. Total value 500 NOK.**

**1. Mensik vs Zverev (RG SF, clay)**
- Selection: Zverev to Win
- Odds: 1.25
- Est. Prob: 83-86% (0.845)
- Est. EV: +4% to +7.5%
- Key Reasoning (Full Playbook Research): Zverev experience + clay H2H win + Mensik fatigue in best-of-5 after tough run. Consistent form. Form/H2H/motivation (RG SF)/stats/surface all checked - no shortcuts.

**2. Hurricanes vs Golden Knights (NHL SCF G2)**
- Selection: Under 5.5 Total Goals
- Odds: ~1.95
- Est. Prob: 52-55% (0.535)
- Est. EV: +2% to +7%
- Key Reasoning (Full Playbook Research): Game 1 high scoring; Game 2 expects defensive tightening & adjustments. Public bias to Over. Form/trends/motivation/stats/H2H checked.

**3. Minnesota Lynx vs Golden State Valkyries (WNBA)**
- Selection: Lynx Moneyline
- Odds: ~1.50 (confirm live)
- Est. Prob: ~68% (0.68)
- Est. EV: ~+4%
- Key Reasoning (Full Playbook Research): Lynx superior recent form, better defense/pace vs Valkyries. Matchup edge. Form/H2H/motivation/stats checked.

**4. Mexico vs Serbia (Intl Friendly)**
- Selection: BTTS - No
- Odds: 1.58
- Est. Prob: 70-73% (0.715)
- Est. EV: +11% to +15% (example +13%)
- Key Reasoning (Full Playbook Research): Mexico strong home form (5W 2D last 7, clean sheets), WC 2026 motivation + home crowd. Serbia poor recent results (L5 of last 8), limited attack. Controlled/low-scoring expected. Form/H2H/motivation/stats checked. High value.

**5. Mexico vs Serbia (Intl Friendly)**
- Selection: Mexico to Win (HUB)
- Odds: 1.25
- Est. Prob: 84-88% (0.86)
- Est. EV: +5% to +10%
- Key Reasoning (Full Playbook Research): Same context: Home advantage + form + high motivation vs Serbia struggles. Solid value on the short. Form/H2H/motivation/stats checked.

## Alignment with Playbook & Moderate Acceleration
- Bankroll: 500 NOK start. Phase 1: Protect & Validate until ~1000 NOK + positive ROI data over 20-40 bets.
- Future: Scale to 15-25 NOK flat per high-conviction bet, allow 4-6 bets/round on good +EV opportunities. Daily risk target ~60-100 NOK.
- Strict rules: Daily/weekly review, reset protocol on significant drawdown, full transparency in logs.

## Notes
- **This .md is the primary NON-CSV detailed narrative tracker** (per user request). bankroll_tracker.csv is supplementary structured data/CSV log.
- All changes per user-provided correct info (old Liga MX replaced with correct Mexico vs Serbia friendly). bet_log.csv fully replaced with clean correct version (user allowed replace this time for accuracy).
- GitHub version history preserves prior states. Playbook followed with explicit user permission for this fix.
- Next: Post-settlement updates will append realized P/L and adjust balance.

*File updated 2026-06-05 via GitHub tool + validation. Playbook followed by the letter (with user replace permission for this accuracy fix).*