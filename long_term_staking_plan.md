# Long-Term Staking Plan (Phased Progression with NOK Milestones)

**Last Updated:** 2026-07-08

This document defines the long-term staking and risk progression for the nt-betting-tracker system. It is designed to be gradual, responsible, and compliant with Norsk Tipping rules.

The system uses **hybrid triggers** (Equity amount **or** number of settled bets) to avoid getting stuck in early phases.

## Current Status
- We are currently in **Phase 1B** (advanced 2026-07-08).
- We have more than 110 settled bets (user confirmed with stable/positive results across recent batches).
- Phase advancement confirmed after discussion per plan rules (OR trigger: 40+ settled bets with stable/positive results met; Equity still in 1B range).
- Goal: Move to Phase 2 once we hit either 1,200 NOK Equity **or** 60 settled bets with stable/positive results.

## Phased Progression Plan

| Phase | Equity Range          | Trigger to Enter                          | Max Bets per Round | Stake Size       | Combo / System Policy                              | Max Risk per Round     | Purpose of Phase                              |
|-------|-----------------------|-------------------------------------------|--------------------|------------------|----------------------------------------------------|------------------------|-----------------------------------------------|
| **1A** (Previous) | < 700 NOK            | Starting point                            | 1–4 single bets    | 10–15 NOK        | **No combos**                                      | Max 50 NOK            | Build discipline, clean data, and habits      |
| **1B** (Current) | 700 – 1,200 NOK      | 700 NOK **or** 40 settled bets            | 2–5 bets           | 12–20 NOK        | **Max 1 double per round** (only strong cases)     | Max 70–80 NOK         | First controlled introduction of doubles      |
| **2**            | 1,200 – 2,500 NOK    | 1,200 NOK **or** 60 settled bets          | 2–6 bets           | 15–30 NOK        | Max 2 doubles per round                            | Max 3% of Equity      | Normal and controlled use of doubles          |
| **3**            | 2,500 – 5,000 NOK    | 2,500 NOK                                 | 3–7 bets           | 20–45 NOK        | Max 2 doubles or 1 small triple                    | Max 3.5–4% of Equity  | Introduce small systems                       |
| **4**            | 5,000+ NOK           | 5,000 NOK                                 | Flexible           | 2–4% of Equity   | Selective 2–3 leg systems allowed                  | Max 4–5% of Equity    | Mature, optimized, but responsible growth     |

## Core Rules (Apply in All Phases)

- **Norsk Tipping Compliance**: We stay within responsible gambling limits and combo restrictions.
- **Equity Rule**: Equity is only adjusted on settled bets (Win = +P/L, Loss = -Stake).
- **Stupid Loss Filter** and **DNB Preference** remain active at all times.
- **Short Notes Rule** is mandatory in `bet_log.csv`.
- **Post-Settlement Learning** must include tool searches and real edge updates.
- Max risk per round is always capped as a percentage of current Equity.

## When to Move Between Phases

We only move to the next phase when **at least one** of the following is true:
- We reach the Equity target for the next phase, **or**
- We complete the required number of settled bets **with stable or positive results**.

**2026-07-08 Phase Advancement Note**: Advanced from 1A to 1B after user confirmation of >110 settled bets (well over 40 trigger) with stable/positive results across batches. Phase change was discussed and confirmed before any change to staking behavior or combo policy. Max 1 double (2-leg combo) per round now allowed on strong, multi-perspective researched cases only. Full GitHub SHA workflow + verification completed for this update.

## Success Metrics

- Consistent positive or break-even ROI over meaningful samples.
- High-quality post-settlement learning reviews.
- Proper file updates (bet_log.csv and current_bankroll.md).
- Controlled risk and gradual growth.

This plan ensures we grow responsibly while avoiding both stagnation and reckless aggression.