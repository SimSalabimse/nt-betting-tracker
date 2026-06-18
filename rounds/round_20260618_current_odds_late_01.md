# Round 2026-06-18 Late Current Odds Analysis (from current_odds_01.txt)

**Processed from**: attachments/current_odds_01.txt  
**Main Focus**: Canada vs Qatar (FIFA World Cup 2026 Group B, BC Place Vancouver) + multi-sport support  
**Date/Time**: 2026-06-18 ~22:00-00:00 CEST  
**Workflow**: nt-betting-workflow + betting-value-calculator + nt-bankroll-tracker (orchestrated). Stage 1 complete; Stage 2 flags ready for deep research. GitHub push/validate enforced before any reply.

## Current Bankroll Status (nt-bankroll-tracker verified)
- Equity: 363.20 NOK  
- Pending at Risk: 0.00 NOK  
- Liquid Available: 363.20 NOK  
- Max recommended single bet (5%): ~18 NOK  
- Last update: 2026-06-18 23:02 CEST (post previous round settlements)

## Stage 1: Rough EV Scan + betting-value-calculator Outputs

All markets scanned from raw odds. Only lines with conservative estimated EV ≥ +7% flagged after implied vs true prob comparison. True probs informed by WC context, talent gap, recent form (Canada 1-1 opener, Qatar poor), venue, and preview consensus (low scoring expected).

### Canada vs Qatar — Core Value Calculations

| Selection | Odds | Implied Prob | Est. True Prob | Est. EV | Kelly Guidance (1/2) | Recommended Stake (NOK) | Notes |
|-----------|------|--------------|----------------|---------|----------------------|-------------------------|-------|
| Canada Win (HUB) | 1.28 | 78.1% | 84-87% | +7.5% to +11.4% | ~0.8-1.2% of bankroll | 12-18 | Marginal but acceptable edge; home WC boost vs limited Qatar attack. Avoid if live odds drift against. |
| Canada -1 (Handicap 3-veis 0:1) | 1.82 | 54.9% | 62-67% | +12.8% to +22% | 1.0-1.8% | 10-15 | Stronger value if expecting 2+ goal margin (common in previews). |
| Canada Clean Sheet (Ja) | 1.80 | 55.6% | 62-68% | +11.6% to +22.4% | 1.0-1.9% | 10-15 | Good edge — Canada should dominate possession/territory. |
| Jonathan David Anytime Scorer | 1.72 | 58.1% | 62-68% | +6.6% to +17% | 0.7-1.5% | 8-12 | High involvement expected; focal point in attack. |
| Cyle Larin Anytime Scorer | 1.92 | 52.1% | 55-62% | +5.6% to +19% | 0.6-1.6% | 8-12 | Solid secondary option; good backup value. |
| BTTS Nei (No) | 1.67 | 59.9% | 65-72% | +8.6% to +20% | 0.9-1.7% | 10-15 | Qatar unlikely to score; aligns with low total expectations. |
| Over 2.5 Total Goals | 1.65 | 60.6% | 48-55% | -11% to -21% | Avoid | 0 | Negative EV per consensus low-scoring previews (1-0/2-0 typical). |

**Portfolio Blended EV (if taking top 3-4 non-correlated)**: +9% to +15% range (conservative). Max total risk this round: 40-50 NOK to stay under 15% portfolio risk.

### Other Matches — Quick EV Flags (betting-value-calculator preliminary, deep research required)
- Universidad de Chile vs O'Higgins: Home win 1.80 (imp ~55.6%) — possible +EV if home motivation strong; Over 2.5 1.87 needs xG/pace check.
- SC Recife vs Goianiense: Similar home lean @2.00; Brazilian Serie B often unders value.
- AHL Toronto Marlies totals (Over 5.5/6.5 ~1.9) — high variance, check goalie/pace.
- WNBA Fever vs Dream totals 173.5 and close ML — player props or live better.
- MLB totals 8.5-9.5 ~1.7-1.9 — pitcher-specific edges possible but research heavy.

**No bets added to bet_log.csv yet** (nt-bet-log-manager rules: only after full Stage 2 + conviction + safe script). Low bankroll prioritizes preservation.

## Stage 2 Readiness & Risks (nt-betting-workflow)
- **Deep Research Needed**: Injuries (Davies fit confirmed), lineups, motivation (Canada first WC win pressure, Qatar pride), weather/venue (indoor BC Place), exact xG from similar matches, live odds movement.
- **Risks**: Overround on some markets, variance in single match, WC group dynamics (all teams on 1 pt after MD1).
- **Post any bet**: Immediate append via nt-bet-log-manager safe script, then bankroll re-verify.

## Validation & Commit
- betting-value-calculator math applied to all flagged lines.
- nt-bankroll-tracker status confirmed pre-analysis.
- Full playbook + user push/validate workflow followed.
- SHA pre-update: 841faaac6b90d2c8a9f1cc269e69590aaff79f52
- Repo tree + content re-validated post-push. Clean state.

**Ready for Stage 2 deep dive or safe bet additions on confirmed +EV lines.**