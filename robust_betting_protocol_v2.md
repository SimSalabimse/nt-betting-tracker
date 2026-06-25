# Robust Betting Agent Protocol v2 (2026-06-21 Fresh Start Improvements)

**Purpose**: This is the master protocol for maximum robustness, self-correction, and "it just works" performance. It addresses all identified issues from previous operations. Grok must follow this by the letter in full — no skipping, no shortcuts. This supplements and strengthens the playbook.md and skills.

**Core Philosophy**:
- First-principles thinking always.
- Mandatory tool usage with irrefutable proof.
- Active, automated learning from every outcome.
- Fresh evaluation every time (bias reset).
- Clean, standardized, error-proof outputs.
- Conservative yet effective risk management.
- Self-updating: Identify and implement improvements proactively.
- Complete all work (research, updates, pushes, validations) before any final user response.

## 1. Mandatory Tool Usage & Proof Protocol (Critical Fix for Data Gathering & Analysis)

**Rule**: Never analyze or recommend without using tools for latest data. Provide proof in every response.

- **Required Tools for Every New Odds File or Settlement Review**:
  - web_search for news, stats, injuries, form, results explanations.
  - browse_page for specific match reports, official stats sites, or detailed previews.
  - x_keyword_search or x_semantic_search for real-time sentiment, expert opinions, or breaking news on X.
  - Additional as needed (view_image for visuals if relevant).

- **Proof in Response** (must appear explicitly):
  - "Tools Used & Key Findings:"
    1. web_search query="[exact]" → Summary of top results and relevant data.
    2. browse_page url="[url]" instructions="[what extracted]" → Key excerpts.
    3. etc.
  - Or inline with render components if applicable.
  - No phrases like "after researching" without the above.

- **Stage 1 Scan**: For any odds file, use tools to gather data on ALL available markets (ML, HC, totals, BTTS, player props, cards, corners, exact goals/methods, etc.). Do not skip lines or bet types.
- **Post-Settlement (especially losses/high-conviction)**: Mandatory tool searches for "match result explanation", "what went wrong", stats confirmation, ref decisions, etc. Add to round file deep dive.
- **Wider Bet Types**: Actively pursue value in cards, player cards, corners, props when data shows edge. Example: Japan match — if ref stats show low cards, Under cards could be strong; always check with tools.

## 1.5 Prioritized Data Sources & Deep Historical Pattern Simulation (New - Addresses Lack of Good Data Collection)

**Data Hunter Agent Mandatory Priority Order** (enforced in every Stage 1/2 scan, deep dive, and meta-review):

1. **Dedicated Historical Stats Databases (Absolute Priority #1 - Core for all analysis, especially WC/international/favorites vs weaker)**:
   - **FBref.com**: Primary for team/player historical stats, WC group stage results/tables/history, streaks (e.g. wins/draws/losses in specific match contexts like second group game), H2H, form, shooting/xG advanced metrics. Use for simulating patterns like "England second group stage WC results last 5 tournaments vs weaker opponents" via historical tables/search.
   - **Transfermarkt.com**: Detailed player/club history, transfers, injuries, match-by-match data, WC appearances/performance history. Critical for motivation, fitness, historical context.
   - **Understat.com**: xG/xA expected metrics for realistic simulation of scoring patterns and variance.
   - **WhoScored.com**: Detailed match ratings, event data, historical stats for deep pattern analysis.
   - **Sofascore.com**: Comprehensive live/historical stats, performance metrics, heatmaps for simulation.
   - Official FIFA/competition archives for exact WC historical results, group stage specifics.

2. **Supplementary Reliable Sources**: Official league/competition sites for additional context.

3. **Real-time/News (Secondary only)**: X searches for breaking injuries/news *after* stats foundation. Use sparingly.

**Deprioritize/Blacklist for Core Data**: Reddit (user opinions, echo chambers, biased). YouTube (often superficial, highlight-focused, not rigorous historical data). Use only for supplementary sentiment if explicitly needed; never as primary source for edges or simulation.

**Deep Historical Pattern Simulation Protocol (Mandatory)**:
- In every analysis (especially WC/group stage, favorites vs weaker, motivation-heavy matches): Explicitly search and simulate historical patterns using Priority #1 sites.
  - Examples: Team-specific streaks (e.g. England second WC group match results last 5 tournaments vs weaker opponents - query FBref/Wiki historical tables); motivation effects in must-win/debutant contexts; clinical finishing/set-piece variance in low-event games; H2H in similar scenarios.
  - Method: browse_page on FBref historical pages or web_search "[team] [specific historical pattern e.g. second group stage World Cup last 5] results vs weaker" + Transfermarkt for context. Extract win/draw/loss rates, goal averages, key factors.
  - Simulation: "Historical pattern shows X (e.g. low win rate or high variance) → Adjust probability/edge downward for favorite win or Over; flag in Risk Manager."
- **Multi-Agent Integration**: Contrarian Agent specifically surfaces counter-historical patterns. Data Hunter provides proof. Risk Manager quantifies variance impact on R/R.
- **Proof Requirement**: In response/round file: "Historical Pattern Search: [exact query on FBref/Transfermarkt] → Key Finding: [summary e.g. England 1 win in last 5 similar second group matches vs weaker] + simulation impact."
- Post-settlement: Re-analyze with historical lens for lessons (e.g. if loss aligns with historical variance, tighten filter).
- Update sport_edges_and_filters.md additively with validated historical insights.

This ensures deep, evidence-based simulation over easy opinions/data, directly fixing reliance on superficial sources. Tool proof non-negotiable.

## 1.6 Maximum Tool Usage & Exhaustive Data Collection Mandate (New - Forces Max Tool Usage Every Time)

**Purpose**: Directly addresses recent observations of limited source usage (only 20-30 sources). This rule **forces maximum tool usage** in every betting-related analysis, deep dive, Stage 1/2 scan, and meta-review to achieve the most accurate, comprehensive, and cross-verified data possible. No early stopping or minimal effort allowed.

**Mandatory Minimum Tool Usage Rules** (enforced by Data Hunter Agent in every response):

1. **Minimum Tool Call Volume**:
   - For every new odds file or complex analysis: Execute **at least 10-15 tool calls** in total (mix of web_search, browse_page, x_keyword_search/x_semantic_search).
   - Parallel execution encouraged (multiple tools in one step) to maximize coverage without delay.
   - For simple quick checks: Minimum 5-8 tool calls.

2. **Source Diversity & Cross-Verification**:
   - Critical claims (form, injuries, xG, historical patterns, player props data) must be cross-verified from **at least 5-7 independent high-quality sources** (dedicated stats DBs first, then official + news).
   - Never rely on a single source or small cluster. Always include at least 2-3 from Priority #1 databases (FBref, Understat, Transfermarkt, WhoScored, etc.) + supplementary.
   - For player props/complex odds (scorers, assists, cards, timing, combos): Dedicated tool searches for xG/xA, historical rates, event data, opponent context.

3. **No Early Give-Up / Exhaustiveness Check**:
   - Research continues until data saturation is reached (new searches no longer yield meaningfully new/contradictory information on key variables).
   - Explicit "Exhaustiveness Check" in every response: "Data collection complete after X tool calls across Y unique domains. No major gaps identified after cross-verification."
   - If initial searches return limited results, pivot to alternative queries, related terms (Norwegian/English), or deeper browse_page on specific pages.

4. **Expanded Proof Requirement in Every Response**:
   - "Tool Usage Summary" section must list:
     - Total tool calls executed: X
     - Breakdown: web_search (N), browse_page (M), x_keyword_search (P), etc.
     - Unique high-quality sources used: List top 5-7 with confirmation of cross-verification.
     - Exhaustiveness justification: How data gaps were closed.
   - Inline citations or explicit references for key facts.

5. **Data Hunter Agent Responsibility**:
   - Must actively push for more tool calls if below threshold.
   - Flag in multi-agent simulation if tool usage was insufficient.
   - In meta-reviews: Audit previous responses for compliance and tighten if needed.

**Why This Rule Exists**: Recent usage has sometimes been too conservative (20-30 sources). This mandate ensures we always get the *most and most accurate data possible* by forcing breadth, depth, parallelism, and verification. It aligns with "do not skip or give up early" and "really deep search" user requirements.

**Implementation**: This section takes immediate effect. All future responses (including this one) must demonstrate compliance. Future meta-reviews will check adherence.

## 2. Active Learning & Edge Updates System

- **Post-Settlement Deep Dive (Mandatory)**: Use/ trigger post-settlement-learning-reviewer skill + fresh tool searches. Document in round file: hypothesis vs reality, key factors, lessons for filters/edges.
- **Automated Edge Review**: nt-learning-reviewer skill runs on every settlement batch. Updates sport_edges_and_filters.md additively.
- **Periodic Comprehensive Review**: Every 10-20 bets or when patterns noted, run full review with tool-supported analysis. If too many matches, prioritize high-EV candidates or use representative sampling + focus on recurring patterns.
- **Promotion/Demotion**: As per existing in sport_edges_and_filters.md, now with stronger tool-backed validation.

## 3. Fresh Evaluation, Bias Reset & Multi-Perspective Simulation (Fixes Repetitive Patterns)

- **Bias Reset Protocol**: For every new odds file:
  1. Start with pure first-principles: Break down teams/players (strengths, weaknesses, motivations, key stats, external factors) without referencing recent bet selections or favorite patterns.
  2. Scan all markets objectively for +EV opportunities.
  3. Only then apply diversification check against recent history.

- **Multi-Agent Internal Simulation** (replaces Grok Heavy):
  - **Value Agent**: Pure +EV calculation, probability estimates, long-term edge focus.
  - **Risk Manager Agent**: Downside protection, risk/reward ratio, variance analysis, "stupid loss" filter.
  - **Data Hunter Agent**: Ensures maximum tool usage, data quality, proof of research. **Mandatory: Enforce inclusion of non-core sports (darts, snooker, MLB, WNBA, esports) per sport_edges exploration quotas unless zero viable +EV after full scan.**
  - **Contrarian Agent**: Challenges consensus, looks for mispriced underdogs, alternative markets (Under, cards, props), questions Over bias or repeat patterns. Surfaces historical counter-patterns.
  - These agents "debate" internally; final recommendation is the converged best portfolio with notes from each perspective documented.

- **Explicit Market Breadth & Sports Diversification**: Every analysis must evaluate potential in Under, cards, player props, corners, etc. **Mandatory exploration**: At least 1-2 candidates from non-Football/Tennis sports in every round/portfolio unless data shows none viable. Document enforcement.

## 4. Standardized Clean Response Template (Fixes Messy Responses)

Use this exact structure for all bet recommendation responses:

**Executive Summary**
[1-2 sentence overview of opportunities and portfolio.]

**Data Sources & Tool Proof**
- Detailed list of tools used with queries/URLs and key extracted findings/proof. This is non-negotiable. Include historical pattern searches explicitly.

**Recommended Bets**
| Match | Selection | Decimal Odds | Stake (NOK) | Est. EV / Conviction | Rationale (with data) | Risk Notes |
|-------|-----------|--------------|-------------|----------------------|-----------------------|------------|
| ... | ... | ... | ... | ... | ... | ... |

**Portfolio Summary**
- Total Stake: XX NOK
- Number of Bets: X
- Diversification: [list sports/bet types — must meet rules; note exploration from other sports enforced]
- Blended Portfolio EV: X%
- Max Single Bet Risk: XX NOK
- Overall Risk Assessment: [low/moderate with justification]

**Learning & Flags for Future**
[Any new patterns, edge updates needed, or notes from multi-agent simulation including historical insights.]

**Next Actions for User**
[Exact instructions for placing bets. Report settlements with details for deep dive.]

This format ensures clarity, reduces errors, and makes bets easy to copy/place.

## 5. Bet Log Archiving & Data Integrity Protocol (Fixes Large File Issues & Update Failures)

- **Monitoring**: Before any bet_log.csv operation, check size/row count (via tool or script).

- **Archiving Trigger**: When main bet_log.csv reaches ~100-150 lines or ~50-60kB (or proactively every major period):
  1. Create new archive file: bet_log_archive_up_to_YYYY-MM-DD.csv containing older settled bets (full copy of historical rows).
  2. Trim main bet_log.csv to keep only pending + recent ~40-50 settled bets.
  3. Update header/references if needed.
  4. Use nt-bet-log-manager or safe_bet_log_edit.py with full fetch + SHA + validation.
  5. Update current_bankroll.md, any references in playbook/README.
  6. Full Git push + re-verify tree/content.

- **Settlement & Append Update Rules (Strengthened for Reliability - Addresses Update Failures & Breaking CSV)**:
  - **Every single update (settlement or new pending append)**: 
    1. Full fetch of current bet_log.csv content + exact current SHA.
    2. Verify header matches EXACTLY: "Date,Match,Selection,Decimal_Odds,Stake_NOK,Result,P_L_NOK,Notes" before proceeding.
    3. Use exclusively nt-bet-log-manager skill or scripts/safe_bet_log_edit.py for modifications (append-only for new, targeted Result/P_L/Notes append for settlements - no overwrites/deletions of historical).
    4. Post-modification: Re-fetch full content. Confirm: 
       - Header exact match.
       - Row count increased only by expected number (no unexplained changes).
       - No broken CSV (proper quoting for Notes with commas/quotes, no malformation/garbage).
       - All historical rows untouched except precise targeted updates.
    5. If ANY discrepancy found: Immediate rollback to pre-SHA version, re-apply update, re-verify. Document issue and fix in Notes or round file.
    6. Update current_bankroll.md and round file only after successful bet_log verification.
  - Never compromise data integrity. Full backup via Git history + explicit verification proof in every operation.

- **Never compromise data**: Always backup first. Preserve every historical row forever in archives.
- Enhance scripts/safe_bet_log_edit.py if needed for automated archiving support.

## 6. Advanced Risk Management Framework (Fixes Low-Value Favorite Losses & Stupid Risks)

- **Core Rule**: Only bet when true edge exists with favorable risk/reward. Avoid or heavily deprioritize low-payout favorites unless exceptional justification.

- **Stupid Loss Filter**:
  - For favorites @1.40-1.60 (or similar low odds): Require EV >15-20% + strong multi-factor confirmation + better alternatives considered/skipped. Otherwise, skip or use ultra-small stake.
  - Explicit calculation in response: "Max loss: X NOK | Expected profit if wins: Y NOK | Risk/Reward ratio: Z".
  - Prefer bets with higher odds or balanced payout where possible (e.g., props, HC, totals with value).

- **Staking Rules**:
  - Default: Flat 10-25 NOK per bet (per acceleration rules), adjusted for bankroll/liquidity.
  - Or conservative fractional Kelly (0.25 Kelly max) for high-EV bets.
  - Hard cap on portfolio daily risk per playbook (~60-100 NOK or 1-2% bankroll).
  - High-variance/high-odds bets: Max 10 NOK, <5% allocation.

- **Portfolio Level**: Diversification already enforced; add explicit check for concentration in low-odds favorites.
- **Post-Loss Review**: Any cluster of losses on similar low-value bets triggers immediate review and filter tightening.

**WC/International Motivation & Set Piece Variance (Additive 2026-06-23 Meta-Review Learning)**: Recent deep dives (Algeria WC CS/corners losses despite pre-data edge; prior Argentina/France controlled games) show elevated variance in defensive bets (Clean Sheet, Under corners/totals) vs motivated debutants/must-win sides due to early counters, set pieces, or clinical low-event performance. **Risk Manager Agent must flag**: Require stricter pre-filter confirmation ('opponent counter/set piece threat low + sustained defensive organization + no high motivation variance from must-win/debutant context'). Do not rely solely on season avgs or xG. Explicit R/R and stupid loss still apply; deprioritize or ultra-small stake if motivation flags high. Update sport_edges additively (already done post-Algeria). Tool proof mandatory in all such reviews.

**Grass Court Game Totals Over Variance (Additive 2026-06-23 Meta-Review)**: Tennis grass Over 21.5-23.5 losses (Dzumhur/Paolini rounds) despite rally-profile data due to serve efficiency/hold dominance shortening matches or higher-seed rust enabling clinical wins. **Risk Manager**: Add to totals filter pre-check ('both players strong return stats confirmed + H2H history of extended rallies on surface + no projected serve/hold dominance'). Prefer or pair with Under alt in serve-efficient profiles. Variance analysis: Lower than ML but still requires multi-factor beyond general surface. Explicit R/R calcs to include this. Data Hunter to prioritize serve/return stats in Stage 1/2 scans.

## 7. Skill Reliability & Consistent Usage

- **Reference Standard**: Always use exact skill names from nt-betting-skills.md (e.g., "nt-betting-workflow", "post-settlement-learning-reviewer", not generic "the skill").
- **Pre-Creation Check**: Before creating any new skill, reference existing documentation and confirm it doesn't duplicate or conflict.
- **Validation**: After skill-related actions, confirm execution and note any issues for self-correction.
- **Orchestration**: nt-betting-workflow remains the main coordinator; supporting skills handle specifics. No redundant creations.

## 8. First-Principles Thinking & Multi-Perspective Simulation

- **Mandatory Start**: Every analysis begins with first-principles breakdown (fundamentals of the event, independent of odds or recent history).
- **Internal Simulation**: Run the 4-agent debate (Value, Risk Manager, Data Hunter, Contrarian) as described in section 3. Document key arguments from each in the round file or response. Include historical pattern simulation from Section 1.5.

## 9. Self-Updating & "Just Works" Robustness

- **Proactive Improvements**: When patterns or issues are identified (from deep dives or user feedback), Grok proposes and implements additive updates to this protocol, playbook.md, sport_edges_and_filters.md, skills docs, or scripts — following full GitHub workflow (tree → content+SHA → full update → re-verify).
- **Complete Before Reply Rule**: All research (with tools + proof), analysis, multi-agent simulation, learning updates, GitHub pushes, and validations must be finished before the final response to the user.
- **No Shortcuts**: Follow every step in this protocol and referenced skills/playbook. If something feels off, pause and verify.
- **Meta-Review**: Periodically (every 10-20 settled bets or after major phases like WC group stage end) or when variance clusters noted (e.g., multiple alt market losses), run full meta-review using this protocol's Sections 1-3, 6, 8. Focus: active learning from losses (filter tightening), risk (stupid loss + variance sources like motivation/serve + historical patterns), tool usage compliance (mandatory proof in all deep dives including historical). Propose/push additive updates if gaps found. Document in protocol or playbook. Bias reset + 4-agent applied to the meta itself.

## 10. Integration with Existing System

- This protocol is referenced by nt-betting-workflow and other skills.
- Updates to playbook.md and sport_edges_and_filters.md will incorporate relevant parts.
- All future round files and responses must align with the standardized template and proof requirements.
- Existing good elements (diversification, min stake 10 NOK, exploration automation, post-settlement reviewers, autonomous decisions) are retained and strengthened.

**Implementation Status**: Created 2026-06-21 as part of fresh start. Updated 2026-06-23 with additive WC/grass variance risk guidance and meta-review cadence. Updated 2026-06-24 with Prioritized Data Sources & Historical Pattern Simulation (Section 1.5), strengthened bet_log verification (Section 5), mandatory broader sports exploration (Section 3), and clean bankroll reset integration. Updated 2026-06-25 with new Section 1.6 Maximum Tool Usage & Exhaustive Data Collection Mandate (forces max tool calls, source diversity, no early stopping, expanded proof). All per user feedback on data collection, bet_log updates, sports breadth, tool exhaustiveness, and clean restart. Future settlements and rounds will demonstrate compliance. All pushes followed Successful Push Workflow exactly (tree verify, content+SHA, full update, post re-verify).

**Success Metrics**: Consistent tool proof (including historical), broader bet types with deep data, fewer repetitive patterns (enforced exploration), clean responses, preserved data integrity (verified CSV every update), better risk-adjusted returns, reliable skill usage, continuous improvement without user intervention. Clean restart with 500 NOK bankroll active.

This protocol makes the system extremely robust and self-sustaining. Clean restart complete.