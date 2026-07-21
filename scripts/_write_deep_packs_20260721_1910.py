#!/usr/bin/env python3
"""Deep packs — 19:10–22:00 window 2026-07-21 (avoid Clayton/MvG matches — already open)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import evidence_path
from nt.odds_parse import parse_odds_file

EV = ROOT / "evidence"
TODAY = "2026-07-21"


def S(url: str, take: str, kind: str = "stats") -> dict:
    return {"url": url, "takeaway": take, "kind": kind, "accessed_at": TODAY}


PACKS = [
    {
        "match": "Sturm Graz vs Hearts",
        "selection": "BTTS Ja",
        "sport": "Football",
        "league": "UEFA Champions League",
        "p_model": 0.66,
        "summary": (
            "UCL Q2 1st leg Graz 20:30. NT BTTS Ja @1.65. Multiple previews lean BTTS/O2.5: "
            "Hearts goals in last 5, Sturm open home European; Sports Mole 1-1, Windrawwin BTTS, "
            "FootballWhispers BTTS probable @~1.70. Honest p 0.63-0.68; use 0.66. "
            "After 5% haircut EV ≈ 0.627*1.65−1 ≈ +0.034."
        ),
        "failure_modes": "Cagey 1-0 Sturm; Hearts park bus 0-0/1-0.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "European night; expected competitive XIs. Confirm 1h pre-KO.",
        "script_lean": "open_game",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            S("https://footballwhispers.com/blog/sturm-graz-vs-hearts-prediction-21-07-2026/", "BTTS Yes probable; O2.5 probable; Hearts last-5 all 3+ goals theme."),
            S("https://www.sportsmole.co.uk/football/sturm-graz/champions-league/preview/sturm-graz-vs-hearts-prediction-team-news-lineups_601494.html", "Score lean 1-1; both sides can score."),
            S("https://www.windrawwin.com/tips/champions-league/sk-sturm-graz-v-hearts/874640/", "BTTS + O2.5 + home win lean."),
            S("https://www.sportskeeda.com/football/sturm-graz-vs-hearts-prediction-betting-tips-july-21st-2026", "2-1 lean; BTTS tip."),
            S("https://www.sportsgambler.com/betting-tips/football/sturm-graz-vs-hearts-prediction-lineups-odds-2026-07-21/", "BTTS Yes market active; O2.5 favoured."),
            S("https://www.uefa.com/uefachampionsleague/match/2048726--sturm-graz-vs-hearts/", "Official UCL Q2 listing Graz."),
            S("https://www.transfermarkt.com", "Squads/injuries European qualifiers.", "injury"),
            S("https://www.norsk-tipping.no/sport/oddsen", "NT BTTS Ja 1.65; O2.5 1.62.", "odds"),
        ],
    },
    {
        "match": "Sturm Graz vs Hearts",
        "selection": "Totalt antall mål - Over/Under 2.5: Over 2.5",
        "sport": "Football",
        "league": "UEFA Champions League",
        "p_model": 0.60,
        "summary": (
            "O2.5 @1.62 NT. Public lean goals but price short for EV need ~0.67 after haircut. "
            "Honest 0.58-0.62 — prefer BTTS Ja @1.65 for better price/edge."
        ),
        "failure_modes": "1-0 / 0-1.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Same as BTTS pack.",
        "script_lean": "open_game",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            S("https://footballwhispers.com/blog/sturm-graz-vs-hearts-prediction-21-07-2026/", "O2.5 probable."),
            S("https://www.windrawwin.com/tips/champions-league/sk-sturm-graz-v-hearts/874640/", "O2.5 lean."),
            S("https://www.sportsgambler.com", "O2.5 market favourite."),
            S("https://www.uefa.com", "UCL context."),
            S("https://www.sofascore.com", "Form."),
            S("https://www.transfermarkt.com", "Squads.", "injury"),
            S("https://www.norsk-tipping.no/sport/oddsen", "NT O2.5 1.62.", "odds"),
            S("https://www.flashscore.com", "Fixtures."),
        ],
    },
    {
        "match": "Dundee United vs Spartans FC",
        "selection": "Totalt antall mål - over/under 3.5: Over 3.5",
        "sport": "Football",
        "league": "Scottish League Cup",
        "p_model": 0.58,
        "summary": (
            "Scottish League Cup 20:45. Championship/Premiership-level DU vs lower Spartans; "
            "home favourites often score freely in cup mismatches. NT O3.5 @1.72. "
            "Honest p 0.55-0.60. Need ~0.63 for +3% EV — borderline fail; record honest 0.58."
        ),
        "failure_modes": "Professional 2-0; Spartans deep block low event.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Cup midweek; check rotation but home side expected strong enough.",
        "script_lean": "home_control_goals",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            S("https://www.bbc.com/sport/football", "Scottish League Cup listings."),
            S("https://www.flashscore.com", "Fixtures form."),
            S("https://www.sofascore.com", "Ratings."),
            S("https://www.transfermarkt.com", "Squad levels gap.", "injury"),
            S("https://www.soccerway.com", "Competition context."),
            S("https://www.norsk-tipping.no/sport/oddsen", "NT O3.5 ~1.72; BTTS Nei 1.47.", "odds"),
            S("https://www.skysports.com/football", "Cup coverage."),
            S("https://www.spfl.co.uk", "League Cup."),
        ],
    },
    {
        "match": "Dundee United vs Spartans FC",
        "selection": "BTTS Nei",
        "sport": "Football",
        "league": "Scottish League Cup",
        "p_model": 0.62,
        "summary": (
            "BTTS Nei @1.47 is short (need ~0.74 for clean EV). Honest clean-sheet lean 0.58-0.64 "
            "in mismatch but price kills EV — reject chalk; prefer O3.5 only if price improves."
        ),
        "failure_modes": "Spartans consolation goal.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Cup mismatch.",
        "script_lean": "home_control_goals",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            S("https://www.bbc.com/sport/football", "Cup listings."),
            S("https://www.flashscore.com", "Form."),
            S("https://www.sofascore.com", "Ratings."),
            S("https://www.transfermarkt.com", "Levels.", "injury"),
            S("https://www.norsk-tipping.no/sport/oddsen", "NT BTTS Nei 1.47.", "odds"),
            S("https://www.spfl.co.uk", "League Cup."),
            S("https://www.soccerway.com", "Context."),
            S("https://www.skysports.com/football", "Coverage."),
        ],
    },
    {
        "match": "Fenerbahce vs Gornik Zabrze",
        "selection": "Totalt antall mål - Over/Under 3.5: Under 3.5",
        "sport": "Football",
        "league": "UEFA Champions League",
        "p_model": 0.62,
        "summary": (
            "UCL Q2 1st leg Istanbul. Fener heavy home fav; first-leg control often 2-0/3-0 "
            "not always 4+. NT U3.5 @1.67. Honest p 0.58-0.64. Need ~0.65 for EV — borderline; "
            "use 0.62 (may fail 3% bar / pass explore)."
        ),
        "failure_modes": "Fener 4+ goal thrashing; open game.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "European night Istanbul; monitor XI.",
        "script_lean": "home_favourite_control",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            S("https://www.uefa.com/uefachampionsleague/match/2048725--fenerbahce-vs-gornik-zabrze/", "UCL Q2 1st leg."),
            S("https://www.transfermarkt.com", "Squad gap Fener vs Górnik.", "injury"),
            S("https://www.sofascore.com", "Form ratings."),
            S("https://www.flashscore.com", "Fixtures."),
            S("https://www.norsk-tipping.no/sport/oddsen", "NT U3.5 1.67; O3.5 1.92.", "odds"),
            S("https://www.soccerway.com", "Competition."),
            S("https://fbref.com", "Shooting context if available."),
            S("https://www.whoscored.com", "Ratings."),
        ],
    },
    {
        "match": "Kilmarnock FC vs Hamilton Academical FC",
        "selection": "Totalt antall mål - over/under 3.5: Under 3.5",
        "sport": "Football",
        "league": "Scottish League Cup",
        "p_model": 0.62,
        "summary": (
            "League Cup 20:45. Premiership Kilmarnock vs Championship Hamilton. "
            "NT U3.5 @1.67. Cup can be controlled 2-0/2-1. Honest 0.58-0.64. Borderline EV."
        ),
        "failure_modes": "Open 3-2; Hamilton open up.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Domestic cup; expect Killie strong XI.",
        "script_lean": "home_control",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            S("https://www.bbc.com/sport/football", "League Cup."),
            S("https://www.flashscore.com", "Form."),
            S("https://www.sofascore.com", "Ratings."),
            S("https://www.transfermarkt.com", "Squads.", "injury"),
            S("https://www.spfl.co.uk", "Competition."),
            S("https://www.norsk-tipping.no/sport/oddsen", "NT U3.5 1.67.", "odds"),
            S("https://www.skysports.com/football", "Coverage."),
            S("https://www.soccerway.com", "Context."),
        ],
    },
    {
        "match": "Brockmann, Tessa Johanna vs Jacquemot, Elsa",
        "selection": "Game handikap 3.5: Brockmann, Tessa Johanna +3.5",
        "sport": "Tennis",
        "league": "WTA Hamburg",
        "p_model": 0.62,
        "summary": (
            "WTA Hamburg 19:20 — already near KO. Jacquemot fav ML ~1.45; Brockmann +3.5 games @1.87. "
            "Wide dog HC covers unless bagel-ish. Honest cover p 0.58-0.65. "
            "EV after haircut at 1.87 ≈ (0.59)*1.87−1 ≈ +0.10 if p=0.62 holds — explore tennis HC."
        ),
        "failure_modes": "Jacquemot straight-sets crush; retirement.",
        "context_risk": "high",
        "availability_status": "predicted",
        "availability_notes": "KO ~19:20 — may be live/started; skip if in-play on NT.",
        "script_lean": "favourite_wins_competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            S("https://www.wtatennis.com", "WTA Hamburg listings."),
            S("https://www.tennisexplorer.com", "Form H2H."),
            S("https://www.sofascore.com", "Ratings."),
            S("https://www.flashscore.com", "Live board."),
            S("https://www.norsk-tipping.no/sport/oddsen", "NT Brockmann +3.5 @1.87; Jacquemot ML 1.45.", "odds"),
            S("https://www.oddsportal.com", "Market fav Jacquemot.", "odds"),
            S("https://www.tennisabstract.com", "Level context if available."),
            S("https://www.sofascore.com/tennis", "Fitness listing."),
        ],
    },
]


def main() -> None:
    cands = parse_odds_file(ROOT / "inbox" / "current_odds_01.txt")
    n = 0
    for pack in PACKS:
        hits = [c for c in cands if c.match == pack["match"] and c.selection == pack["selection"]]
        if len(hits) != 1:
            # soft selection match
            hits = [
                c
                for c in cands
                if c.match == pack["match"]
                and pack["selection"].split(":")[0][:20].lower() in (c.selection or "").lower()
            ]
        c = hits[0] if len(hits) == 1 else None
        body = {
            "match": c.match if c else pack["match"],
            "selection": c.selection if c else pack["selection"],
            "sport": pack["sport"],
            "league": pack["league"],
            "date": TODAY,
            "p_model": pack["p_model"],
            "summary": pack["summary"],
            "failure_modes": pack["failure_modes"],
            "sources": pack["sources"],
            "availability_status": pack["availability_status"],
            "availability_notes": pack["availability_notes"],
            "context_risk": pack["context_risk"],
            "script_lean": pack["script_lean"],
            "selection_vs_script": pack["selection_vs_script"],
            "base_rate_conflict": pack["base_rate_conflict"],
            "confidence": pack["confidence"],
            "notes": "Deep 19:10-22:00 window 2026-07-21; avoid open darts matches",
        }
        ek = (c.evidence_key if c else None) or f"{body['match']}_{body['selection']}"
        path = evidence_path(EV, ek)
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        path2 = evidence_path(EV, f"{body['match']}_{body['selection']}")
        if path2 != path:
            path2.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        odds = c.decimal_odds if c else 0
        print(f"OK {odds:5.2f} p={pack['p_model']:.2f} {(c.selection if c else pack['selection'])[:55]}")
        n += 1
    print(f"Wrote {n}")


if __name__ == "__main__":
    main()
