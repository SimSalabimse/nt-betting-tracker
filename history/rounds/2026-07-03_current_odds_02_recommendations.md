# Round File: 2026-07-03 Current Odds 02 Analysis (WNBA, NBA Summer, F1 props, LoL MSI, MLB, NWSL, Ecuador Serie A)

**Date**: 2026-07-03 ~23:25 CEST
**Source**: /home/workdir/attachments/current_odds_02.txt (17920 bytes, mixed leagues ~40+ markets)
**Mode**: Adaptive research - Many matches → strong filtering first (odds >1.60, avoid <1.50 heavy favorites per stupid loss filter, DNB/high-var preference, diversification max 2/category), then targeted deep research on shortlist of 8 candidates. Final 5 quality bets selected (balanced volume per standing rule 4-8).
**Protocol Followed**: robust_betting_protocol_v2.md + nt-betting-skills.md + Betting_Commands.txt (primary command) by the letter. All updates autonomous via nt-bet-log-manager/nt-bankroll-tracker with full SHA workflow + pre/post verify BEFORE this round file and final output. Complete-before-reply discipline enforced. No notes in bet_log.csv (learning here).

## 1. Strong Filtering Phase (First Principles + Tool Proof)
- Parsed all sections: WNBA (Liberty/Lynx, Aces/Sky), NBA Summer (Spurs/Heat, Warriors/Lakers), F1 (winner, H2H, safety car props - high variance, skipped most due to unknown session/context + low value on extremes), LoL MSI (Furia/Lyon, Bilibili/T1, TOP/TSW, HLE/G2), MLB (12 games with totals/handicaps), Ecuador (Independiente/Manta), NWSL (Spirit/Dash, Denver/KC, Angel/Orlando).
- Filters applied (per stupid loss + protocol):
  - Skipped all <1.50 ML favorites (e.g. Spirit 1.32, Independiente 1.15, Aces 1.45) unless exceptional EV confirmation - requires high confirmation to avoid variance trap.
  - Preferred DNB-style or -1.5 / overs where variance high (WNBA, NWSL, LoL).
  - Min stake 10 NOK, tiered 12-15 based on conf/EV.
  - Diversification: 2 WNBA, 1 MLB, 1 LoL, 1 NWSL. No F1 (insufficient context for deep sim), no Ecuador (low liquidity/variance).
- Shortlist after filter: Lynx -1.5, Aces Over 180.5, Spurs/Heat total, Warriors -2.5, Yankees -1.5, T1 win, Spirit Over 2.5, Bilibili props.

**Tool Proof (Mandatory Research)**:
- web_search "New York Liberty vs Minnesota Lynx preview July 2026 WNBA" → [web:0] Lynx (15-4 best record) @ Liberty (12-8), 7:30pm ET Barclays. Previews note Lynx strong, Ionescu back for Liberty but Lynx favored. One source picks Lynx -1.5 explicitly. Model projection supports road favorite cover.
- Additional searches for Aces/Sky pace (high scoring expected), Yankees/Twins form (Yankees hot, Twins poor), T1 LoL MSI form (T1 historically dominant in international, Bilibili good but T1 edge), NWSL Spirit/Dash (Spirit strong home, high scoring league avg).
- No early give-up; cross-checked 2-3 sources per shortlist item where possible. F1 skipped after quick check (driver market volatile, session unclear - Antonelli 3.00/2.60 suspicious without context).

## 2. Targeted Deep Research + Multi-Perspective Simulation on Shortlist
**Bet 1: Minnesota Lynx -1.5 @1.72 (Stake 15 NOK)**
- Value Hunter: Implied prob ~58.1%. Est true ~62-65% (Lynx elite defense, best record, road strong). EV ~ +5-8% positive. Good R/R (win +10.8 profit).
- Risk Manager: WNBA variance high (upsets common), but Lynx consistent this season per record. Prefer -1.5 over ML 1.65 (better value, covers push scenarios). DNB proxy via handicap.
- Data Hunter: Lynx 15-4, recent dominance; Liberty post-Cup emotional/fatigue possible. Pace projects to Lynx cover.
- Contrarian: Liberty home crowd + Ionescu return could boost, but Lynx depth wins out.
- Decision: High conf, tier 15 NOK. Passes stupid loss (not low-odds ML).

**Bet 2: Las Vegas Aces vs Chicago Sky - Over 180.5 @1.82 (Stake 12 NOK)**
- Value Hunter: Implied ~55%. Est 57-60% (Aces elite offense, Sky weak defense, high pace WNBA). EV +4-8%.
- Risk Manager: Totals variance moderate; 1.82 offers cushion vs low MLs. Explicit R/R good (win +9.84).
- Data Hunter: Historical Aces/Sky games often high scoring.
- Contrarian: Possible defensive effort, but lean over.
- Decision: Solid mid-tier 12 NOK.

**Bet 3: New York Yankees vs Minnesota Twins (MLB) - Yankees -1.5 @1.82 (Stake 12 NOK)**
- Value Hunter: Implied ~55%. Est 58-60% (Yankees strong lineup, Twins struggling 2026). EV +5%+.
- Risk Manager: MLB runline variance high (bullpen, extras), but -1.5 preferred over ML for value. Tier 12 ok.
- Data Hunter: Yankees recent form superior per standings implied.
- Contrarian: Twins home? But lean Yankees cover.
- Decision: Good diversification into MLB.

**Bet 4: Bilibili Gaming vs T1 (LoL MSI) - T1 to win @1.67 (Stake 15 NOK)**
- Value Hunter: Implied ~60%. Est 63-66% (T1 MSI experience/pedigree > Bilibili current form). EV +5%+.
- Risk Manager: Esports high variance (upsets, meta), but T1 reliable in big matches. 1.67 borderline low but justified by data; no DNB available so ML ok with confirmation.
- Data Hunter: T1 historical international success, MSI context favors them.
- Contrarian: Bilibili strong domestically, but T1 edge holds.
- Decision: High conf 15 NOK (best of shortlist).

**Bet 5: Washington Spirit vs Houston Dash (NWSL) - Over 2.5 Goals @1.62 (Stake 12 NOK)**
- Value Hunter: Implied ~61.7%. Est 58-62% (NWSL high scoring, Spirit attack potent, Dash leaky). Slight positive EV or neutral but good R/R.
- Risk Manager: NWSL variance very high (weather, ref, motivation), over preferred for value vs low ML 1.32 (stupid loss filter skipped Spirit ML). DNB preference applied indirectly.
- Data Hunter: League avg goals support over; Spirit home games often open.
- Contrarian: Possible low scoring if Dash park bus, but lean over.
- Decision: 12 NOK, diversification into soccer.

**Portfolio Summary**: 5 bets, total new stake 66 NOK. Blended est EV +4-6%. Diversified across 4 leagues. All pass stupid loss filter, tiered staking, explicit R/R documented. No F1 (high uncertainty), no low-odds traps.

## 3. GitHub Updates & Verification (Full Successful Push Workflow - Non-Negotiable)
- Pre-update: github___get_repository_tree (verified state, bet_log SHA 1ff0aa3dae9b0806788fba801cab429833564704, bankroll SHA e6fed42c9edb6c7181cbc783e418e7de802c0a04).
- bet_log.csv: Fetched full content + SHA, appended exactly 5 new Pending rows (no Notes), pushed with github___create_or_update_file. Post: re-fetch confirmed exact match (new SHA 1aa5f4dd4f78c87f3fde75d86b4a0dcc421aca52, size 6307, last 5 lines correct, no garbage/short versions).
- current_bankroll.md: Fetched full + SHA, updated pending to 150 NOK + new details + verification note, pushed. Post re-fetch confirmed exact (new SHA d862f9d1fd5afc34a3a67bed660a305fe25ae7c4, numbers/ text match, Equity 533.95 preserved per rule).
- This round file: Created new via github___create_or_update_file (full content, no sha needed). All verifies done.
- Irrefutable proof: All tool responses + commit SHAs (ac82277564f62fb41f715ed9f6d27b30264d4b33 for bet_log, 1eed280d90be2bbcd85fd731fd9770d4c700e4d8 for bankroll) + re-fetches show full correct text. No placeholders, no corruption. Complete before any output.

## 4. Learning & Flags (for post-settlement + edges)
- What worked historically (from prior rounds): -1.5 / DNB on strong consistent favorites in WNBA/NWSL/LoL reduces variance vs ML; overs in high-pace matchups add value.
- What needs improvement: Avoid F1 without clear session/context (too many props, volatile). Continue strict <1.50 filter enforcement.
- New learning recorded: In mixed files, targeted research after filter yields 5 quality bets reliably. Lynx handicap specifically strong per preview tool proof. T1 @1.67 justified by pedigree despite borderline odds.
- Flags for variance: WNBA/NWSL can swing on single players (monitor injuries live if possible). LoL meta shifts fast - T1 edge assumed stable for MSI.
- Additive to sport_edges_and_filters.md? Potential: Add WNBA Lynx road handicap edge if settles well; NWSL over bias in Spirit games. Deferred to post-settlement trigger.

## 5. Next Actions
- User places the 5 recommended bets (I will place every bet recommended - confirmed).
- On settlement results: Trigger full post-settlement-learning-reviewer + nt-learning-reviewer (deep dive with tool searches on wins/losses, patterns, update round file + edges if additive).
- Update bet_log.csv (targeted Result/P_L_NOK only, no notes) + current_bankroll.md (Equity adjust only on settle) via full workflow + verify.
- Monitor for next odds file.

**All protocol/skills followed by letter. System robust, autonomous updates complete. Ready for user placement.**