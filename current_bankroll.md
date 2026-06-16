# Current Bankroll Status (Strict Rule - Single Source of Truth: bet_log.csv)

**Last Updated**: 2026-06-16 (after nt-bet-log-manager settlement of 4 bets: Rochedale Rovers O3.5 win, Mateusz Baranowski +0.5 loss, Sashi eSport -1.5 loss, Game Master -1.5 win; Fu -3.5 and Rublev Under 25.5 remain Pending)
**Verified via**: Full bet_log.csv recalc using strict formula (Equity = 500 + SUM(P_L_NOK where Result != 'Pending'); Pending = SUM(Stake where Pending); Liquid = Equity - Pending). analyze_betting.py logic applied. nt-bankroll-tracker protocol followed exactly.

## Bankroll Figures (as of this update)
- **Initial Bankroll**: 500.00 NOK
- **Realized P/L (all settled rows in active log)**: -9.22 NOK
- **Bankroll (Equity)**: 490.78 NOK
- **Pending at Risk**: 24.00 NOK (Fu -3.5 frames @12 NOK + Rublev Under 25.5 games @12 NOK)
- **Liquid Available for new bets**: 466.78 NOK

**Settled in this batch**:
- Rochedale vs Moreton City Over 3.5 total goals @1.72 (12 NOK) - Win +8.64 NOK payout 20.64
- Baranowski vs O'Sullivan Baranowski +0.5 frames @1.82 (12 NOK) - Loss -12.00 NOK
- Sashi eSport vs Hyperspirit Sashi eSport -1.5 @2.10 (12 NOK) - Loss -12.00 NOK
- Game Master vs Grey Track Game Master -1.5 maps @1.82 (12 NOK) - Win +9.84 NOK payout 21.84

Net batch P/L: -5.52 NOK. Total realized now -9.22 NOK.

**Verification Checklist Executed**:
1. bet_log.csv updated via nt-bet-log-manager protocol (4 rows updated in place for Result/P_L_NOK + Notes append with 'Settled' details and deep dive pointer; header, historical rows and structure 100% preserved). Re-fetch validated clean.
2. Full recalc: Equity = 500 + (-9.22) = 490.78. Pending = 24.00. Liquid = 466.78.
3. Cross-check vs actual Norsk Tipping balance: User confirmation needed (flag if >5-10 NOK diff).
4. No discrepancy in logged figures. Settlements correctly moved value from Pending to realized P/L.
5. Additive only, Git history preserved. nt-bankroll-tracker skill/protocol followed by the letter.

**Portfolio note**: Low remaining risk (24 NOK on 2 pending). Original placement followed exploration quota (Snooker 2), diversification. Phase 1 singles stability.

**Next**: Monitor Fu and Rublev pending. On settlement: nt-bet-log-manager update CSV + mandatory deep dives in round md BEFORE reply + re-verify this file + run analyze script if possible.

*Bankroll update pushed and validated per playbook 2026-06-14 Major Implementation + nt-bet-log-manager/nt-bankroll-tracker skills. All before user reply.*