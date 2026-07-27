# Tennis live capture fixtures (PR-4)

## Capture recipe (§2.5.4)

Realistic Flashscore-like tennis match structure (participant names, rank badges,
form W/L strips, tournament header, surface, H2H) plus Firecrawl markdown and
XHR JSON. Not full production minified SPA dumps.

### Operator re-capture

```text
python run_nt.py research match-intel --match "Arnaldi Matteo vs Musetti Lorenzo" ^
  --sport tennis --allow-network --force --json

# Save under live/tennis/{match_key}/ :
#   summary.html, h2h.html (optional), summary.md, xhr/*.json
```

### Patterns for `tennis_live.py`

| Field | Signals |
|-------|---------|
| Identity | `duelParticipant__home/away`, `participant__participantName` |
| Competition | breadcrumb / `tournamentHeader`, title `\|` segment |
| form_or_rank | form W/L badges **or** `participant__participantRank` / `#N` / Rank: N |
| surface | `data-surface`, Clay/Hard/Grass → `competition.format` |
| H2H | `h2h__row` rows; markdown `## H2H` |

### Fixtures

| Dir | Purpose |
|-----|---------|
| `arnaldi_vs_musetti/` | Golden ATP Hamburg — grade ≥ **B** (form + rank + competition) |
| `sinner_vs_medvedev/` | Second competition (ATP Finals) — grade ≥ **C** |
| `empty_shell.html` | JS shell → grade **F** / parse_empty |
