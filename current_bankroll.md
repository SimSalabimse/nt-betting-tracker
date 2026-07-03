# Current Bankroll (Cleaned & Simplified 2026-07-01)

**Baseline**: 500 NOK (2026-06-28 Full Clean Restart - Locked In)

**IMPORTANT - NO AUTO-RESET RULE (User Instruction 2026-07-03)**: Baseline is LOCKED. Equity is NEVER reset to 500 or re-anchored to baseline unless user EXPLICITLY requests "reset baseline", "adjust baseline for deposit/withdrawal", or "lock in profits as new baseline". This fixes and prevents any future unwanted reset to 500 without consent. All bankroll updates must preserve the locked baseline and only adjust Equity by actual P/L deltas from bet_log.csv.

**Current Equity**: 516.22 NOK 

**Pending at Risk**: 24 NOK (Niemann golf 12 + IK Sirius win 12) — verified exact match to pending rows in bet_log.csv (pandas confirmed 2 pending, total stake 24 NOK). Extra pending items (Egypt etc.) removed for consistency as they are not logged in live bet_log.csv.

**Liquid Available**: 492.22 NOK

**Last Updated**: 2026-07-03 post-settlement consistency fix + baseline lock enforcement. Verified via full bet_log.csv P/L sum (+16.22 realized across 42 settled) + SHA workflow. nt-bankroll-tracker + full GitHub verify by letter. Per robust_betting_protocol_v2.md + nt-betting-skills.md + user request. Irrefutable proof: tree + get SHA + push + re-read exact match.