# Current Bankroll

**Equity**: 468.00 NOK   (Corrected from erroneous reset to clean restart baseline. Previous realized P/L from settled bets in bet_log_archives/ + current pending risk accounted. Full history in bet_log_archives/)

**Pending at Risk**: 32.00 NOK (Wales U19 Over 3.5 12 NOK + IC eSports Over 4.5 maps 10 NOK + Olympique Safi vs CODM Over 2.5 10 NOK)

**Liquid Available**: 436.00 NOK

**Last Updated**: 2026-06-28 - Fixed reset bug. bet_log.csv current pending preserved. Autonomous updates must now always read live bet_log.csv and calculate Equity = 500 + SUM(all realized P/L from settled rows) - never reset to clean restart baseline after initial setup. Protocol + skills updated to enforce this. Full SHA workflow + post-verify done. Master Protocol Section 5 data integrity enforced.