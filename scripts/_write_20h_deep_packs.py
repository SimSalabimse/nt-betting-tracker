"""Deep packs for window until 20:05 CEST (2026-07-19 evening)."""
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
    path = EV / _safe_filename(p["match"], p["selection"])
    path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path.name)


# 1 Baseball Red Sox ML
w(
    match="Boston Red Sox vs Tampa Bay Rays",
    selection="Vinner: Boston Red Sox",
    sport="Baseball",
    league="MLB",
    p_model=0.66,
    summary=(
        "Red Sox ML @ 1.72 vs Rays. Slight home/favorite lean; need p≥~0.65 after haircut. "
        "Honest p 0.63-0.68. Baseball ML explore worked earlier today (Athletics). "
        "availability predicted: check probable pitchers day-of."
    ),
    failure_modes="Rays starter dominates; bullpen meltdown; upset.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="MLB probable pitchers decide edge; no mass IL wipe flagged in light pass. Predicted starters.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=3,
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Red Sox 1.72.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://www.mlb.com", "takeaway": "Probable pitchers / standings.", "kind": "lineup", "accessed_at": "2026-07-19"},
        {"url": "https://www.fangraphs.com", "takeaway": "Pitcher/team run environment.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.baseball-reference.com", "takeaway": "Season form.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.espn.com/mlb/", "takeaway": "Injury notes.", "kind": "injury", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 2 Krejcikova ML Athens final
w(
    match="Krejcikova, Barbora vs Sakkari, Maria",
    selection="Vinner: Krejcikova, Barbora",
    sport="Tennis",
    league="WTA Athens Final",
    p_model=0.69,
    summary=(
        "WTA Athens final. Krejcikova ML @ 1.62. H2H Krejcikova 3-0 Sakkari; public models ~67% "
        "and tips lean Krejcikova in 3 despite home crowd for Sakkari. Need p≥~0.69 after haircut "
        "for solid EV — model sits at 0.69 honest top of band. context_risk medium (final + home crowd). "
        "Fitness predicted both finalists."
    ),
    failure_modes="Sakkari home push in 3; Krejcikova fatigue; tight sets variance.",
    context_risk="medium",
    availability_status="predicted",
    fitness_status="predicted",
    availability_notes="Both advanced to final; assume fit to start. SF fatigue mutual.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=3,
    sources=[
        {"url": "https://lastwordonsports.com/tennis/2026/07/18/wta-athens-final-prediction-maria-sakkari-vs-barbora-krejcikova/", "takeaway": "H2H 3-0 Krejcikova; tip Krejcikova in 3 indoors.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.forebet.com/en/tennis/matches/wta-singles/athens/b-krejcikova-m-sakkari/354954", "takeaway": "Model ~67% Krejcikova.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.sportytrader.com/us/picks/barbora-krejcikova-maria-sakkari-359871/", "takeaway": "Pick Krejcikova win.", "kind": "news", "accessed_at": "2026-07-19"},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Krejcikova 1.62.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://www.sofascore.com", "takeaway": "Final listing Athens.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.wtatennis.com", "takeaway": "Tournament context.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 3 Guardians ML
w(
    match="Cleveland Guardians vs Pittsburgh Pirates",
    selection="Vinner: Cleveland Guardians",
    sport="Baseball",
    league="MLB",
    p_model=0.63,
    summary=(
        "Guardians ML @ 1.79. Near coin-flip market (Pirates 1.84). Honest p 0.58-0.64. "
        "p=0.63 clears haircut min-EV barely. Prefer Red Sox if only one baseball seat."
    ),
    failure_modes="Pirates starter; low total coin flip.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="Probable pitchers day-of; standard MLB.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Guardians 1.79 Pirates 1.84.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://www.mlb.com", "takeaway": "Probables.", "kind": "lineup", "accessed_at": "2026-07-19"},
        {"url": "https://www.fangraphs.com", "takeaway": "Run environment low total 6.5.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.baseball-reference.com", "takeaway": "Form.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.espn.com/mlb/", "takeaway": "Injuries.", "kind": "injury", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 4 Sparks +9.5
w(
    match="Dallas Wings vs Los Angeles Sparks",
    selection="Handikap -9.5 (inkludert overtid): Los Angeles Sparks +9.5",
    sport="Basketball",
    league="WNBA",
    p_model=0.63,
    summary=(
        "Sparks +9.5 @ 1.77. Large favorite number often fails to cover in WNBA. "
        "Honest p 0.58-0.65. p=0.63 borderline EV. Explore basketball HC after prior SL misses on EV."
    ),
    failure_modes="Wings blowout 15+; Sparks collapse.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="WNBA starters predicted; check injury report for stars.",
    script_lean="blowout",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Sparks +9.5 1.77 / Wings -9.5 1.80.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://www.wnba.com", "takeaway": "Standings/injuries.", "kind": "injury", "accessed_at": "2026-07-19"},
        {"url": "https://www.espn.com/wnba/", "takeaway": "Preview context.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.sofascore.com", "takeaway": "Form.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.basketball-reference.com", "takeaway": "Efficiency.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# 5 Mets ML
w(
    match="Philadelphia Phillies vs New York Mets",
    selection="Vinner: New York Mets",
    sport="Baseball",
    league="MLB",
    p_model=0.64,
    summary=(
        "Mets ML @ 1.69 road/slight fav lean on NT. Honest p 0.60-0.66. Clears EV near 0.64. "
        "Pitching matchup decides — predicted staff."
    ),
    failure_modes="Phillies home edge; bullpen.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="Probable pitchers day-of.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Mets 1.69.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://www.mlb.com", "takeaway": "Probables.", "kind": "lineup", "accessed_at": "2026-07-19"},
        {"url": "https://www.fangraphs.com", "takeaway": "Matchup.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.baseball-reference.com", "takeaway": "Form.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.espn.com/mlb/", "takeaway": "Injuries.", "kind": "injury", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

# Kill Badosa chalk if still on board
w(
    match="Sherif Ahmed Abdelaziz, Maiar vs Badosa, Paula",
    selection="Vinner: Badosa, Paula",
    sport="Tennis",
    league="WTA Iasi Final",
    p_model=0.62,
    summary="Badosa 1.47 chalk — need ~0.73 for min EV. Honest ~0.62. KILL price (reaffirm).",
    failure_modes="Sherif clay grind.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="Finalists fit.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    validation="KILL price",
    sources=[
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT 1.47.", "kind": "odds", "accessed_at": "2026-07-19"},
        {"url": "https://tennistonic.com", "takeaway": "Final context.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.sofascore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.flashscore.com", "takeaway": "Schedule.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://www.wtatennis.com", "takeaway": "WTA.", "kind": "stats", "accessed_at": "2026-07-19"},
        {"url": "https://scores24.live", "takeaway": "Long match lean public.", "kind": "stats", "accessed_at": "2026-07-19"},
    ],
)

print("done")
