# Football live capture fixtures (PR-3)

## Capture recipe (§2.5.3)

These fixtures are **realistic structure captures** of Flashscore-like match pages
(class names, JSON-LD, form widgets, standings table, H2H rows) plus a Firecrawl-style
markdown twin. They are **not** full production minified SPA dumps.

### Operator re-capture (when Firecrawl / Playwright available)

```text
# 1. Resolve URL (PR-2 discovery or --url)
python run_nt.py research match-intel --match "Rosenborg vs Fredrikstad" ^
  --sport football --allow-network --force --json

# 2. With FIRECRAWL_API_KEY set, router scrapes markdown+html.
#    Save under live/football/{match_key}/ :
#      summary.html   — main match page after wait
#      h2h.html       — optional H2H tab snapshot
#      summary.md     — Firecrawl markdown
#      xhr/*.json     — filtered XHR (form/standings/h2h)
# 3. Redact cookies / tracking; keep participant names, form, table text.
# 4. Unit tests must stay offline (load fixtures only).
```

### Patterns documented for extractors (`flashscore_live.py`)

| Field | HTML / markdown signals |
|-------|-------------------------|
| Identity | `duelParticipant__home/away`, `participant__participantName`, `<title>Home vs Away \| Comp` |
| Competition | breadcrumb / `tournamentHeader`, title segment after `\|` |
| Form | `form__home` / `form__away`, `wld` / `formIcon` badges, `Home form: W D W L W` in markdown |
| Standings | `tableCellRank` / `table__cell--rank`, `Rank: N` near team, points |
| H2H | `h2h__row` / `h2h__entity`, score + date rows; markdown `## H2H` |
| JSON-LD | `SportsEvent` + `homeTeam` / `awayTeam` / `superEvent` |
| XHR | `{home:{form,rank,points}, away:{…}, tournament, h2h:[]}` shapes |

### Fixtures

| Dir | Purpose |
|-----|---------|
| `rosenborg_vs_fredrikstad/` | Golden Eliteserien card — target grade ≥ **B** (n_miss 0) |
| `barcelona_sc_vs_ldu_quito/` | Second competition (Liga Pro) — grade ≥ **C** |

### Smoke (optional, network)

```text
set FIRECRAWL_API_KEY=...
python run_nt.py research match-intel --match "Rosenborg vs Fredrikstad" ^
  --sport football --allow-network --force --url "https://www.flashscore.com/match/..." --json
# Expect: among matched football, grade ≥ C when scrape returns form widgets
```
