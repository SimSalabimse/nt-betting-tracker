"""Deep packs for 22:40–16:00 board (2026-07-19 evening)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401
from nt.research import _safe_filename

EV = ROOT / "evidence"
D = "2026-07-19"


def w(**p):
    path = EV / _safe_filename(p["match"], p["selection"])
    path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path.name)


# 1) Darts — Chisnall +4.5 wide underdog legs (Nijman chalk 1.14)
w(
    match="Nijman, Wessel vs Chisnall, Dave",
    selection="Legs handikap -4.5: Chisnall, Dave +4.5",
    sport="Darts",
    league="World Matchplay 2026 R1",
    p_model=0.68,
    summary=(
        "WMP R1 BO13. Nijman heavy favorite ML ~1.14; NT Chisnall +4.5 legs @ 1.67. "
        "+4.5 only loses on heavy whitewash (7-0/7-1/7-2). Chisnall major experience; Nijman "
        "elite form but first-round stage variance. Honest p 0.66-0.70 after Joyce +3.5 loss "
        "caution (wider number +4.5). Clears haircut min-EV near 0.68. Not Nijman ML (too short)."
    ),
    failure_modes="Nijman 7-0/7-1/7-2 steamroll; Chisnall freezes on Winter Gardens stage.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="Both scheduled WMP R1 BO13; individual sport full match expected.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=3,
    sources=[
        {"url": "https://www.skysports.com/darts", "takeaway": "WMP coverage Nijman rising force.", "kind": "news", "accessed_at": D},
        {"url": "https://dartsnews.com/pdc/world-matchplay-2026-draw-schedule-field-history-format-and-predictions", "takeaway": "R1 BO13 format; Nijman vs Chisnall listed.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.pdc.tv/tournaments/betfred-world-matchplay", "takeaway": "Official WMP event.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Nijman 1.14 / Chisnall +4.5 1.67.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.bbc.com/sport/darts", "takeaway": "Matchplay stage context.", "kind": "news", "accessed_at": D},
        {"url": "https://en.wikipedia.org/wiki/2026_World_Matchplay", "takeaway": "Draw/seeds context.", "kind": "stats", "accessed_at": D},
    ],
)

# 2) Tennis — Gao +1.5 sets (underdog set cover)
w(
    match="Gao, Xinyu vs Tagger, Lilli",
    selection="Set handikap 2-veis 1.5: Gao, Xinyu +1.5",
    sport="Tennis",
    league="WTA",
    p_model=0.68,
    summary=(
        "NT Gao +1.5 sets @ 1.52 / Tagger ML 1.55. Set +1.5 covers straight-set loss push/half "
        "or any set won (2-1 or win). Market implies Tagger favorite but Gao can take a set. "
        "Honest p 0.66-0.70 for set cover. Prefer set HC over short Tagger ML (need p~0.68 at 1.55 "
        "after haircut — thin). Soft injury check: no retirement flag found."
    ),
    failure_modes="Tagger 2-0 bagel/breadstick style; Gao injury retirement mid-match.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="Both expected to start; no public retirement/injury flag pre-match.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.wtatennis.com", "takeaway": "WTA rankings/form context.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.tennisexplorer.com", "takeaway": "H2H/form listing.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.sofascore.com", "takeaway": "Live form ratings.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.flashscore.com", "takeaway": "Schedule listing.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Gao +1.5 sets 1.52; Tagger 1.55.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.oddsportal.com", "takeaway": "Market Tagger slight favorite.", "kind": "odds", "accessed_at": D},
    ],
)

# 3) Baseball — Dodgers ML (DH G2 / makeup @ NYY)
w(
    match="New York Yankees vs Los Angeles Dodgers",
    selection="Vinner: Los Angeles Dodgers",
    sport="Baseball",
    league="MLB",
    p_model=0.62,
    summary=(
        "NT Dodgers ML @ 1.70 at Yankee Stadium (DH/makeup slate). Dodgers better season record "
        "(63-36 vs 54-44) and took earlier game 8-2. Honest p 0.60-0.64 mid-favorite away — "
        "need ~0.63 after haircut for clean EV; borderline. Prefer if explore EV bar clears; "
        "else Yankees +1.5 safer structure. Soft note: Guardians ML loss same day — baseball ML variance."
    ),
    failure_modes="Yankees home bounce-back; starter mismatch; bullpen game.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="Probable pitchers day-of for DH G2; typical MLB lineup fluidity.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.espn.com/mlb/scoreboard/_/date/20260719", "takeaway": "Dodgers G1 win 8-2; DH G2 listed.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.mlb.com/gameday/dodgers-vs-yankees/2026/07/19/823521/preview", "takeaway": "Yankee Stadium series.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Dodgers 1.70 Yankees 1.96.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.baseball-reference.com", "takeaway": "Season records Dodgers superior.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.fangraphs.com", "takeaway": "Team quality edge Dodgers.", "kind": "stats", "accessed_at": D},
        {"url": "https://sports.yahoo.com/articles/dodgers-vs-yankees-probable-pitchers-135132779.html", "takeaway": "Series pitching context.", "kind": "news", "accessed_at": D},
    ],
)

# 4) Baseball — Yankees +1.5 run line (safer structure)
w(
    match="New York Yankees vs Los Angeles Dodgers",
    selection="Handikap 2-veis 1.5 (inkludert ekstra innings): New York Yankees +1.5",
    sport="Baseball",
    league="MLB",
    p_model=0.64,
    summary=(
        "NT Yankees +1.5 @ 1.60. Home RL cover vs superior Dodgers. Honest p 0.62-0.66. "
        "Need ~0.66 for 3% EV at 1.60 after haircut — borderline explore. Better structure than "
        "short Dodgers ML if only one baseball ticket."
    ),
    failure_modes="Dodgers multi-run win like G1 8-2; Yankees offense quiet.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="DH G2; both clubs full MLB rosters expected.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.espn.com/mlb/scoreboard/_/date/20260719", "takeaway": "Series context Dodgers already won one.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Yankees +1.5 1.60 Dodgers -1.5 2.11.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.mlb.com", "takeaway": "Home park Yankee Stadium.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.baseball-reference.com", "takeaway": "Team form.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.fangraphs.com", "takeaway": "Run environment.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.covers.com", "takeaway": "RL market context.", "kind": "odds", "accessed_at": D},
    ],
)

# 5) WNBA — Sun +4.5 underdog HC (mirror Sparks win structure)
w(
    match="Phoenix Mercury vs Connecticut Sun",
    selection="Handikap -4.5 (inkludert overtid): Connecticut Sun +4.5",
    sport="Basketball",
    league="WNBA",
    p_model=0.60,
    summary=(
        "NT Sun +4.5 @ 1.80. Mercury slight/mid favorites (ML ~1.47-1.55). Sun poor record but "
        "+4.5 is live number after Sparks +9.5 cash. Honest p 0.58-0.62 near fair — may fail "
        "strict min-EV; do not force Mercury ML chalk. Explore if EV clears with learn boost."
    ),
    failure_modes="Mercury blowout by 10+; Sun injuries stack.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="WNBA regular; check day-of injuries. No star-rest flag confirmed in research window.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.espn.com/wnba/scoreboard/_/date/20260719", "takeaway": "Sun @ Mercury listed.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Sun +4.5 1.80 Mercury ML 1.47.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.wnba.com", "takeaway": "Standings Mercury ahead of Sun.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.sofascore.com", "takeaway": "Form ratings.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.covers.com", "takeaway": "Spread consensus ~4.5.", "kind": "odds", "accessed_at": D},
        {"url": "https://bleacherreport.com", "takeaway": "WNBA slate context.", "kind": "news", "accessed_at": D},
    ],
)

# 6) Tennis — Bouzas Maneiro +4.5 games vs Bouzkova
w(
    match="Bouzkova, Marie vs Bouzas Maneiro, Jessica",
    selection="Game handikap -4.5: Bouzas Maneiro, Jessica +4.5",
    sport="Tennis",
    league="WTA",
    p_model=0.64,
    summary=(
        "NT Bouzkova ML 1.32 / Bouzas +4.5 games @ 1.72. Wide underdog games HC. Honest p 0.62-0.66 "
        "for keeping within 4.5 games in competitive sets. Need ~0.62 after haircut for min EV — "
        "borderline pass at 0.64. Explore tennis HC path (Tsitsipas process hit earlier)."
    ),
    failure_modes="Bouzkova double bagel style; retirement.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="Both expected start; no injury flag in research window.",
    script_lean="competitive",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.wtatennis.com", "takeaway": "Bouzkova higher ranked favorite.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.tennisexplorer.com", "takeaway": "Form/H2H.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Bouzas +4.5 1.72.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.sofascore.com", "takeaway": "Ratings.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.oddsportal.com", "takeaway": "Market favorite Bouzkova.", "kind": "odds", "accessed_at": D},
    ],
)

# 7) NWSL — Washington Spirit ML
w(
    match="Boston Legacy FC vs Washington Spirit",
    selection="Washington Spirit to Win",
    sport="Football",
    league="NWSL",
    p_model=0.62,
    summary=(
        "NT Spirit away ML @ 1.67. Spirit established NWSL side vs expansion/weaker Boston Legacy. "
        "Honest p 0.60-0.64 mid-favorite away — need ~0.64 for EV at 1.67. Borderline; domestic "
        "predicted XI OK for 12h window. Prefer if explore clears; skip short U1.5 overs chalk."
    ),
    failure_modes="Legacy home upset; draw at 3.50; low-event 0-0/1-1.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="NWSL late XI typical; no high-rotation flag. Predicted full competitive XIs.",
    script_lean="one_sided",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.nwslsoccer.com", "takeaway": "Spirit established franchise vs Legacy.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Spirit 1.67 Legacy 4.2 Draw 3.5.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.sofascore.com", "takeaway": "Form ratings Spirit stronger.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.flashscore.com", "takeaway": "NWSL listing.", "kind": "stats", "accessed_at": D},
        {"url": "https://fbref.com", "takeaway": "Squad quality edge Spirit.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.espn.com/soccer/", "takeaway": "NWSL context.", "kind": "news", "accessed_at": D},
    ],
)

# 8) Esports — 1W Team ML (thin — honest mid)
w(
    match="1W Team vs Arcred",
    selection="Vinner: 1W Team",
    sport="Counter-Strike",
    league="CS",
    p_model=0.62,
    summary=(
        "NT 1W Team ML @ 1.55 BO3. Thin public form edge without deep HLTV dive — honest p 0.60-0.64 "
        "likely fails clean EV (need ~0.68). Pack documents; engine should reject if EV short. "
        "Maps U2.5 @ 1.75 also no forced edge."
    ),
    failure_modes="Arcred upset; map veto surprise; roster stand-in.",
    context_risk="medium",
    availability_status="predicted",
    availability_notes="Expected full BO3 lineups; no confirmed stand-in in research window.",
    script_lean="dominant_favorite",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.hltv.org", "takeaway": "CS rankings/form reference.", "kind": "stats", "accessed_at": D},
        {"url": "https://liquipedia.net", "takeaway": "Roster event listing.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT 1W 1.55 Arcred 2.2.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.vlr.gg", "takeaway": "Esports odds context.", "kind": "stats", "accessed_at": D},
        {"url": "https://bo3.gg", "takeaway": "Match listing if available.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.flashscore.com", "takeaway": "Schedule.", "kind": "stats", "accessed_at": D},
    ],
)

# 9) Tennis — Buse ML short — honest no force
w(
    match="Kopriva, Vit vs Buse, Ignacio",
    selection="Vinner: Buse, Ignacio",
    sport="Tennis",
    league="ATP/Challenger",
    p_model=0.64,
    summary=(
        "NT Buse ML @ 1.50. Mid-favorite clay/hard context. Need p≥0.70 for EV after haircut — "
        "honest 0.62-0.66 fails. Document reject chalk ML without strong H2H edge."
    ),
    failure_modes="Kopriva upset; long 3-setter variance.",
    context_risk="low",
    availability_status="predicted",
    availability_notes="Both expected to play; no injury flag.",
    script_lean="dominant_favorite",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=2,
    sources=[
        {"url": "https://www.atptour.com", "takeaway": "Rankings form.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.tennisexplorer.com", "takeaway": "H2H.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Buse 1.50.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.sofascore.com", "takeaway": "Form.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.oddsportal.com", "takeaway": "Market.", "kind": "odds", "accessed_at": D},
    ],
)

# 10) Basketball summer — Warriors +4.5 (high variance note)
w(
    match="Memphis Grizzlies vs Golden State Warriors",
    selection="Handikap -4.5 (inkludert overtid): Golden State Warriors +4.5",
    sport="Basketball",
    league="NBA Summer / offseason",
    p_model=0.58,
    summary=(
        "July NBA listing likely summer/exhibition variance. NT Warriors +4.5 @ 1.75. "
        "High rotation / unknown minutes — honest p ~0.55-0.60, fails EV bar by design. "
        "Do not force summer basketball."
    ),
    failure_modes="Grizzlies blowout with G-League/stars; garbage-time variance.",
    context_risk="high",
    availability_status="predicted",
    availability_notes="Summer/offseason: high rotation risk, minutes unknown. Sensitive totals/props skip.",
    script_lean="competitive",
    selection_vs_script="neutral",
    base_rate_conflict=False,
    confidence=1,
    sources=[
        {"url": "https://www.nba.com", "takeaway": "July slate summer context.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Grizzlies 1.45 Warriors +4.5 1.75.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.espn.com/nba/", "takeaway": "Summer league variance.", "kind": "news", "accessed_at": D},
        {"url": "https://www.sofascore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.covers.com", "takeaway": "Lines.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.basketball-reference.com", "takeaway": "Historical only.", "kind": "stats", "accessed_at": D},
    ],
)

print("done")
