# Current Bankroll

**Equity**: 319.72 NOK  
**Pending at Risk**: **0 NOK** (Uruguay vs Cape Verde 3 bets settled this batch; previous pending cleared)  
**Liquid Available**: **319.72 NOK**

**Last Updated**: 2026-06-22 (post-settlement batch via post-settlement-learning-reviewer + nt-bet-log-manager + nt-bankroll-tracker skills executed in full per robust_betting_protocol_v2.md Sections 2 & 5 + nt-betting-skills.md. bet_log.csv full fetch + SHA a3df8fd1.. first; exact 3 matching rows updated with Result/P_L_NOK + deep dive Notes (hyp vs reality, tool proof from ESPN/FIFA/Guardian/X boxscores + xG 2.34/0.86, 2-2 result, Pina FK + Varela gift goal explanations). Net P/L for batch -17 NOK realized. Bankroll recalc from all realized P/L in updated bet_log.csv. All pushes validated with tree + re-read before/after. Multi-agent simulation applied to outcomes: Value noted corners edge held while goal lines showed WC variance; Risk highlighted need for tighter filters on motivated minnows; Data Hunter confirmed tool-backed explanations; Contrarian pointed to resilience of debutants vs xG models. First-principles: reviewed fundamentals (motivation, errors, set pieces) not bias.)

**Settlements processed this batch (with full deep dive in round file)**:
- Uruguay vs Cape Verde corners Over 5.5 @1.50 stake 10 NOK → Win +5 P/L (payout 15 NOK). Hyp matched (dominance held). Tool proof: boxscores confirm high URU corner volume.
- Uruguay vs Cape Verde Under 2.5 @1.72 stake 12 NOK → Loss -12 P/L. Hyp (xG 2.6 + trends) vs reality (2-2, 4 goals): CV historic FK + URU defensive gift (Olivera error). Lesson: Add stricter 'motivated debutant + no set piece threat' filter for Under in WC.
- Uruguay vs Cape Verde BTTS Nei @1.48 stake 10 NOK → Loss -10 P/L. Both scored via set piece + error. Lesson: BTTS No needs extra defensive error/set piece filter; corners edge more robust.

**Validation note**: Full bet_log.csv + SHA fetched first. Only exact rows modified. Post-update re-read confirmed correct P_L_NOK/Notes. Equity = previous 336.72 + net -17 = 319.72. Pending cleared for these bets. nt-bankroll-tracker + post-settlement-learning-reviewer followed exactly. References: robust_betting_protocol_v2.md, bet_log.csv (re-read SHA a3df8fd..), round file (deep dive appended). Ready for nt-learning-reviewer edge tracker update.