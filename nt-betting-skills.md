# NT Betting Skills (Updated 2026-07-10 - Improved Combo Logic)

**Phase 1B is now the active staking phase**.

**Norsk Tipping Combo Rules**:
- Max 1 double per round.
- No same-match legs.
- Only recommend a combo when there are **two solid uncorrelated bets** with clear positive EV on both legs and the double adds meaningful value.

## Core Principle

**Research Depth Rule (STRICT)**: 8-12+ sources per bet.

**nt-betting-workflow**:
- Enforce Research Depth Rule.
- Look for combo opportunities after finding strong singles (only if quality pair exists).
- Phase 1B target: 3-6 quality bets.
- bet_log + bankroll updates **only at the very end**.
- Never output broken or placeholder tables.

**post-settlement-learning-reviewer**:
- Mandatory edges update when patterns found.

**Odds File Analysis Flow**:
1. Stage 1 + Stage 2 deep research
2. Multi-perspective simulation
3. Calculate EV + staking
4. Check for strong combo (different matches + both legs solid)
5. bet_log + bankroll updates last

**Settlement Flow**:
1. Analyze results
2. Record patterns in round file
3. Update sport_edges_and_filters.md (mandatory)
4. Update bet_log + bankroll
5. Final summary after verification