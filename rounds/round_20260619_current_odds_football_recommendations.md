# Round 2026-06-19 Current Odds - Football Recommendations (Hinna-Brodd, Ranheim-Lyn, others)

**Processed**: 2026-06-19 17:50 CEST (updated 17:52 with Exploration section + 3rd bet; fixed min stake 17:53)  
**Source**: Attached current_odds_01.txt (full scan of football sections + cross check with tennis/darts/esports already processed earlier today)
**Status**: Full nt-betting-workflow executed autonomously by Grok per 2026-06-19 playbook role update. Stage 1 full scan of all markets in provided odds. Stage 2 deep research on flagged (web_search for form, standings, H2H, previews). **3 new bets decided** (2 core + 1 small exploratory on new odds type). All stakes now respect the 10 NOK minimum rule. All GitHub updates pushed + validated before this record.

## Matches Overview & Stage 1 EV Scan Highlights

**Core Filters Applied** (from playbook + sport_edges_and_filters.md):
- Rough EV threshold: >6-8% edge after conservative buffer for variance/sport
- Prioritize: Norwegian domestic (familiar leagues, good data), clear form/H2H edges, value on main lines or props with cushion
- Avoid: Unknown leagues (Kuwait etc without deep data), heavy fav ML without HC value, overround heavy markets
- Bankroll: Max ~5% equity per bet (~20 NOK), total new pending <10% equity. Diversify from previous tennis/darts/esports.

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
| 3 | Ranheim vs Lyn | Scorer begge lag i 1. omgang Ja | 3.15 | 10 | +8-15% | **Exploratory on new odds type** (half-time BTTS). Expected open, high-tempo game. True prob both score in 1H ~39-44% >> 31.7% implied. Small stake (now at minimum 10 NOK rule) to test new market per playbook exploration rule. Uncorrelated to main Over 2.5. |

**Total New Stake / Risk**: 32 NOK  
**New Pending Total**: 32 NOK (~8.1% of 396.10 equity) — well within strict discipline (<10-12% total pending).  
**Blended Portfolio EV**: Positive ~9-15% across legs. Low correlation (win + goals + half BTTS).  
**Risk Management**: All stakes respect the 10 NOK minimum rule. Small flat stakes, strict EV filter post deep research, no parlays. Includes 1 small exploratory on new odds type to follow "Exploration & Balance" rule.

## Exploration of New Odds Types & Sports (per Playbook - Added on Feedback)

You are correct — the playbook explicitly requires trying new odds types/new sports when edge supports it, and avoiding over-weighting usual ones.

**Actions taken in this round**:
- Full Stage 1 scan included **all** sections: advanced football props (time of 1st goal, both teams score in half, player scorers, HT/FT, correct score, etc.), athletics H2H (110m hurdles, high jump Barshim/Doroshchuk, steeplechase, triple jump, javelin, 1500m/400m women, etc.), and the Kuwait match.
- **Athletics H2H**: New sport for the tracker. Quick research on close lines (e.g. Barshim 2.20 vs Doroshchuk 1.55 — Barshim legend but recent form down; US hurdlers Britt/Tinch very competitive). High single-event variance + limited specific 2026 event news meant most did not clear strict EV >7-8% after buffer. No addition today, but noted for future major champs where data improves.
- **New football props**: Several flagged. The half-time BTTS Ja @3.15 in Ranheim-Lyn cleared filters (open game expected) and is added as small exploratory #3 (stake corrected to minimum 10 NOK). Other props (full time BTTS, time of goal, player anytime) were close but kept out to control total pending risk.
- **Kuwait match**: Skipped — insufficient reliable recent form/H2H/xG data for deep research.

This directly addresses the exploration rule while keeping risk disciplined and respecting the 10 NOK minimum stake rule. Future rounds will continue allocating small exploratory stakes to athletics H2H and exotic props when they pass Stage 2.

## Workflow Compliance & Next Steps (Executed by nt-betting-workflow)

1. This recommendations file **updated** (stake fix to 10 NOK min + totals) and pushed.
2. bet_log.csv: The 3rd Pending row stake corrected to 10 NOK (full fetch + SHA verified, targeted update on the exact row, append-only discipline maintained).
3. current_bankroll.md: Updated with new pending risk 32 NOK, liquid recalculated, note added.
4. All changes pushed via GitHub tools + re-validated (tree re-check + full content re-fetch) before reply.
5. Post-settlement deep dives + additive learning to this file and sport_edges_and_filters.md.

**Ready-to-Place Summary for User (Norsk Tipping platform)**:

Place these **3 new bets** now:

1. **Hinna vs Brodd** — Brodd to win @ **2.15** for **10 NOK**
2. **Ranheim vs Lyn** — Over 2.5 goals @ **1.35** for **12 NOK**
3. **Ranheim vs Lyn** — Both teams to score in 1st half (Ja) @ **3.15** for **10 NOK** (exploratory new odds type, minimum stake applied)

Report back settlements/results for processing via nt-bet-log-manager. All per strict playbook discipline. Repo single source of truth. Grok autonomous decisions complete.

This maintains full compliance with nt-betting-workflow, playbook 2026-06-19 update, Exploration & Balance rule, 10 NOK minimum stake rule, and successful push workflow.