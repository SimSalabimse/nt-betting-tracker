# Best Sources & Data Integration

Practical, high-quality sources for Norsk Tipping Oddsen research. Prefer **official stats DBs and injury/lineup sites** over social media as primary evidence.

## Football (Fotball) — including Eliteserien

| Priority | Source | Best for | Notes |
|----------|--------|----------|-------|
| 1 | [FBref](https://fbref.com) | xG, form, shooting, historical | Primary stats DB |
| 1 | [Transfermarkt](https://www.transfermarkt.com) | Injuries, suspensions, squads | Confirm absences |
| 1 | [Sofascore](https://www.sofascore.com) | Form, ratings, lineups | Pre-match lineup |
| 1 | [Flashscore](https://www.flashscore.com) | H2H, schedules, scores | Fast context |
| 2 | [Understat](https://understat.com) | Shot quality / xG (selected leagues) | Not all Nordic coverage |
| 2 | [WhoScored](https://www.whoscored.com) | Ratings, event trends | Supplement |
| 2 | [SoccerSTATS](https://www.soccerstats.com) | BTTS / O/U tables | Quick filters |
| 2 | OddsPortal / odds history | Line movement | Soft signal only |
| 1 | NFF / Eliteserien official | Fixtures, news | Competition context |
| 3 | Club sites / trusted local media | Late team news | Verify with Transfermarkt |

### Eliteserien research checklist (bookmark this)

- [ ] Table position + motivation (title / Europe / relegation / mid)
- [ ] Last 5–8 results + xG if available (FBref)
- [ ] Key injuries / suspensions (Transfermarkt)
- [ ] Predicted or confirmed lineup (Sofascore)
- [ ] H2H last 3–5 meetings (Flashscore)
- [ ] Home/away split relevant to market
- [ ] Weather / pitch only if material (cup replays, coastal wind)
- [ ] Failure modes written *before* p_model locked

## Other sports (summary)

| Sport | Tier-1 sources |
|-------|----------------|
| Tennis | TennisExplorer, ATP/WTA, Sofascore/Flashscore |
| Ice hockey | Hockey-Reference, Eliteprospects, Sofascore |
| Handball | Sofascore/Flashscore, EHF/IHF, Handball.ai |
| Esports (CS) | HLTV, Liquipedia |
| Esports (Dota) | OpenDota, Dotabuff, Liquipedia |
| Snooker | CueTracker, Snooker.org, Flashscore |
| Darts | PDC, Darts Orakel, Flashscore |
| Baseball | Baseball-Reference, Fangraphs, MLB.com |
| Basketball | Basketball-Reference, official NBA, Sofascore |
| F1 / Golf | Official tour sites + Flashscore |

Full historical notes: `history/legacy_docs/nt_sports_data_sources.md` (reference only — not control-plane).

## How to integrate with this OS

1. **Evidence JSON** — every source is a `{url, takeaway}` (optional `kind`, `accessed_at`).
2. **p_model** — set in evidence or odds CSV; never invent post-hoc after seeing results.
3. **CLI**

```bash
python run_nt.py research sources --sport football
python run_nt.py research checklist --sport football
python run_nt.py research scaffold --match "..." --selection "..." --p-model 0.55
```

4. **Legal / ToS** — use public pages manually or official APIs if you add them later. This repo does **not** ship scrapers that violate site terms. Helpers only scaffold files and print checklists.

## Importing model probabilities

### Via odds CSV

```csv
date,match,selection,decimal_odds,sport,market_type,p_model,notes
2026-07-20,Bodø/Glimt vs Brann,Bodø/Glimt to Win,1.55,football,Match result,0.68,model_v1
```

### Via evidence pack

```json
{
  "p_model": 0.68,
  "model_name": "manual_v1",
  "model_version": "2026-07",
  "summary": "..."
}
```

### Via agent assist (optional)

```bash
python run_nt.py agent ask "Given this evidence pack path, critique p_model calibration risks"
```

Agent may suggest a range; **you** write the final p_model into evidence.

## Bookmarks folder template

```
NT/
  Eliteserien_FBref
  Eliteserien_Transfermarkt
  Sofascore_Football
  Flashscore_Today
  Injuries_News
  NT_Oddsen (operator)
```
