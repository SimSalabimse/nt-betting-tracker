# NT Betting Skills (Updated 2026-07-05 - STRICT Research Depth Enforcement)

**IMPORTANT: This file was re-pushed on 2026-07-05 with stronger rules after user feedback that previous updates were not visible enough.**

## Core Principle (Updated 2026-07-05)

**Research Depth Rule (STRICT - Non-Negotiable)**:
The system previously did too little research (often only 2-5 sources). This caused repeated poor decisions, especially on O2.5 bets.

**Mandatory Minimum Research Standards**:
- Every shortlisted bet requires **minimum 8-12 distinct high-quality tool calls/sources**.
- High-variance bets (O2.5, player props in KO, ET lines, lower league totals): **minimum 12-15 sources**.
- Must include: FBref/Transfermarkt/Understat, FotMob lineups + weather, motivation reports, H2H, recent form, set pieces, and per-line targeted searches.
- Shallow research is now a violation of this protocol. No exceptions.

## nt-betting-workflow (Main Orchestrator Skill)

- Must enforce the Research Depth Rule strictly.
- No bet may be recommended without meeting the minimum source requirements above.
- Over/Under in knockout games is heavily deprioritized unless exceptional multi-source evidence exists.

## nt-bet-log-manager

Handles bet_log.csv safely. No Notes column. Learning goes to round files.

## post-settlement-learning-reviewer (Updated 2026-07-05)

- Must perform real tool searches on losses.
- Pay special attention to recurring weak areas (O2.5 variance).
- Record learning in round file.
- Update sport_edges_and_filters.md additively when patterns appear.

## How the Skills Work Together

All steps must follow the new Research Depth Rule and Over/Under Caution Rule.

**Over/Under Caution**: O2.5 in KO/high-variance profiles is heavily deprioritized. Default to DNB, BTTS No, or primary star props instead.