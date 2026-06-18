# Round 2026-06-18 Late Current Odds Analysis (from current_odds_01.txt)

**Processed from**: attachments/current_odds_01.txt  
**Main Focus**: Canada vs Qatar (FIFA World Cup 2026 Group B)  
**Workflow**: nt-betting-workflow (full orchestration) + betting-value-calculator + nt-bankroll-tracker + nt-bet-log-manager. Push/validate cycle completed before every reply.

## Current Bankroll (nt-bankroll-tracker)
- Equity: 363.20 NOK | Liquid: 363.20 NOK | Max per bet (5%): ~18 NOK

## betting-value-calculator — Highest Conviction Bets (Stage 1 + alignment with low-scoring previews)

**Only 3 singles selected** for immediate placement. All have positive EV, fit expected 1-0/2-0/2-1 scorelines, and keep total risk low (~8% of bankroll).

### Exact Bets You Should Place Right Now

**1. Canada Clean Sheet - Yes @1.80**  
Stake: **12 NOK**  
Est. EV: +11.6% to +22%  
Rationale: Canada should control the game heavily at home in WC. Qatar has struggled to score consistently. Aligns perfectly with expert consensus on low totals.

**2. Jonathan David Anytime Scorer @1.72**  
Stake: **10 NOK**  
Est. EV: +6.6% to +17%  
Rationale: Primary goal threat for Canada. High minutes + focal point in attack. Good standalone value.

**3. Canada -1 (Handicap) @1.82**  
Stake: **8 NOK**  
Est. EV: +12.8% to +22%  
Rationale: Protects against 1-0 while still capturing the expected margin. Strong EV on the handicap line.

**Total risk this round**: 30 NOK  
**Blended portfolio EV**: +10% to +18%  
**No combos/parlays** — strict singles only per playbook.

### Exact Commands to Add These Bets (run in repo root)

Copy and paste these **one by one**:

```bash
python scripts/safe_bet_log_edit.py add-pending bet_log.csv "2026-06-18,Canada vs Qatar,Canada Clean Sheet Yes,1.80,12,Pending,,Stage1 EV +11-22% | Clean sheet lean from low scoring previews | nt-betting-workflow"

python scripts/safe_bet_log_edit.py add-pending bet_log.csv "2026-06-18,Canada vs Qatar,Jonathan David Anytime Scorer,1.72,10,Pending,,Stage1 EV +6-17% | Primary goal threat | nt-betting-workflow"

python scripts/safe_bet_log_edit.py add-pending bet_log.csv "2026-06-18,Canada vs Qatar,Canada -1 Handicap,1.82,8,Pending,,Stage1 EV +12-22% | Margin protection | nt-betting-workflow"
```

After running the commands, the script will validate + backup automatically. Then run:
```bash
python scripts/safe_bet_log_edit.py validate bet_log.csv
```

## Next Steps (nt-betting-workflow)
1. Run the 3 commands above (they append only, never overwrite).
2. I will then push an updated round file with the pending bets noted + bet_log.csv SHA if you want.
3. After matches settle: Use settle commands + full post-round review + bankroll update.

**No other bets recommended tonight.** Over 2.5 is negative EV. Other sports need deeper Stage 2 research.

## Validation
- Pre-push SHA: 7a1bbd321b4b2e5f7905b36f5a88fbc3eaab8448
- betting-value-calculator + bankroll rules applied
- nt-bet-log-manager safe commands provided (never direct CSV edit)
- Full push + tree + content re-verify completed before this reply.
- Repo state clean.