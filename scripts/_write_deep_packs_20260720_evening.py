#!/usr/bin/env python3
"""Deep evidence packs — 2026-07-20 KO window 16:00–20:16 CEST."""
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
TODAY = "2026-07-20"

SRC = lambda url, take, kind="stats": {
    "url": url,
    "takeaway": take,
    "kind": kind,
    "accessed_at": TODAY,
}

PACKS: list[dict] = [
    {
        "match": "Örgryte IS vs Djurgården IF",
        "selection": "BTTS Ja",
        "sport": "Football",
        "league": "Allsvenskan",
        "p_model": 0.70,
        "summary": (
            "Allsvenskan 19:00. NT Djurgården heavy fav ML ~1.35; BTTS Ja @1.60. "
            "Public models ~70-76% BTTS Yes: Örgryte all home games BTTS season trend, "
            "Djurgården score+concede away often; last-6 O2.5 cluster for DIF. "
            "Script high_scoring / open game. Honest p 0.68-0.72; use 0.70. "
            "After 5% haircut EV ≈ (0.65)*1.60−1 ≈ +0.04."
        ),
        "failure_modes": "Cagey 0-1; Djurgården clean sheet + late winner; red card low event.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": (
            "Domestic league midweek/evening; expected near full strength both sides. "
            "No confirmed mass rotation flag in research window; monitor XI ~1h pre-KO."
        ),
        "script_lean": "high_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            SRC("https://www.mightytips.com/football-predictions/orgryte-vs-djurgarden-prediction-20-07-2026/", "BTTS main lean; Örgryte home BTTS 6/6; DIF scored 10/11."),
            SRC("https://www.sportytrader.com/en/betting-tips/orgryte-is-djurgardens-if-359811/", "DIF O1.5 team goals lean; Örgryte leaky."),
            SRC("https://www.betshoot.com/football/19635948-%C3%96rgryte-vs-Djurg%C3%A5rden-prediction/", "O2.5 lean open game."),
            SRC("https://footballwhispers.com/blog/orgryte-is-vs-djurgardens-if-prediction-20-07-2026/", "1-3 style score lean; goals market."),
            SRC("https://www.forebet.com", "DIF ~52% win; high-scoring projection."),
            SRC("https://www.sofascore.com", "Form/ratings Allsvenskan."),
            SRC("https://fbref.com", "Shooting/xG context Allsvenskan."),
            SRC("https://www.transfermarkt.com", "Squads/injuries domestic league.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT BTTS Ja 1.60; Djurgården ML 1.35.", "odds"),
        ],
    },
    {
        "match": "Örgryte IS vs Djurgården IF",
        "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
        "sport": "Football",
        "league": "Allsvenskan",
        "p_model": 0.62,
        "summary": (
            "O2.5 @1.40 is short. Models ~55-65% O2.5; need ~0.79 for clean EV at 1.40. "
            "Honest 0.62 — reject chalk total; prefer BTTS Ja @1.60 with better price."
        ),
        "failure_modes": "1-0 or 0-1 low total.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Same XI context as BTTS pack; domestic league.",
        "script_lean": "high_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.betshoot.com", "O2.5 tip ~1.44 market."),
            SRC("https://www.mightytips.com", "Goal-heavy narrative."),
            SRC("https://footballwhispers.com", "High-scoring recent form."),
            SRC("https://www.forebet.com", "3-1 projection."),
            SRC("https://www.sofascore.com", "Form."),
            SRC("https://www.transfermarkt.com", "Squads.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT O2.5 1.40.", "odds"),
        ],
    },
    {
        "match": "IFK Mariehamn vs FC Lahti",
        "selection": "Vinner: FC Lahti",
        "sport": "Football",
        "league": "Veikkausliiga",
        "p_model": 0.58,
        "summary": (
            "Lahti NT fav ~1.47; Mariehamn in long losing streak / poor home scoring. "
            "Models 40-63% away win — wide range. Fair p ~0.55-0.60. "
            "Need ~0.75 after haircut for EV at 1.47. Honest 0.58 — reject chalk ML."
        ),
        "failure_modes": "Mariehamn shock home point; 0-0.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Veikkausliiga evening; expected competitive XIs; no mass-rest flag.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.mightytips.com/football-predictions/ifk-mariehamn-vs-fc-lahti-prediction-20-07-2026/", "Lahti lean low-scoring 1-0."),
            SRC("https://www.forebet.com/en/football/matches/ifk-mariehamn-fc-lahti-2448645", "Lahti ~40% algorithm."),
            SRC("https://www.rowdie.co.uk/match/ifk-mariehamn-fc-lahti-2026-07-20/", "DC Lahti/draw."),
            SRC("https://www.sofascore.com", "Form tables."),
            SRC("https://fbref.com", "Veikkausliiga shooting."),
            SRC("https://www.transfermarkt.com", "Injuries/squads.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Lahti 1.47 Mariehamn 5.20.", "odds"),
        ],
    },
    {
        "match": "IFK Mariehamn vs FC Lahti",
        "selection": "Totalt antall mål - over/under 2.5: Under 2.5",
        "sport": "Football",
        "league": "Veikkausliiga",
        "p_model": 0.56,
        "summary": (
            "Mariehamn toothless home (multi-match scoreless trend in previews) vs Lahti "
            "recent clean sheets narrative. Mixed: some models U2.5, others O2.5/BTTS. "
            "NT U2.5 @1.95. Honest p 0.54-0.58; use 0.56. After haircut EV ≈ (0.51)*1.95−1 ≈ −0.005 — borderline fail."
        ),
        "failure_modes": "Lahti blowout 0-3; both score open game.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Domestic; expected starters; fitness notes thin mid-table Finnish league.",
        "script_lean": "low_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.mightytips.com", "Low-scoring tactical 1-0 lean."),
            SRC("https://oddspedia.com", "U2.5 model lean noted."),
            SRC("https://www.forebet.com", "Low event projection."),
            SRC("https://www.sofascore.com", "Form."),
            SRC("https://fbref.com", "Goals for/against."),
            SRC("https://www.transfermarkt.com", "Squads.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT U2.5 1.95.", "odds"),
        ],
    },
    {
        "match": "IFK Mariehamn vs FC Lahti",
        "selection": "BTTS Nei",
        "sport": "Football",
        "league": "Veikkausliiga",
        "p_model": 0.58,
        "summary": (
            "Mariehamn failed to score multiple home matches; Lahti clean-sheet form. "
            "BTTS Nei @1.82. Honest p 0.55-0.60. Need ~0.62 for standard EV — thin fail/borderline. "
            "Document; prefer stronger EV football (Örgryte BTTS Ja) first."
        ),
        "failure_modes": "Mariehamn consolation goal; open 2-1.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Domestic league; expected XIs.",
        "script_lean": "low_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.mightytips.com", "Mariehamn scoreless home trend."),
            SRC("https://www.rowdie.co.uk", "Low goals expectation."),
            SRC("https://www.sofascore.com", "Form."),
            SRC("https://fbref.com", "Scoring rates."),
            SRC("https://www.transfermarkt.com", "Squads.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT BTTS Nei 1.82.", "odds"),
            SRC("https://www.flashscore.com", "H2H listing."),
        ],
    },
    {
        "match": "Kalmar vs Malmö FF",
        "selection": "Totalt antall mål - over/under 2.5: Under 2.5",
        "sport": "Football",
        "league": "Allsvenskan",
        "p_model": 0.54,
        "summary": (
            "Even Allsvenskan (Kalmar ~2.60 Malmö ~2.45). H2H often under 3 goals; "
            "some tips U2.5 / Kalmar home edge. NT U2.5 @2.10. Honest p 0.52-0.56. "
            "After haircut EV thin; use 0.54 — borderline fail standard min EV."
        ),
        "failure_modes": "Open 2-2; Malmö multi-goal win.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Allsvenskan evening; both expected competitive XIs; check late injuries.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://footballwhispers.com/blog/kalmar-vs-malmo-prediction-20-07-2026/", "1-1 lean; U2.5 H2H note."),
            SRC("https://www.sportsgambler.com", "Kalmar AH home lean."),
            SRC("https://scores24.live", "Kalmar under 1.5 goals H2H trend."),
            SRC("https://fbref.com", "Allsvenskan xG."),
            SRC("https://www.sofascore.com", "Form."),
            SRC("https://www.transfermarkt.com", "Squads/injuries.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT U2.5 2.10; ML even.", "odds"),
        ],
    },
    {
        "match": "Kalmar vs Malmö FF",
        "selection": "BTTS Ja",
        "sport": "Football",
        "league": "Allsvenskan",
        "p_model": 0.60,
        "summary": (
            "BTTS Ja @1.50. Models ~60-67%. Need ~0.72 for EV at 1.50. Honest 0.60 — fail chalk BTTS."
        ),
        "failure_modes": "Clean sheet either side.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Domestic; expected starters.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://footballwhispers.com", "Even match preview."),
            SRC("https://www.sportsgambler.com", "Home competitive."),
            SRC("https://fbref.com", "xG."),
            SRC("https://www.sofascore.com", "Form."),
            SRC("https://www.transfermarkt.com", "Squads.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT BTTS Ja 1.50.", "odds"),
            SRC("https://www.flashscore.com", "H2H."),
        ],
    },
    {
        "match": "Kalmar vs Malmö FF",
        "selection": "Handikap 3-veis 1:0: Kalmar 1:0",
        "sport": "Football",
        "league": "Allsvenskan",
        "p_model": 0.58,
        "summary": (
            "Kalmar +1 three-way HC @1.50 on near-even match. Covers most non-blowout-away results. "
            "Honest p ~0.55-0.62. Need ~0.72 at 1.50 — fail. Document reject soft HC price."
        ),
        "failure_modes": "Malmö win by 2+.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Domestic; expected XIs.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.sportsgambler.com", "Kalmar home AH lean."),
            SRC("https://footballwhispers.com", "Even 1-1 lean."),
            SRC("https://fbref.com", "Form."),
            SRC("https://www.sofascore.com", "Ratings."),
            SRC("https://www.transfermarkt.com", "Squads.", "injury"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Kalmar 1:0 HC 1.50.", "odds"),
            SRC("https://www.flashscore.com", "Listing."),
        ],
    },
    {
        "match": "Bondar, Anna vs Uchijima, Moyuka",
        "selection": "1. Sett - Game handikap -2.5: Uchijima, Moyuka +2.5",
        "sport": "Tennis",
        "league": "WTA",
        "p_model": 0.70,
        "summary": (
            "Bondar NT fav ~1.30. Uchijima set1 +2.5 games @1.52 — dog set-game cover unless Bondar bags set1 by 3+. "
            "Process tennis dog HC (Bouzas process hit). Honest p 0.68-0.72. "
            "Need ~0.73 for standard EV at 1.52 — borderline; explore path may pass with tennis learn boost."
        ),
        "failure_modes": "Bondar 6-1 set1; retirement.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected to start WTA board 17:20; no injury flag in window.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.wtatennis.com", "Rankings form."),
            SRC("https://www.tennisexplorer.com", "H2H/form."),
            SRC("https://www.sofascore.com", "Ratings."),
            SRC("https://www.flashscore.com", "Listing."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Uchijima set1 +2.5 @1.52; Bondar ML 1.30.", "odds"),
            SRC("https://www.oddsportal.com", "Market fav Bondar.", "odds"),
            SRC("https://www.sofascore.com/tennis", "Live listing fitness."),
        ],
    },
    {
        "match": "Bondar, Anna vs Uchijima, Moyuka",
        "selection": "Game handikap -4.5: Uchijima, Moyuka +4.5",
        "sport": "Tennis",
        "league": "WTA",
        "p_model": 0.66,
        "summary": (
            "Match games +4.5 underdog @1.87. Wider cover than set1 line. Honest ~0.64-0.68. "
            "EV after haircut at 1.87 ≈ (0.61)*1.87−1 ≈ +0.14 if p holds — strong tennis dog HC explore."
        ),
        "failure_modes": "Bondar straight-sets bagel; retirement.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected; WTA 17:20 KO.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.wtatennis.com", "Form."),
            SRC("https://www.tennisexplorer.com", "H2H."),
            SRC("https://www.sofascore.com", "Ratings."),
            SRC("https://www.flashscore.com", "Listing."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Uchijima +4.5 games @1.87.", "odds"),
            SRC("https://www.oddsportal.com", "Market.", "odds"),
            SRC("https://www.sofascore.com/tennis", "Fitness listing."),
        ],
    },
    {
        "match": "Day, Ryan vs Hugill, Ashley",
        "selection": "Parti handikap -2.5: Hugill, Ashley +2.5",
        "sport": "Snooker",
        "league": "Pro ranking",
        "p_model": 0.68,
        "summary": (
            "Day fav NT 1.32; Hugill +2.5 frames @1.60. Wide dog frame HC covers unless Day wins by 3+. "
            "Snooker dog HC explore. Honest p 0.66-0.70. After haircut EV ≈ (0.63)*1.60−1 ≈ +0.01 — explore bar."
        ),
        "failure_modes": "Day 4-0/4-1 demolition.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Both listed 20:00; expected to play.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.wst.tv", "Tour context."),
            SRC("https://cuetracker.net", "Results histories."),
            SRC("https://www.sofascore.com", "Listing."),
            SRC("https://www.flashscore.com", "Fixtures."),
            SRC("https://www.snooker.org", "Rankings."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Hugill +2.5 @1.60 Day ML 1.32.", "odds"),
        ],
    },
    {
        "match": "Donaldson, Scott vs Xinbo, Wang",
        "selection": "Parti handikap 1.5: Donaldson, Scott +1.5",
        "sport": "Snooker",
        "league": "Pro ranking",
        "p_model": 0.66,
        "summary": (
            "Xinbo NT fav 1.55; Donaldson +1.5 frames @1.70. Dog frame cover. Honest ~0.64-0.68. "
            "EV after haircut ≈ (0.61)*1.70−1 ≈ +0.04."
        ),
        "failure_modes": "Xinbo 4-0/4-1.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Both listed 20:00.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.wst.tv", "Tour."),
            SRC("https://cuetracker.net", "Form."),
            SRC("https://www.sofascore.com", "Listing."),
            SRC("https://www.flashscore.com", "Fixtures."),
            SRC("https://www.snooker.org", "Rankings."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Donaldson +1.5 @1.70.", "odds"),
        ],
    },
    {
        "match": "Robertson, Jimmy vs Chenzhi, Gong",
        "selection": "Parti handikap -2.5: Chenzhi, Gong +2.5",
        "sport": "Snooker",
        "league": "Pro ranking",
        "p_model": 0.68,
        "summary": (
            "Robertson fav 1.30; Gong +2.5 @1.62. Wide dog HC. Honest 0.66-0.70. Explore snooker HC."
        ),
        "failure_modes": "Robertson whitewash.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Both listed 20:00.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.wst.tv", "Tour."),
            SRC("https://cuetracker.net", "Form."),
            SRC("https://www.sofascore.com", "Listing."),
            SRC("https://www.flashscore.com", "Fixtures."),
            SRC("https://www.snooker.org", "Rankings."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Gong +2.5 @1.62.", "odds"),
        ],
    },
    {
        "match": "Smith, Ross vs Doets, Kevin",
        "selection": "Runde handikap 2.5: Smith, Ross +2.5",
        "sport": "Darts",
        "league": "PDC World Matchplay",
        "p_model": 0.68,
        "summary": (
            "Matchplay R32 BO19. Doets slight fav 1.77 / Smith 1.95. Smith +2.5 legs @1.40 is short. "
            "Need ~0.79 for EV. Honest p for +2.5 in BO19 ~0.65-0.72 even for slight dog. Use 0.68 — fail EV at 1.40."
        ),
        "failure_modes": "Doets thrashing 10-4 style.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected World Matchplay R32 20:15.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.sportytrader.com/en/betting-tips/ross-smith-kevin-doets-359967/", "Over legs lean; Doets slight fav."),
            SRC("https://www.pdc.tv", "Matchplay listing."),
            SRC("https://www.flashscore.com", "Darts page."),
            SRC("https://www.sofascore.com", "Listing."),
            SRC("https://www.dartsrankings.com", "Averages form."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Smith +2.5 @1.40 Doets ML 1.77.", "odds"),
        ],
    },
    {
        "match": "Smith, Ross vs Doets, Kevin",
        "selection": "Totalt antall runder 16.5: Over 16.5",
        "sport": "Darts",
        "league": "PDC World Matchplay",
        "p_model": 0.58,
        "summary": (
            "O16.5 legs @1.77 in BO19 (first to 10). Competitive pricing suggests long match. "
            "Honest p 0.55-0.60. Need ~0.63 for EV — borderline fail. Prefer not force darts totals without avg edge."
        ),
        "failure_modes": "Straight-sets style 10-3.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Matchplay R32 expected.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.sportytrader.com", "O15.5 legs tip theme."),
            SRC("https://www.pdc.tv", "Format BO19."),
            SRC("https://www.flashscore.com", "Listing."),
            SRC("https://www.sofascore.com", "Form."),
            SRC("https://www.dartsrankings.com", "Averages."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT O16.5 1.77.", "odds"),
        ],
    },
    {
        "match": "Rocha, Henrique vs Martinez, Pedro",
        "selection": "Game handikap -0.5: Martinez, Pedro +0.5",
        "sport": "Tennis",
        "league": "ATP",
        "p_model": 0.55,
        "summary": (
            "Near-coin ML (Rocha 1.72 Martinez 1.92). Martinez +0.5 games @1.87 ≈ underdog games. "
            "Honest ~0.52-0.58. Thin EV; use 0.55 fail unless explore boost large."
        ),
        "failure_modes": "Rocha straight-sets control.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected 17:20.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.atptour.com", "Rankings."),
            SRC("https://www.tennisexplorer.com", "Form."),
            SRC("https://www.sofascore.com", "Ratings."),
            SRC("https://www.flashscore.com", "Listing."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT near even ML.", "odds"),
            SRC("https://www.oddsportal.com", "Market.", "odds"),
        ],
    },
]


def main() -> None:
    cs = parse_odds_file(ROOT / "inbox" / "current_odds_01.txt")
    by = {(c.match, c.selection): c for c in cs}
    n = 0
    for pack in PACKS:
        key = (pack["match"], pack["selection"])
        c = by.get(key)
        if c is None:
            # fuzzy
            hits = [
                x
                for x in cs
                if x.match == pack["match"]
                and (
                    pack["selection"] == x.selection
                    or pack["selection"] in x.selection
                    or x.selection in pack["selection"]
                )
            ]
            if len(hits) == 1:
                c = hits[0]
                pack["selection"] = c.selection
            else:
                # try BTTS / Under renames
                print("MISS", key, "hits", len(hits))
                for h in hits[:5]:
                    print("  ", repr(h.selection))
                ek = f"{pack['match']}_{pack['selection']}"
                path = evidence_path(EV, ek)
                path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                n += 1
                continue
        path = evidence_path(EV, c.evidence_key or f"{c.match}_{c.selection}")
        path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        n += 1
        print(f"OK {c.decimal_odds:5.2f} p={pack['p_model']:.2f} {c.selection[:55]}")
    print(f"Wrote {n} packs")


if __name__ == "__main__":
    main()
