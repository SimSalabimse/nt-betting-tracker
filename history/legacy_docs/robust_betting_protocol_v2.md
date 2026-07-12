# Robust Betting Agent Protocol v2 (Updated 2026-07-10 - Better Combo Logic + Consistent Volume)

**IMPORTANT: Phase 1B is now the active staking phase** (trigger met: >40 settled bets).

**Norsk Tipping Combo Rules (Strictly Enforced)**:
- Maximum 1 double per round in Phase 1B.
- No two legs from the same match in any combo.
- **When to recommend a combo**: Only when there are **two solid, uncorrelated bets** (from different matches/events) where:
  - Both legs have clear positive EV on their own.
  - The combined EV of the double is meaningfully better than taking them as singles.
  - Multi-perspective simulation supports both legs.
  - The combo fits diversification rules.
- Do **not** force a combo if no strong pair exists. Prefer quality singles instead.

**Analyze Correctly Going Forward (Standing Rule)**:
- Strong filtering + targeted deep research on the shortlist.
- **Target volume in Phase 1B**: Aim for **3–6 quality bets** per mixed file.
- Overly conservative outputs (1 bet or forcing weak combos) are not acceptable.
- Never output placeholder or garbage data in tables.

**Research Depth Rule (STRICT)**:
- Minimum 8-12 sources per shortlisted bet.

**Step-by-Step Workflows**:
**For Odds File Analysis (Mandatory Order)**:
1. Stage 1 rough scan + filtering
2. Stage 2 deep research
3. Multi-perspective simulation
4. betting-value-calculator + staking
5. Check for strong combo opportunities (different matches only)
6. bet_log.csv + current_bankroll.md updates **only at the very end**

**For Settlements (Mandatory Order)**:
1. Analyze results
2. Identify patterns
3. Record in round file
4. **Mandatory** update to sport_edges_and_filters.md if patterns found
5. Update bet_log.csv + current_bankroll.md
6. Final summary only after verification

**Long-Term Staking Plan**: See `long_term_staking_plan.md`.

**Purpose**: Master protocol. The system must deliver balanced, high-quality recommendations with clean output every time.