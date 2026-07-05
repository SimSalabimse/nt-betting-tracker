# Robust Betting Agent Protocol v2 (Updated 2026-07-05 - STRICT Research Depth Enforcement)

**IMPORTANT: This file was re-pushed on 2026-07-05 with stronger, clearer rules after user confirmed previous updates were not visible/strong enough.**

**2026-07-01 MAJOR CLEANUP & RELIABILITY FIXES**

**Critical New Rules (Non-Negotiable)**:

1. **GitHub Update Reliability (Successful Push Workflow Mandatory)**: Every change must follow: tree verify → get content + exact SHA → full clean update with sha → post re-verify tree + full re-read.

2. **Bankroll Correctness**: Use full archive + live method. No auto-reset of baseline.

3. **Skills First**: Follow nt-betting-skills.md by the letter.

4. **FULL CONTENT RULE**: Always fetch full current content + SHA before any update. Never use placeholders.

**Notes Column DEPRECATED (2026-07-03)**: Removed from bet_log.csv. Learning now goes to round files only.

**Post-Settlement Learning Requirements**: Must trigger post-settlement-learning-reviewer + nt-learning-reviewer, do real tool searches, record in round file, and **update sport_edges_and_filters.md additively** when patterns appear.

**Analyze Correctly Going Forward (Standing Rule)**: Strong filtering + targeted deep research. Balanced volume (4-8 bets typical). Proper tool proof required.

**Research Depth Rule (STRICT - 2026-07-05)**:

**This is now a hard requirement. Shallow research is a violation of this protocol.**

The system previously did insufficient research (often only 2-5 sources). When tested without constraints, 80-130 sources were used. This caused poor bet selection (especially repeated O2.5 failures).

**Mandatory Minimums**:
- Every shortlisted bet: **Minimum 8-12 distinct high-quality sources/tool calls**.
- High-variance bets (O2.5, player props in KO, ET lines, lower league totals, handicaps): **Minimum 12-15 sources**.
- Required sources: FBref/Transfermarkt/Understat xG, FotMob lineups + weather, official motivation, H2H trends, recent form, set pieces, per-line targeted searches.
- No bet may be recommended on shallow or single-source data.
- When in doubt: do MORE research, never less.

**Over/Under Goals Caution Rule (STRICT - 2026-07-05)**:

Recent O2.5 performance has been poor across multiple rounds (WC KO + Norwegian/K League lower leagues).

**New Binding Rules**:
- O2.5 in knockout/high-stakes games is **heavily deprioritized**.
- Only allowed with **very strong multi-source evidence** (projected xG >2.8 + confirmed attacking intent from both teams + no weather/heat issues).
- Default in KO games: DNB, BTTS No, or primary star props.
- Any O2.5 recommendation in KO must explicitly explain why it is different from the recent failing pattern.

**Norwegian 1. Div / K League / Lower Leagues O2.5**: Require explicit motivation + attacking intent confirmation. Prefer DNB/home ML on favorites. Ultra-small stake or avoid on defensive bottom-table clashes.

**Long-Term Staking Plan**: See `long_term_staking_plan.md`.

**Purpose**: Master protocol for all betting work. All future recommendations and settlements must follow this by the letter.

**Implementation Status (2026-07-05)**:
- Research Depth Rule added and strengthened.
- Over/Under Caution Rule added and made binding.
- Both rules now non-negotiable.
- All future analysis must comply. Shallow research will be flagged as a protocol violation.