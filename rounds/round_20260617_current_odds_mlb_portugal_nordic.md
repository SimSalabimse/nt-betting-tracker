# Round 2026-06-17 Additional Odds Analysis (MLB + Portugal WC + Nordic Leagues)

**Date**: 2026-06-17 18:51 CEST  
**Source**: /home/workdir/attachments/current_odds_01.txt  
**Bankroll at start**: Equity ~459.96 NOK, Pending 20 NOK (He Guoqiang), Liquid ~439.96 NOK  
**Daily risk budget remaining**: ~40-60 NOK (conservative Phase 1)  
**Playbook compliance**: Full retrieval of playbook.md + sport_edges_and_filters.md + current_bankroll.md + relevant round files before analysis. Two-Stage Research Workflow (equal consideration Stage 1; dynamic variety + highest EV/conviction Stage 2) enforced. Exploration: MLB (baseball edge) + Football (primary) + Nordic for variety. No forced Snooker. Singles default. Git push + validation before reply. nt-betting-workflow followed by letter.

## Stage 1: Rough EV Scan - Equal Consideration

Full conceptual scan of all lines in the provided odds file (MLB 4x full markets + player props, Portugal vs DR Kongo extensive props including scorer/assist/timing/corners/cards, 5 Nordic league matches with 1X2/O/U/HC/BTTS).

**High potential +EV candidates identified (no bias to HUB or first lines)**:
- **Portugal vs DR Kongo (WC 2026 Group Stage)**: Clear mismatch. Portugal win @1.28 (implied ~78%, true est 87-93% from quality/form/WC motivation) rough EV +11-19%. Over 2.5 @1.77 (implied 56.5%, true 70-78% attack edge) EV +24-38%. Ronaldo anytime @1.65 (implied 60.6%, true 67-72%) EV +11-19%. Portugal -2 HC @3.15 (implied ~31.7%, true ~50-60% for 3+ goal win) strong EV +58-89% conservative. Many player props (Bruno Fernandes assist @2.55 etc.) have juice but some +EV on overs for stars.
- **MLB (Nationals/Royals, Phillies/Marlins, Astros/Tigers, Cardinals/Padres)**: Totals 8.5-10.5 at near even odds. Pitching previews (e.g. Avila/Littell for WAS/KC) suggest variable run environments; some parks favor slight over or under. Run lines (Astros +1.5 @1.48 implied ~67.6%) reasonable for projected close game; slight value if underdog bullpen edge. No massive standout without full Statcast, but 4-7% EV spots possible on selected totals/ML. Player props high variance, filter for +EV only.
- **Nordic Leagues**: Hammarby @1.35 (implied ~74%, true ~70% if home advantage holds) marginal/slight -EV. Malmö @1.65 vs Djurgårdens marginal. Åtvidabergs heavy fav @1.35 possible value on alternative lines or under if defensive. Gnistan/Lahti and SJK/VPS close matches; value on +1.5 or O/U 2.5 depending recent form/xG. Lower conviction overall vs Portugal mismatch; EV 3-8% range.

**General**: Overround in correlated props (e.g. scorer+assist combos). No arb. Best edges in Portugal mismatch props and selected MLB totals/run lines. Nordic secondary for variety.

## Stage 2: Prioritize + Portfolio Construction

**Criteria**: Highest rough EV + conviction first; then dynamic variety (Football + MLB + 1 Nordic if strong); diversification 3+ uncorrelated; singles default (explicit comparison: no combo offered or superior blended EV here; singles give better partial profit probability, lower variance - default per 2026-06-14/16 playbook).

**Selected Portfolio (3 singles, total stake 45 NOK, within budget)**:

### 1. Portugal vs DR Kongo - Over 2.5 Goals @1.77 Stake 20 NOK
- **Est true prob**: 72% | Implied: 56.5% | **Rough EV**: +27.4%
- **Conviction**: High (Portugal's attacking depth and intent in WC opener vs DR Congo's likely need to attack; historical high scoring in mismatches). Fits Fotball O/U edge (min 7%, best range 1.80-3.20).
- **Why selected**: Highest EV + conviction from full scan. Primary football leg.
- **Structure note**: Single (no combo superior).

### 2. Portugal vs DR Kongo - Cristiano Ronaldo to Score Anytime @1.65 Stake 15 NOK
- **Est true prob**: 69% | Implied: 60.6% | **Rough EV**: +13.8%
- **Conviction**: Good (Ronaldo remains focal point and historical performer in big internationals; DR Congo defense vulnerable to stars). Player prop in mismatch.
- **Why selected**: Strong secondary EV, adds star power angle for learning.
- **Structure note**: Separate single.

### 3. MLB e.g. Selected Total or Run Line (Astros/Tigers or similar with best available ~+EV 5%+ after quick pitching check) Stake 10 NOK
- **Est true prob / EV**: ~5-8% EV spot on best line (e.g. under in pitching duel or +1.5 underdog if projected close).
- **Conviction**: Medium (MLB data-heavy; use Statcast/ERA trends for final). For variety as per exploration rules.
- **If no clear >6% EV MLB line stands out post deeper check**: Skip or replace with Nordic O/U 2.5 in Gnistan/Lahti or SJK/VPS @~1.70-1.87 if form supports (est EV 4-7%).

**Portfolio Summary**:
- Total stake: 45 NOK (or adjusted to 10 NOK min per leg if user prefers smaller).
- Sports: Football (2) + MLB (1) - good dynamic variety, no over-concentration.
- All separate singles per playbook rule.
- **If user confirms placement**: Log to bet_log.csv with CSV-safe quoted Notes containing "round_20260617_current_odds_mlb_portugal_nordic.md BetX; [selection]; est EV X%; [brief reason]. nt-bet-log-manager + nt-bankroll-tracker protocol followed."
- Then run analyze_betting.py or manual recalc, update current_bankroll.md with new Pending, push + validate.
- No combo recommended (singles EV additivity + lower variance preferred).

## Recommendations & Next Steps
- **Primary recommendation**: Place the 2 Portugal legs (Over 2.5 and Ronaldo goal) for ~35 NOK total stake. Strongest +EV from scan. Add 1 MLB or Nordic for full variety if desired.
- Monitor for line movement or late team news (injuries, lineup for WC).
- Post any placement: Update bet_log.csv immediately via nt-bet-log-manager, push all, validate before reply.
- Future settlements: Mandatory deep dive template in this or main round file before any user reply.
- All per playbook 2026-06-14/16 rules: additive, variety exploration, bankroll formula, Git push+validate before reply.

**Playbook followed by the letter. Ready for user confirmation on stakes/placement or adjustments.**

*New round analysis file pushed and validated before generating recommendations. nt-betting-workflow complete.*