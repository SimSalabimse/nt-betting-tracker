# Sport Edges, Multipliers, Filters & ROI Tracking

**Dedicated file for per-sport parameters (important but infrequently updated).**
**Updated only after sufficient data (typically 8-15+ bets or clear repeated patterns from deep dives).**
**playbook.md and nt-learning-reviewer skill reference this for decisions.**
**All changes additive or with clear version notes. Full history in Git.**

**NEW 2026-07-05 RESEARCH DEPTH & O2.5 CAUTION UPDATE (Triggered by user feedback on shallow research + repeated O2.5 failures in latest 3 rounds)**:

**Critical Problem Identified**:
- Multiple previous responses performed only shallow research (often 2-5 sources on 2-3 matches).
- When tested in a fresh unconstrained chat, 80-130 sources were used.
- This led to over-reliance on weak signals and poor bet selection (especially Over 2.5 Goals).
- Recent O2.5 bets in WC R32/R16 and Norwegian lower leagues have shown high failure rate due to defensive realizations, game state shifts (reds/subs), weather/heat, and low motivation in bottom-table clashes.

**Mandatory Research Depth Rule (Non-Negotiable)**:
- Every shortlisted bet now requires **minimum 8-12 distinct high-quality tool calls/sources** before recommendation.
- For high-variance bets (O2.5, player props in KO, ET lines, lower league totals): **minimum 12-15 sources**.
- Required sources include: FBref/Transfermarkt/Understat xG, FotMob lineups + weather, official motivation reports, H2H trends, recent form streaks, set-piece data, and per-line targeted searches.
- No bet may be recommended on shallow or single-source confirmation. Depth > Speed.

**Over/Under Goals - Strong Caution (Especially KO Games)**:
- O2.5 in World Cup knockout stages (R32/R16+) has shown repeated poor performance across multiple rounds.
- Primary variance sources: Early goals/game state shifts, defensive blocks by underdogs, heat/extreme conditions, low motivation near elimination, red cards/subs altering flow.
- **New Rule**: O2.5 in KO games is now heavily deprioritized. Only consider when there is **very strong multi-source evidence** (projected xG >2.8 + both teams confirmed attacking intent + no major weather/heat factor + historical trends strongly support).
- Default preference in knockout games: DNB, BTTS No (vs low creation), primary star scorer props, or conservative team lines.
- Any O2.5 recommendation in KO must explicitly justify why it differs from the recent failing pattern.

**Norwegian 1. Division / Lower Leagues O2.5**:
- Recent Raufoss O2.5 loss (despite strong stats lean) confirmed high variance from defensive caution in bottom-table clashes and unmodeled factors.
- **New Filter**: O2.5 in 1. Div requires explicit confirmation of both teams' recent high scoring intent + motivation delta. Avoid or use ultra-small stake on defensive bottom-table clashes. Prefer DNB or home ML for favorites as more robust var buffer.

**Additive Updates to Existing Sections**:
- WC / International Knockout: Reinforced DNB + BTTS No + primary star props as priority. O2.5 / aggressive HC deprioritized unless exceptional multi-source confirmation.
- Norwegian Lower Leagues: O2.5 tightened sharply per recent variance. DNB/ML on home favorites reinforced.
- Player Props in KO: Require finishing xG share + starter confirmation + pair with team line or ultra-small stake.

**nt-learning-reviewer Tracker Update (2026-07-05)**:
- O2.5 in KO / high-variance profiles: + multiple L across recent rounds → tightened sharply.
- Research quality flag: Previous responses showed insufficient depth → new mandatory minimum source rule enforced.
- DNB priority in high-var profiles: Reinforced as robust var buffer (multiple validated W).

All changes are additive. Full tool proof and multi-agent simulation applied. Master Protocol + new Research Depth Rule followed. System self-sustaining.