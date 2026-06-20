# round_20260620_current_odds_04.md — Processing of current_odds_01.txt (Spanish lower leagues + Norwegian + Almeria/Malaga + WNBA + MLB + Darts + Esports)

**Date**: 2026-06-20 (late batch) | **Source**: /home/workdir/attachments/current_odds_01.txt (new 15kB mixed odds dump) | **Workflow**: nt-betting-workflow + nt-bet-log-manager + nt-bankroll-tracker + post-settlement-learning-reviewer

**Bets placed (exact)**:
1. Frigg vs Lokomotiv Oslo — Over 3.5 goals @1.45 stake **12 NOK** — **Loss** -12.00
2. Almeria vs Malaga — Begge lag scorer Ja @1.72 stake **12 NOK** — (user did not report; assume pending or settled separately)
3. Nathan Aspinall vs Jim Long (Darts) — Aspinall totalt antall 180s Over 2.5 @1.65 stake **10 NOK** — **Loss** -10.00 (NEW ODDS TYPE)

**Total stake this batch**: 34 NOK | **Net P/L reported**: -22.00 NOK (from reported settlements)

**Post-Settlement Deep Dive (nt-bet-log-manager + post-settlement-learning-reviewer executed)**
**Settlements reported**:
- Frigg Over 3.5: Loss (did not hit despite form/xG research supporting open game).
- Aspinall O2.5 180s: Loss (variance in scoring rate realized despite good rate research).
- Gentle Mates -1.5 (from prior round): Loss (esports BO3 variance).

**Deep dive learnings**:
- **New type 180s prop variance**: The Aspinall 180s Over was a deliberate exploration bet. Edge was real on paper (form + expected leg count), but variance in leg scoring/defensive opponent realized. Lesson reinforced: Darts scoring props good for small-stake diversification but require per-player consistency filter and acceptance of variance. Prefer when multiple supporting factors align strongly.
- **HUB Over 3.5 in Norwegian**: Similar to previous Over 2.5 lessons — can have variance even when filters met. Tighten for expected goal volume or prefer BTTS in some spots.
- **Esports map HC**: Gentle Mates loss adds to pattern of higher variance in BO3 than pre-match form suggests (opponent adaptation). Lesson: Tighten filter for recent map record vs specific opponent; keep small stakes.

**Additive updates to sport_edges_and_filters.md completed** (Darts 180s section: variance lesson + continued selective use; HUB football Over totals: tighten volume filters; Esports map HC: adaptation note).

**Bankroll impact**: Equity 378.64 NOK after batch. All GitHub updates pushed + re-validated.

**All workflow steps completed and validated per strict protocol.**