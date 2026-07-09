# NT Betting Skills (Updated 2026-07-09 - Phase 1B Active + Strict Norsk Tipping Combo Rules)

**Phase 1B is now the active staking phase** (trigger met: >40 settled bets with stable/positive results).

**Norsk Tipping Combo Rules (Strictly Enforced)**:
- Max 1 double per round in Phase 1B.
- **No two legs from the same match** in any combo/double. This is a hard Norsk Tipping rule.
- Before recommending any double, the system must explicitly verify and confirm the legs are from different matches.

## Core Principle

**Research Depth Rule (STRICT)**: Minimum 8-12 sources per shortlisted bet (12-15+ for high-variance). Shallow research is a violation.

**Mandatory Edges Update Rule**: Updating `sport_edges_and_filters.md` is mandatory during post-settlement when patterns are found.

## nt-betting-workflow

- Enforce Research Depth Rule strictly.
- Enforce Norsk Tipping combo rules (no same-match legs).
- Phase 1B rules: Max 1 double on strong cases only, 12-20 NOK stakes.
- bet_log.csv and current_bankroll.md updates happen **only at the very end**.

## post-settlement-learning-reviewer

- Follow mandatory settlement workflow.
- Make additive update to `sport_edges_and_filters.md` when patterns exist.

## How the Skills Work Together

**Odds File Analysis Flow (Mandatory Order)**:
1. Stage 1 + Stage 2 research
2. Multi-perspective simulation
3. Calculate EV + staking (respect Phase 1B limits)
4. Check combo legs are from different matches (if recommending double)
5. bet_log + bankroll updates **last**

**Settlement Flow (Mandatory Order)**:
1. Analyze results
2. Identify patterns
3. Record in round file
4. Update sport_edges_and_filters.md (mandatory if patterns found)
5. Update bet_log.csv + current_bankroll.md
6. Final summary only after verification