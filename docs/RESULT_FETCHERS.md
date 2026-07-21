# Multi-sport result fetchers

## Architecture

```
nt/results_fetch.py          ← thin facade (backward compatible)
nt/fetchers/
  base.py                    ← ResultFetcher ABC, MatchResult, FetchSuggestion
  http.py / names.py         ← shared utilities
  markets.py                 ← selection → win/loss mapping
  football.py                ← ESPN leagues + TheSportsDB
  tennis.py                  ← ESPN ATP/WTA + TheSportsDB
  basketball.py              ← ESPN NBA/WNBA
  handball.py                ← TheSportsDB best-effort
  darts.py                   ← stub (manual until source wired)
  registry.py                ← sport → fetcher + suggest_results_for_pending
```

### Adding a sport

1. Create `nt/fetchers/<sport>.py` with a `ResultFetcher` subclass.
2. Implement `fetch_match` + `evaluate_selection` (reuse `markets.py` helpers).
3. Register instance in `registry.py` `_FETCHERS` list.
4. Done — `settle --draft` and LuminaNT Smart settle pick it up automatically.

## CLI

```bash
python run_nt.py settle --list-fetchers
python run_nt.py settle --draft              # auto-fetch all pending
python run_nt.py settle --draft --no-fetch   # skip network
```

## Sources (current)

| Sport | Primary | Fallback |
|-------|---------|----------|
| Football | ESPN scoreboards (many leagues) | TheSportsDB search + livescore |
| Tennis | ESPN ATP/WTA scoreboard | TheSportsDB |
| Basketball | ESPN NBA/WNBA | — |
| Handball | TheSportsDB | — |
| Darts | *(not wired)* | manual |

## Confidence / UX

Each suggestion includes:

- `fetcher` — module used
- `source` — concrete endpoint label
- `confidence` — outcome map × name match
- `match_confidence` — team/player name similarity
- `needs_manual` — true if uncertain / unfinished
- `auto_fetch_ok` — high-confidence ready to include

Never invents results: failed fetch → clear reason → manual input.
