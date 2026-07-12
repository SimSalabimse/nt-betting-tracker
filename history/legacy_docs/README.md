# NT Betting Tracker

This repository tracks our Norsk Tipping Oddsen betting system.

## Purpose
- Living playbook with all rules, sport edges, and decision logic
- Versioned bet logs and post-mortems
- Transparent tracking of bankroll, ROI, and lessons learned
- **Moderate acceleration active**: 15-25 NOK flat stakes on high-conviction bets (allow 4-6 bets/round when good opportunities exist). Daily risk target ~60-100 NOK. Strict loss caps apply.

## Current Bankroll
500 NOK (as of 2026-06-04)  [Note: See current_bankroll.md for latest ~393 NOK equity with pending]

## Moderate Acceleration Rules (Active)
**✅ Got it. Moderate acceleration confirmed.**

Effective immediately:
- **Flat 15-25 NOK** per high-conviction single (or system equivalent, always meeting the 10 NOK per leg/row minimum).
- Allow **4-6 bets per round** when there are multiple good +EV opportunities (instead of max 3).
- Daily portfolio risk target: **~60-100 NOK** max initially.
- Strict daily loss caps + full review if hit still apply.
- We stay in Phase 1 (Protect & Validate) but with this slightly faster ramp. Once bankroll hits ~1000 NOK and we have solid data (positive ROI over 20-40 bets), we accelerate further.

The 3 bets you placed today at 10 NOK each were the transition round. From the next round onward we use the new 15-25 NOK range.

## Quick Start
1. Read `playbook.md` for full rules and strategy
2. Check `robust_betting_protocol_v2.md` for the master robustness improvements (tool proof, risk management, clean templates, active learning, etc.)
3. Check `rounds/` folder for daily recommendations and results
4. Update after every settlement

## Structure (Clean Restart 2026-06-28)
- Root: Active files only (bet_log.csv, current_bankroll.md, robust_betting_protocol_v2.md, README.md, nt-*.md files, Betting_Commands.txt, sport_edges_and_filters.md, meta_review_log.md)
- `rounds/`: All historical and current round analysis/recommendation files (post-use move to rounds/archived/ for future to keep active scans fast)
- `bet_log_archives/`: All historical bet_log archives + clean restart snapshots of current bet_log.csv and current_bankroll.md as of 2026-06-28 (full history preserved; main bet_log.csv reset to header-only for fresh start era)
- `scripts/`: Supporting automation scripts

**Clean Restart 2026-06-28 Completed**: All stray round_ files moved to rounds/. All remaining root bet_log_archive_*.csv + backups moved to bet_log_archives/. Current bet_log.csv and current_bankroll.md fully archived as dated snapshots. bet_log.csv reset to clean header for new era. All key files updated (protocol, commands, README, data sources). Autonomous mode active. Root perfectly clean. Multiple Successful Push Workflow verifies passed.

## Bankroll & Data Tracking Updates (2026-06-04 original + ongoing)

- Added `current_bankroll.md`: Detailed additive tracker...
- Fixed formatting in `bet_log.csv`...

See `current_bankroll.md`, `bet_log.csv`, `playbook.md`, and the new `robust_betting_protocol_v2.md` for full details. All updates follow strict GitHub workflow and validation. The system is now significantly more robust with mandatory tool proof, standardized outputs, better risk controls, autonomous updates, and self-updating mechanisms. Last updated: 2026-06-28 (Full Clean Restart + Autonomous Enforcement).