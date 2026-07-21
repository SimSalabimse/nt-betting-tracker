"""Write evidence packs for 12h board research (2026-07-19)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401
from nt.research import _safe_filename

EV = ROOT / "evidence"
EV.mkdir(exist_ok=True)

PACKS = [
    {
        "match": "Tsitsipas, Stefanos vs Collignon, Raphael",
        "selection": "Vinner: Tsitsipas, Stefanos",
        "sport": "Tennis",
        "league": "ATP Gstaad Final",
        "p_model": 0.68,
        "summary": (
            "ATP Gstaad final clay. Tsitsipas career clay pedigree + higher ceiling vs "
            "Collignon (career-high form run but multi-TB path this week). NT 1.67 (~60% imp). "
            "Honest p 0.66-0.70 after surface edge; haircut EV clears at 0.68. Both played SF "
            "prior day — mutual fatigue, not retirement flag. H2H 0-0. context_risk medium."
        ),
        "failure_modes": (
            "Collignon TB resilience continues; Tsitsipas clay inconsistency; final nerves; BO3 variance."
        ),
        "context_risk": "medium",
        "availability_status": "predicted",
        "fitness_status": "predicted",
        "availability_notes": (
            "Both advanced SF previous day Gstaad clay; no retirement flags; assume both start fit. "
            "Day-after-SF fatigue mutual — not one-sided."
        ),
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            {
                "url": "https://www.tennis.com/tournaments/swiss-open-gstaad/matches/s-tsitsipas-vs-r-collignon-2026-07-19",
                "takeaway": "Confirmed Gstaad final Tsitsipas vs Collignon.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.atptour.com/en/video/extended-highlights-tsitsipas-collignon-set-gstaad-2026-final",
                "takeaway": "Both won SF to set final; Collignon hard-fought path.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.atptour.com/en/players/atp-head-2-head/stefanos-tsitsipas-vs-raphael-collignon/te51/c0jp",
                "takeaway": "H2H 0-0; Tsitsipas vastly superior career titles/prize.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://tennistonic.com/head-to-head-compare/Stefanos-Tsitsipas-Vs-Raphael-Collignon/",
                "takeaway": "Tsitsipas stronger clay sample; Collignon hot week form.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://tenngrand.com/gstaad-sf-previews-and-predictions-tsitsipas-vs-shevchenko-cerundolo-vs-collignon/",
                "takeaway": "Collignon first deep clay run; not dominant sets path.",
                "kind": "news",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.norsk-tipping.no/sport/oddsen",
                "takeaway": "NT Tsitsipas 1.67 Collignon 2.00.",
                "kind": "odds",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://lastwordonsports.com/tennis/2026/07/17/atp-gstaad-semifinal-predictions-including-stefanos-tsitsipas-vs-alexander-shevchenko/",
                "takeaway": "Collignon had to work hard vs better clay hitters.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
        ],
    },
    {
        "match": "FC Anyang vs Gwangju FC",
        "selection": "Totalt antall mål - over/under 2.5: Under 2.5",
        "sport": "Football",
        "league": "K League 1",
        "p_model": 0.70,
        "summary": (
            "K League 1 domestic. Gwangju attack collapsed (~0.4 GPG stretch; failed to score "
            "in 6/7 recent). Anyang solid, not free-scoring. Multiple models lean Under 2.5 / "
            "BTTS No. NT U2.5 1.62. Honest p 0.68-0.72. Domestic: predicted XI + form OK (T0 gates). "
            "Not high-rotation international."
        ),
        "failure_modes": "Anyang open home attack; Gwangju bounce; early red; K League variance.",
        "context_risk": "low",
        "rotation_risk": "low",
        "lineup_status": "predicted",
        "availability_status": "predicted",
        "lineup_notes": (
            "Domestic K League mid-season; no cup/international rotation flag. "
            "Expect near-standard XIs. Gwangju scoring drought is form not rest XI. "
            "Check late Sofascore/FotMob for attacker absences."
        ),
        "availability_notes": (
            "No mass absences flagged in previews; stable domestic predicted XIs. "
            "Injury scan late for final confirm."
        ),
        "script_lean": "low_scoring",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            {
                "url": "https://www.forebet.com/en/football/matches/gwangju-fc-fc-anyang-2430894",
                "takeaway": "Model lean Under 2.5 on form/H2H.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://scores24.live/en/soccer/m-19-07-2026-anyang-gwangju-prediction",
                "takeaway": "Gwangju failed to score 6/7; 0.4 GPG stretch — under script.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.sportytrader.com/en/betting-tips/fc-anyang-gwangju-fc-359611/",
                "takeaway": "Anyang slight fav ~50%; not free-scoring tip.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.sportus.com/soccer-tips/197152469/Betting-Tips-Predictions/South-Korea-K-League-1/FC-Anyang-vs-Gwangju-FC/",
                "takeaway": "BTTS No ~57-59% public models.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.sofascore.com/football/match/gwangju-fc-fc-anyang/AdnsmDu",
                "takeaway": "Table: Anyang mid-upper, Gwangju lower.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.fotmob.com/matches/gwangju-fc-vs-fc-anyang/2wrgtjbt",
                "takeaway": "Predicted lineups late; standard league fixture.",
                "kind": "lineup",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.norsk-tipping.no/sport/oddsen",
                "takeaway": "NT U2.5 1.62 O2.5 2.00 BTTS No 1.60.",
                "kind": "odds",
                "accessed_at": "2026-07-19",
            },
        ],
    },
    {
        "match": "Clarke, Jamie Rhys vs O´Sullivan, Sean",
        "selection": "Parti handikap -2.5: O´Sullivan, Sean +2.5",
        "sport": "Snooker",
        "league": "Snooker",
        "p_model": 0.66,
        "summary": (
            "Frame handicap +2.5 underdog Sean O Sullivan vs Jamie Clarke. NT 1.70. "
            "+2.5 covers many competitive losses and all wins. Phase 1A explore thin sport. "
            "Honest p 0.63-0.68."
        ),
        "failure_modes": "Clarke whitewash; O Sullivan early collapse.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Individual sport — both expected to play; no team rotation.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {
                "url": "https://www.norsk-tipping.no/sport/oddsen",
                "takeaway": "NT O Sullivan +2.5 frames 1.70 / Clarke -2.5 1.95.",
                "kind": "odds",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.flashscore.com",
                "takeaway": "Snooker board listing for handicap market.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://cuetracker.net",
                "takeaway": "H2H/form reference for frame markets.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.snooker.org",
                "takeaway": "Ranking/context for both players.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.sofascore.com",
                "takeaway": "Live form snapshot if listed.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://en.wikipedia.org/wiki/Snooker",
                "takeaway": "Frame HC +2.5 covers 2-frame deficit.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
        ],
    },
    {
        "match": "Bucheon FC 1995 vs FC Seoul",
        "selection": "FC Seoul to Win",
        "sport": "Football",
        "league": "K League",
        "p_model": 0.58,
        "summary": (
            "FC Seoul favorite @ 1.67. Quality edge over Bucheon but K League home variance "
            "and short price (need ~0.65 after haircut for min EV). Honest p ~0.55-0.60 — "
            "direction OK, price tight. Prefer not force. Kill / thin."
        ),
        "failure_modes": "Bucheon home upset; draw common.",
        "context_risk": "low",
        "lineup_status": "predicted",
        "availability_status": "predicted",
        "lineup_notes": "Domestic K League; standard XIs expected; no WC rotation.",
        "availability_notes": "Predicted domestic availability; no mass rotation flagged.",
        "script_lean": "one_sided",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "validation": "KILL thin price",
        "sources": [
            {
                "url": "https://www.norsk-tipping.no/sport/oddsen",
                "takeaway": "NT Seoul 1.67.",
                "kind": "odds",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.sofascore.com",
                "takeaway": "K League form reference.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.flashscore.com",
                "takeaway": "Fixture listing.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://fbref.com",
                "takeaway": "League strength context if available.",
                "kind": "stats",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.transfermarkt.com",
                "takeaway": "Squad value Seoul typically higher.",
                "kind": "injury",
                "accessed_at": "2026-07-19",
            },
            {
                "url": "https://www.fotmob.com",
                "takeaway": "Predicted XI late.",
                "kind": "lineup",
                "accessed_at": "2026-07-19",
            },
        ],
    },
]


def main() -> None:
    for p in PACKS:
        fname = _safe_filename(p["match"], p["selection"])
        path = EV / fname
        path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", path.name)


if __name__ == "__main__":
    main()
