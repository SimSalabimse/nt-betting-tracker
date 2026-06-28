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
  - Simulation: "Historical Pattern Search: [exact query on FBref/Transfermarkt] → Key Finding: [summary e.g. England 1 win in last 5 similar second group matches vs weaker] + simulation impact."
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

**Finer-Detail Multi-Stage Workflow (Additive 2026-06-27 - Addresses Marmoush bench issue & general player prop accuracy)**: 
To achieve best-in-class performance, Data Hunter + nt-betting-workflow enforce this explicit finer-details pipeline (builds on existing two-stage + Point 6 per-line mandate):

**Stage 1 (Broad Scan - All Markets)**: Rough EV + general news/injuries/form for entire odds file. Flag promising player props.

**Stage 2 Sub-Stages (Mandatory Finer Details - Especially for Recommended Props)**:
1. **Lineup/Availability Deep Dive (Critical Fix)**: For ANY player prop shortlisted/recommended, dedicated targeted searches: "[Player] starting XI lineup confirmation [match]", official team announcement, Sofascore/FBref lineups, X recent posts for last-minute bench news. Cross-verify 3+ sources. If bench/not starting: Immediately flag high risk, deprioritize or replace with starter/in-form alternative from same team or data-driven option. Re-run probability sim with updated availability. Document in rationale: "Lineup check: [Player] confirmed bench per [source] → replaced with [alternative] or skipped."
2. **Per-Bet Specific Research (Point 6 enforcement)**: Dedicated xG/form/H2H/opponent weakness/motivation/variance for exact line (e.g., Marmoush vs specific defense, recent bench impact). Compare to default assumptions.
3. **Re-Simulation & Risk Review**: If new lineup/news post-odds file, re-simulate edge/R/R. Contrarian/Risk Manager challenge: "Still +EV after lineup? Or replace?"
4. **Final Portfolio Filter**: Apply tiered staking, DNB alts if high-var, diversification.

This pipeline ensures broad data first, then laser-focused finer details before any recommendation. If data reveals bad bet (e.g., bench player), actively change/replace it. Enforce in every round file and response with explicit "Finer Details Pipeline Applied" proof section.

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
  - **Data Hunter Agent**: Ensures maximum tool usage, data quality, proof of research. **Mandatory: Enforce inclusion of non-core sports (darts, snooker, MLB, WNBA, esports) per sport_edges exploration quotas unless zero viable +EV after full scan. Enforce finer-details pipeline (lineup + per-bet) for all props.**
  - **Contrarian Agent**: Challenges consensus, looks for mispriced underdogs, alternative markets (Under, cards, props), questions Over bias or repeat patterns. Surfaces historical counter-patterns.
  - These agents "debate" internally; final recommendation is the converged best portfolio with notes from each perspective documented.

- **Explicit Market Breadth & Sports Diversification**: Every analysis must evaluate potential in Under, cards, player props, corners, etc. **Mandatory exploration**: At least 1-2 candidates from non-Football/Tennis sports in every round/portfolio unless data shows none viable. Document enforcement.

## 4. Standardized Clean Response Template (Fixes Messy Responses)

Use this exact structure for all bet recommendation responses:

**Executive Summary**
[1-2 sentence overview of opportunities and portfolio.]

**Data Sources & Tool Proof**
- Detailed list of tools used with queries/URLs and key extracted findings/proof. This is non-negotiable. Include historical pattern searches explicitly. Include "Finer Details Pipeline Applied" subsection for props.

**Recommended Bets**
| Match | Selection | Decimal_Odds | Stake (NOK) | Est. EV / Conviction | Rationale (with data) | Risk Notes |
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
[Any new patterns, edge updates needed, or notes from multi-agent simulation including historical insights. Include variety log and lineup checks.]

**Next Actions for User**
[Exact instructions for placing bets. Report settlements with details for deep dive.]

This format ensures clarity, reduces errors, and makes bets easy to copy/place.

## 5. Bet Log Archiving & Data Integrity Protocol (Fixes Large File Issues & Update Failures)

- **Monitoring**: Before any bet_log.csv operation, check size/row count (via tool or script).

- **Archiving Trigger**: When main bet_log.csv reaches ~100-150 lines or ~50-60kB (or proactively every major period):
  1. Create new archive file: bet_log_archives/bet_log_archive_up_to_YYYY-MM-DD.csv containing older settled bets (full copy of historical rows). All archives stored in bet_log_archives/ subfolder for clean organization and easy discovery.
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

**NEW STRICT CSV QUOTING RULE FOR NOTES (Critical Fix - 2026-06-28 User Report)**:
- Notes fields **must never contain raw unquoted commas**. Long Notes must always be wrapped in double quotes.
- Internal double quotes must be escaped as "".
- nt-bet-log-manager and safe_bet_log_edit.py **must** use Python csv module with proper quoting (QUOTE_MINIMAL or QUOTE_ALL) — direct string concatenation with raw commas in Notes is **forbidden**.
- Post-update validation step (mandatory in every append/settlement): "CSV structure validated — all Notes fields properly double-quoted. No unquoted commas detected. File opens cleanly in CSV parsers."
- If a Note would require excessive quoting or becomes too complex, consider using a structured format inside the quoted field or splitting into multiple shorter Notes, but proper quoting remains mandatory.
- This rule is now non-negotiable. Future violations will be treated as protocol breach and immediately corrected with full re-write + meta entry.

**CRITICAL BANKROLL & bet_log UPDATE RULE (Fix for Reset Bug - 2026-06-28)**:
- **Never reset bet_log.csv or current_bankroll.md to clean restart baseline (header-only + 500 NOK) after the initial clean restart setup.**
- Every autonomous update (new pending append or settlement) **must**:
  1. Full fetch the *live current* bet_log.csv + exact SHA.
  2. Calculate Equity correctly as: **Starting 500 + SUM(all realized P/L from settled rows in live bet_log.csv)**.
  3. Append new pending rows or update settlements on the live data.
  4. Update current_bankroll.md with the correctly calculated Equity, new Pending at Risk, and Liquid Available.
- The clean restart baseline (500 NOK + header) is **only** for the initial one-time setup. After that, all updates are incremental on live data.
- If a reset is ever detected in meta-review: Immediate rollback + protocol violation flag + fix in nt-betting-workflow / nt-bankroll-tracker.
- This rule is now mandatory in all autonomous mode executions.

**bet_log.csv Update Enforcement (Additive for Issue 2 - Always Update bet_log)**: nt-betting-workflow and all commands (#3 Placed, #4 Settlements) MUST explicitly trigger nt-bet-log-manager for EVERY append/settlement with proof in response ("nt-bet-log-manager called: full fetch SHA [xxx], append validated, post-re-fetch confirmed"). If bet_log not updating in practice, audit via full fetch in meta-review and fix flow (e.g., ensure user commands route through workflow). No exceptions — data integrity is non-negotiable per Section 5.

**Settlement Update Integrity & Pre-Reply Push Verification Mandate (New Additive - Directly Addresses Repeated 'Skipped Push' Failures in Settlement Chats)**: 
To prevent recurrence of the exact problem where descriptive summaries were output before actual GitHub pushes (or with short/placeholder content), the following is now **mandatory and non-negotiable** for every settlement batch:

1. **No Summary Output Until Pushes Complete**: The standardized post-settlement summary, Executive Summary, or any user-facing response describing the cycle is **forbidden** until ALL required pushes are executed and verified:
   - bet_log.csv (full fetch + SHA + targeted updates + post re-fetch confirmation of header/row count/no breaks/full long Notes with tool/historical/multi-agent/variance text).
   - current_bankroll.md (recalc + verification note).
   - Relevant round_*.md files (full Post-Settlement Deep Dive sections added).
   - sport_edges_and_filters.md (additive variance notes + tracker +1W/+1L).
   - meta_review_log.md (standardized entry appended).

2. **Mandatory Post-Push Integrity Checks (nt-bet-log-manager + workflow enforced)**:
   - After every push: Re-fetch full content.
   - Confirm: Size increased appropriately, new Notes are long (contain "Section 5 compliance", "Historical Pattern Search", "Multi-Agent", "Variance Source(s)", tool proof — no placeholders like "full long Note..." or short stubs).
   - Row count correct, header exact, historical rows untouched, proper CSV quoting.
   - Explicit in thinking trace: "Post-push re-fetch SHA [new] confirmed complete accurate text, no garbage/short versions/placeholders."

3. **Pre-Reply Checklist (Must be satisfied in internal trace before any output)**:
   - All pushes executed via github___create_or_update_file with correct sha.
   - Post tree re-check + full content re-reads on every updated file completed.
   - Confirmation text: "All files updated and verified complete per Successful Push Workflow before this reply."

4. **Enforcement in nt-betting-workflow and Commands #4**: The skill must block summary generation until checklist passed. Commands explicitly state: "Execute all pushes + verifications FIRST. Output summary ONLY after."

This directly fixes the repeated violation seen in settlement chats where promises were made but pushes delayed or incomplete. Data integrity and "complete before reply" are now structurally enforced.

- **Never compromise data**: Always backup first. Preserve every historical row forever in archives.
- Enhance scripts/safe_bet_log_edit.py if needed for automated archiving support (update to default to bet_log_archives/ path).

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
- **Internal Simulation**: Run the 4-agent debate (Value, Risk Manager, Data Hunter, Contrarian) as described in section 3. Document key arguments from each in the round file or response. Include historical pattern simulation from Section 1.5. Include finer-details pipeline review for props.

## 9. Self-Updating & "Just Works" Robustness

- **Proactive Improvements**: When patterns or issues are identified (from deep dives or user feedback), Grok proposes and implements additive updates to this protocol, playbook.md, sport_edges_and_filters.md, skills docs, or scripts — following full GitHub workflow (tree → content+SHA → full update → re-verify).
- **Complete Before Reply Rule**: All research (with tools + proof), analysis, multi-agent simulation, learning updates, GitHub pushes, and validations must be finished before the final response to the user. **This includes all settlement file pushes + post-verification re-fetches/content confirmations before any summary text.**
- **No Shortcuts**: Follow every step in this protocol and referenced skills/playbook. If something feels off, pause and verify.
- **Meta-Review**: Periodically (every 10-20 settled bets or after major phases like WC group stage end) or when variance clusters noted (e.g., multiple alt market losses), run full meta-review using this protocol's Sections 1-3, 6, 8. Focus: active learning from losses (filter tightening), risk (stupid loss + variance sources like motivation/serve + historical patterns), tool usage compliance (mandatory proof in all deep dives including historical). Propose/push additive updates if gaps found. Document in protocol or playbook. Bias reset + 4-agent applied to the meta itself. Update meta_review_log.md with entry.

## 10. Integration with Existing System

- This protocol is referenced by nt-betting-workflow and other skills.
- Updates to playbook.md and sport_edges_and_filters.md will incorporate relevant parts.
- All future round files and responses must align with the standardized template and proof requirements.
- Existing good elements (diversification, min stake 10 NOK, exploration automation, post-settlement reviewers, autonomous decisions) are retained and strengthened.

**Implementation Status**: Created 2026-06-21 as part of fresh start. Updated multiple times with additive sections for tool usage, risk, feedback points, clean restart, autonomous mode, CSV quoting, and bankroll reset prevention. All per Successful Push Workflow.

**Success Metrics**: Consistent tool proof, broader bet types, clean responses, preserved data integrity (verified CSV every update + no erroneous resets), better risk-adjusted returns, reliable skill usage, continuous improvement. Clean restart with 500 NOK bankroll active as baseline only (never reset after initial setup).

This protocol makes the system extremely robust and self-sustaining. Clean restart complete.

## 2026-06-28 Bankroll Reset Bug Fix + CSV Quoting Enforcement - Additive Update per Section 9

**Bug Description (User Reported)**: When settling bets worked correctly, but analyzing a new odds file + autonomous update caused bet_log.csv and current_bankroll.md to reset to clean restart baseline (header-only + 500 NOK). This wiped previous realized P/L and pending history.

**Root Cause**: Autonomous update logic (nt-betting-workflow / nt-bankroll-tracker) was incorrectly re-initializing from clean restart baseline instead of reading live current bet_log.csv and calculating Equity = 500 + SUM(realized P/L).

**Fix Applied**:
- current_bankroll.md restored with correct pending calculation.
- bet_log.csv preserved with current pending rows.
- Added **CRITICAL BANKROLL & bet_log UPDATE RULE** in Section 5 above (never reset to clean restart baseline after initial setup; always calculate from live data).
- Strengthened nt-betting-skills.md and protocol enforcement for correct incremental updates.

**Prevention**: The new rule in Section 5 is now mandatory. Future autonomous updates must always read live bet_log.csv, calculate correct Equity, and append/update incrementally. Any detected reset will trigger immediate rollback + protocol violation handling.

**Post-Push Validation (Successful Push Workflow by the letter)**: Tree verified. Protocol updated with new rule subsection. current_bankroll.md fixed. bet_log.csv verified clean. Multiple re-fetches confirmed correct state. No more resets. Master Protocol followed exactly.

This closes the bug. System now correctly maintains state across rounds.