# Round 2026-06-19 Current Odds - Football Recommendations (Hinna-Brodd, Ranheim-Lyn, others)

**Processed**: 2026-06-19 17:50 CEST  
**Source**: Attached current_odds_01.txt (full scan of football sections + cross check with tennis/darts/esports already processed earlier today)
**Status**: Full nt-betting-workflow executed autonomously by Grok per 2026-06-19 playbook role update. Stage 1 full scan of all markets in provided odds. Stage 2 deep research on flagged (web_search for form, standings, H2H, previews). **2 new bets decided** for placement. Conservative sizing given current equity ~396 NOK. All GitHub updates pushed + validated before this record.

## Matches Overview & Stage 1 EV Scan Highlights

**Core Filters Applied** (from playbook + sport_edges_and_filters.md):
- Rough EV threshold: >6-8% edge after conservative buffer for variance/sport
- Prioritize: Norwegian domestic (familiar leagues, good data), clear form/H2H edges, value on main lines or props with cushion
- Avoid: Unknown leagues (Kuwait etc without deep data), heavy fav ML without HC value, overround heavy markets
- Bankroll: Max ~5% equity per bet (~20 NOK), total new pending <10% equity. Diversify from previous tennis/esports.

**Flagged from Full Scan**:

**Hinna vs Brodd (3. divisjon Group 4, 19 Jun 17:00)**
- Odds: Hinna 2.40 | Draw 4.20 | Brodd 2.15
- Brodd better form (3W-0D-2L last 5), Hinna poor (0-1-4), Brodd dominates H2H (5 wins in 6 meetings). Hinna 13th, Brodd 10th. True prob Brodd win est 52-56% >> 46.5% implied → solid +EV on Brodd ML.

**Ranheim vs Lyn (OBOS-ligaen, 19 Jun ~17:00)**
- Odds: Ranheim 1.62 | Draw 4.50 | Lyn 4.10 ; Over 2.5 1.35 | Under 2.80
- Ranheim 6th good home, Lyn 13-14th poor form/leaky (21 goals con in 11). H2H Lyn edge but current form favors home. Models ~50-56% home win (fair/slight -EV on 1.62). Over 2.5 value if xG ~3.0+ (high scoring potential) true prob ~78-82% >>74% implied.

Other: Al-Fahaheel/Kazma skipped (limited reliable form data for deep research). Athletics H2H many close, require more specific event context (African Champs?); props risky without player news. Tennis/darts/esports already covered in earlier round file today.

## Exact Bets Decided by Grok (Autonomous - Ready to Place)

**User instruction followed**: "nt-betting-workflow skill You decide the bets to be placed."

| Bet # | Match | Selection | Decimal Odds | Stake (NOK) | Est. EV Range | Rationale / Notes |
|-------|-------|-----------|--------------|---------------|---------------|-------------------|
| 1 | Hinna vs Brodd | Brodd to win | 2.15 | 10 | +12-18% | Stronger form, H2H dominance (Brodd 5W-1L vs Hinna), Hinna struggling bottom side. Clear value on away win vs short price on home. Norwegian 3. div familiarity. |
| 2 | Ranheim vs Lyn | Over 2.5 goals | 1.35 | 12 | +6-12% | Ranheim potent attack at home + Lyn poor defensive record (high xG likely). Over line offers cushion vs main ML which is marginal. Good diversification (goals market uncorrelated to win bets). |

**Total New Stake / Risk**: 22 NOK  
**New Pending Total**: 22 NOK (~5.6% of 396.10 equity) — well within strict discipline (<10-12% total pending).  
**Blended Portfolio EV**: Positive ~9-15% across legs. Low correlation (different bet types: win + goals).  
**Risk Management**: Small flat stakes, strict EV filter post deep research, no parlays. Focus on high-conviction Norwegian football edges.

## Workflow Compliance & Next Steps (Executed by nt-betting-workflow)

1. This recommendations file created/pushed to rounds/round_20260619_current_odds_football_recommendations.md
2. bet_log.csv: 2 new Pending rows appended at bottom (full fetch + SHA verified first, append-only with proper CSV, Notes with round ref + rationale, no historical changes).
3. current_bankroll.md: Updated with new pending risk 22 NOK, liquid recalculated, full verification note referencing this file + nt-betting-workflow + nt-bankroll-tracker execution.
4. All changes pushed via GitHub tools (create_or_update_file) + re-validated (tree re-check + full content re-fetch of updated files) before any user reply.
5. Post-settlement: Will add deep dive + learning notes to this file and sport_edges_and_filters.md (additive) after results reported.

**Ready-to-Place Summary for User (Norsk Tipping platform)**:

Place these **2 new bets** now:

1. **Hinna vs Brodd** — Brodd to win @ **2.15** for **10 NOK**
2. **Ranheim vs Lyn** — Over 2.5 goals @ **1.35** for **12 NOK**

Report back settlements/results for processing via nt-bet-log-manager. All per strict playbook discipline. Repo single source of truth. Grok autonomous decisions complete.

This maintains full compliance with nt-betting-workflow, playbook 2026-06-19 update, and successful push workflow.