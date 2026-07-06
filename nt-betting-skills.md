# NT Betting Skills (Updated 2026-07-06 - Mandatory Edges Update + Stronger Enforcement)

**IMPORTANT: This version strengthens the requirement to always update sport_edges_and_filters.md when patterns are found.**

## Core Principle (Updated 2026-07-06)

**Research Depth Rule (STRICT)**: Minimum 8-12 sources per shortlisted bet (12-15+ for high-variance). Shallow research is a protocol violation.

**Mandatory Edges Update Rule (NEW - 2026-07-06)**:
- During every post-settlement review, if clear patterns or variance sources are identified, **updating sport_edges_and_filters.md additively is mandatory**, not optional.
- The post-settlement-learning-reviewer must either make the additive update or explicitly document why no update was needed.
- This fixes the previous issue where edges were only updated when "forced".

## nt-betting-workflow

- Enforces Research Depth Rule strictly.
- Over/Under in KO heavily deprioritized.
- All recommendations must meet minimum source requirements.

## post-settlement-learning-reviewer (Updated 2026-07-06 - Stronger)

**Mandatory Steps**:
1. Perform real tool searches on why bets won/lost.
2. Identify clear patterns and variance sources.
3. Record structured learning in the round file.
4. **If meaningful patterns exist**: Make an additive update to sport_edges_and_filters.md (this is now mandatory).
5. Update nt-learning-reviewer tracker.
6. Verify all file updates (bet_log, bankroll, round file, edges if applicable).

Special attention to recurring weak areas (O2.5 in KO/lower leagues, high-var handicaps, player props in knockout).

## nt-learning-reviewer

Maintains tracker and proposes promotions/demotions based on data.

## How the Skills Work Together (Updated 2026-07-06)

**Settlement Flow (Mandatory Order)**:
1. Analyze results + tool proof.
2. Identify patterns/variance.
3. Record in round file.
4. **Update sport_edges_and_filters.md additively** (mandatory if patterns found).
5. Update bet_log.csv (no notes).
6. Update current_bankroll.md.
7. Final summary only after all updates verified.

**Odds File Analysis Flow**:
1. Stage 1 rough scan + filtering.
2. Stage 2 deep research (minimum source requirements enforced).
3. Multi-perspective simulation.
4. betting-value-calculator + staking.
5. **bet_log.csv and current_bankroll.md updates only at the very end** (after all research and decisions).

**Over/Under Caution**: O2.5 in KO/high-variance profiles heavily deprioritized. Default to DNB/BTTS No/primary star props.