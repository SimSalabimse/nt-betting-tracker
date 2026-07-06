# Robust Betting Agent Protocol v2 (Updated 2026-07-06 - Full Enforcement + Mandatory Edges Update + Step-by-Step Workflows)

**IMPORTANT: This file was updated on 2026-07-06 to include the Mandatory Edges Update Rule and explicit step-by-step workflows.**

**2026-07-01 MAJOR CLEANUP & RELIABILITY FIXES**

**Critical New Rules (Non-Negotiable)**:

1. **GitHub Update Reliability (Successful Push Workflow Mandatory)**
2. **Bankroll Correctness** (full archive + live method, no auto-reset)
3. **Skills First** — Follow nt-betting-skills.md by the letter
4. **FULL CONTENT RULE** — Always fetch full current content + SHA before updating

**Notes Column DEPRECATED (2026-07-03)**: Removed from bet_log.csv. All learning goes to round files.

**Post-Settlement Learning Requirements (Updated 2026-07-06)**:
- Must trigger full post-settlement-learning-reviewer + nt-learning-reviewer.
- Perform real tool searches on why bets won or lost.
- Identify clear patterns and variance sources.
- Record learning in the round file.
- **Mandatory**: If meaningful patterns exist, make an **additive update to sport_edges_and_filters.md** (this is no longer optional).
- Update bet_log.csv (no notes) and current_bankroll.md.
- Verify all updates before giving any summary.

**Analyze Correctly Going Forward (Standing Rule)**: Strong filtering + targeted deep research. Balanced volume. Proper tool proof required.

**Research Depth Rule (STRICT - 2026-07-05)**:
- Minimum 8-12 sources per shortlisted bet.
- High-variance bets (O2.5, KO props, lower league totals, handicaps): Minimum 12-15 sources.
- Shallow research is a violation of this protocol.

**Over/Under Goals Caution Rule (STRICT - 2026-07-05)**:
- O2.5 in knockout/high-stakes games is heavily deprioritized.
- Only allowed with very strong multi-source evidence.
- Default in KO games: DNB, BTTS No, or primary star props.

**Mandatory Edges Update Rule (NEW - 2026-07-06)**:
Updating sport_edges_and_filters.md additively is now **mandatory** during post-settlement when patterns are identified. The post-settlement-learning-reviewer must either perform the update or explicitly document why it was not needed.

**Step-by-Step Workflows (NEW - 2026-07-06)**:

**For Odds File Analysis (Mandatory Order)**:
1. Stage 1 rough scan + filtering
2. Stage 2 deep research (enforce minimum sources)
3. Multi-perspective simulation
4. betting-value-calculator + staking
5. bet_log.csv + current_bankroll.md updates **only at the very end**

**For Settlements (Mandatory Order)**:
1. Analyze results with tool proof
2. Identify patterns + variance sources
3. Record in round file
4. **Mandatory** additive update to sport_edges_and_filters.md (if patterns found)
5. Update bet_log.csv (no notes)
6. Update current_bankroll.md
7. Final summary only after all updates verified

**Long-Term Staking Plan**: See `long_term_staking_plan.md`.

**Purpose**: Master protocol. All future work must follow this by the letter. Shallow research and skipping edges updates are now protocol violations.