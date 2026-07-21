"""Deep packs for 3h window deep queue (2026-07-19)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401
from nt.research import _safe_filename

EV = ROOT / "evidence"


def w(**p):
    fname = _safe_filename(p["match"], p["selection"])
    path = EV / fname
    path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path.name)


# 1) MvG -2.5 World Matchplay R1
w(
    match="van Gerwen, Michael vs Gilding, Andrew",
    selection="Legs handikap -2.5: van Gerwen, Michael -2.5",
    sport="Darts",
    league="World Matchplay 2026 R1",
    p_model=0.63,
    summary=(
        "World Matchplay first round BO13 (first to 7). MvG seed vs Andrew Gilding. "
        "NT MvG -2.5 legs @ 1.85. Quality/experience edge on Blackpool stage; -2.5 is 2-leg cover "
        "(e.g. 7-4 or better). Honest p 0.60-0.65 after Matchplay variance. Clears haircut min-EV "
        "near 0.63. context_risk medium (major first round)."
    ),
    failure_modes="Gilding hot scoring; MvG slow start; 7-5 tight scoreline loses -2.5.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="Both expected to play full BO13; individual sport; no rotation.",
    script_lean="dominant_favorite",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=3,
    sources=[
        {"url": "https://www.bbc.com/sport/darts/articles/c93204p8y4eo", "takeaway": "WMP draw: MvG vs Gilding first round.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.skysports.com/darts/news/12288/13561989/betfred-world-matchplay-2026-luke-littler-faces-niko-springer-luke-humphries-takes-on-cameron-menzies-as-draw-confirmed", "takeaway": "Gilding described in-form; still underdog vs MvG.", "kind": "news", "accessed_at": "2026-07-19"},
        {"url": "https://en.wikipedia.org/wiki/2026_World_Matchplay", "takeaway": "Field/seeds; MvG ranked elite.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://dartsnews.com/pdc/world-matchplay-2026-draw-schedule-field-history-format-and-predictions", "takeaway": "BO13 first round format.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT MvG -2.5 1.85.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://oche180.com/match/1080028", "takeaway": "Match listing WMP.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 2) Joyce +3.5 underdog legs (Anderson favorite)
w(
    match="Anderson, Gary vs Joyce, Ryan",
    selection="Legs handikap -3.5: Joyce, Ryan +3.5",
    sport="Darts",
    league="World Matchplay 2026 R1",
    p_model=0.64,
    summary=(
        "WMP R1 Anderson vs Joyce. Joyce +3.5 legs @ 1.87. Large number on underdog in BO13 — "
        "covers many competitive losses (e.g. 7-4, 7-5). Honest p 0.60-0.66. Explore path; "
        "recent Cullen +2.5 loss is caution but +3.5 is wider. Not pure longshot ML."
    ),
    failure_modes="Anderson whitewash 7-1/7-2; Joyce freezes on stage.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="Both scheduled WMP R1; full match expected.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.bbc.com/sport/darts/articles/c93204p8y4eo", "takeaway": "Anderson (12) vs Joyce R1.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://en.wikipedia.org/wiki/2026_World_Matchplay", "takeaway": "Seed structure.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Joyce +3.5 1.87 / Anderson -3.5 1.85.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://dartsnews.com/pdc/world-matchplay-2026-draw-schedule-field-history-format-and-predictions", "takeaway": "R1 BO13.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.skysports.com/darts", "takeaway": "Matchplay coverage context.", "kind": "news", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 3) Heathcote ML snooker
w(
    match="Heathcote, Louis vs Xinbo, Wang",
    selection="Vinner: Heathcote, Louis",
    sport="Snooker",
    league="Snooker",
    p_model=0.65,
    summary=(
        "Heathcote ML @ 1.70 vs Xinbo Wang. Slight favorite; need p≥~0.63 after haircut. "
        "Honest p 0.62-0.67 mid-favorite. Explore snooker ML after O'Sullivan HC loss — ML structure cleaner."
    ),
    failure_modes="Xinbo upset; frame variance; poor safety battle.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="Individual sport; both expected to play.",
    script_lean="dominant_favorite",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Heathcote 1.70 Xinbo 1.95.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://cuetracker.net", "takeaway": "H2H/form reference.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.snooker.org", "takeaway": "Rankings context.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Fixture listing.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.sofascore.com", "takeaway": "Form if listed.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://en.wikipedia.org/wiki/Snooker", "takeaway": "Match format context.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 4) Kazakov +2.5 frames
w(
    match="Mertens, Ben vs Kazakov, Anton",
    selection="Parti handikap -2.5: Kazakov, Anton +2.5",
    sport="Snooker",
    league="Snooker",
    p_model=0.65,
    summary=(
        "Kazakov +2.5 frames @ 1.62. Underdog with +2.5 cover structure. Honest p 0.62-0.67. "
        "Need p≥~0.69 for strong EV at 1.62 — borderline; p=0.65 thin explore. "
        "Prefer Heathcote ML if only one snooker seat."
    ),
    failure_modes="Mertens whitewash; Kazakov collapses.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="Both expected; individual sport.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Kazakov +2.5 1.62 / Mertens -2.5 2.05.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://cuetracker.net", "takeaway": "Frame H2H/form.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.snooker.org", "takeaway": "Player rankings.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.sofascore.com", "takeaway": "Form snapshot.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://en.wikipedia.org/wiki/Snooker", "takeaway": "+2.5 frame cover structure.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 5) Badosa games U12.5 — public lean over 21.5 match games → under player total fragile
# Kill Badosa ML 1.47 as too short; document thin kill pack for transparency
w(
    match="Sherif Ahmed Abdelaziz, Maiar vs Badosa, Paula",
    selection="Vinner: Badosa, Paula",
    sport="Tennis",
    league="WTA Iasi Final",
    p_model=0.62,
    summary=(
        "WTA Iasi final clay. Badosa ML @ 1.47 is chalk. Models ~63% win — need ~0.73 after haircut "
        "for min EV at 1.47. Honest p 0.60-0.65. Direction OK, **price wrong**. KILL. "
        "Public also lean long match (O21.5 games) — final clay grind."
    ),
    failure_modes="Sherif clay grind steals title in 3.",
    context_risk="medium",
    availability_status="predicted",
    fitness_status="predicted",
    availability_notes="Both finalists fit enough to start; day after SF fatigue mutual.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    validation="KILL on price",
    sources=[
        {"url": "https://tennistonic.com/tennis-news/1028654/h2h-prediction-of-mayar-sherif-vs-paula-badosa-in-iasi-with-odds-preview-pick-19th-july-2026/", "takeaway": "Iasi final; Badosa tip in 3; odds ~1.46.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://scores24.live/en/tennis/m-19-07-2026-sherif-ahmed-abdelaziz-maiar-badosa-paula-prediction", "takeaway": "Editor lean O21.5 games — long final script.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.sportytrader.com/us/picks/mayar-sherif-paula-badosa-gibert-359874/", "takeaway": "Sherif +3.5 games tip; not pure chalk ML edge.", "kind": "news", "accessed_at": "2026-07-19"},
        {"url": "https://www.sportus.com/tennis-tips/198136044/Betting-Tips-Predictions/WTA-Iasi/Mayar-Sherif-vs-Paula-Badosa/", "takeaway": "Badosa ~63% public models.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Badosa 1.47.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://www.sofascore.com/tennis/match/mayar-sherif-paula-badosa/aGCskqK", "takeaway": "Final Iasi listing.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 6) Parivision ML short — kill
w(
    match="BetBoom Team vs Parivision",
    selection="Kart handikap 2-veis 1.5: BetBoom Team +1.5",
    sport="Esports",
    league="Dota 2",
    p_model=0.64,
    summary=(
        "BetBoom +1.5 maps @ 1.60 in series. Underdog map HC. Honest p 0.60-0.66. "
        "Without live form dump, mid explore only."
    ),
    failure_modes="Parivision 2-0 sweep.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="Rosters assumed full; stand-in risk not checked live.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT BetBoom +1.5 1.60 / Parivision -1.5 2.00.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://liquipedia.net", "takeaway": "Roster/event context.", "kind": "lineup", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://bo3.gg", "takeaway": "Map HC structure.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.sofascore.com", "takeaway": "If listed.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.hltv.org", "takeaway": "Cross-esports form habit (CS analog).", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

print("done")
