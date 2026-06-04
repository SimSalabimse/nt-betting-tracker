# NT Betting Tracker

This repository tracks our Norsk Tipping Oddsen betting system.

## Purpose
- Living playbook with all rules, sport edges, and decision logic
- Versioned bet logs and post-mortems
- Transparent tracking of bankroll, ROI, and lessons learned
- **Moderate acceleration active**: 15-25 NOK flat stakes on high-conviction bets (allow 4-6 bets/round when good opportunities exist). Daily risk target ~60-100 NOK. Strict loss caps apply.

## Current Bankroll
500 NOK (as of 2026-06-04)

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
2. Check `rounds/` folder for daily recommendations and results
3. Update after every settlement

## Structure
- `playbook.md` - Single source of truth
- `rounds/` - One file per betting round

Last updated: 2026-06-04