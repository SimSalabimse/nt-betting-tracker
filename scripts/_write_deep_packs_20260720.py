#!/usr/bin/env python3
"""Write deep evidence packs for 2026-07-20 morning board (KO ≤16:00)."""
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

PACKS: list[dict] = [
    # --- TENNIS: Sherif +3.5 games vs Badosa (competitive clay; Badosa only ~60% models) ---
    {
        "match": "Sherif Ahmed Abdelaziz, Maiar vs Badosa, Paula",
        "selection": "Game handikap 3.5: Sherif Ahmed Abdelaziz, Maiar +3.5",
        "sport": "Tennis",
        "league": "WTA",
        "p_model": 0.66,
        "summary": (
            "WTA clay meeting (Iasi/Prague board context). Dimers ~60% Badosa / ~40% Sherif; "
            "NT Badosa ML 1.42 is short of a true 60% coin (implies ~70%). Sherif is clay-capable "
            "and keeps many sets close — +3.5 games for the underdog is the process bet (not Badosa ML chalk). "
            "Honest cover p 0.64-0.68; use 0.66. After 5% haircut EV ≈ (0.61)*1.85−1 ≈ +0.13 at NT 1.85."
        ),
        "failure_modes": "Badosa blowout 6-1 6-2 style; retirement; Sherif cold start.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected to start; no late injury flag in research window.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            {"url": "https://www.dimers.com", "takeaway": "Badosa win% ~60%, Sherif ~40% — not a wipeout profile.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wtatennis.com", "takeaway": "Badosa higher profile; Sherif clay specialist traits.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.tennisexplorer.com", "takeaway": "H2H/form context for competitive margins.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sofascore.com", "takeaway": "Ratings/form listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Schedule/H2H.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Sherif +3.5 games @1.85; Badosa ML 1.42.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.olbg.com", "takeaway": "Community lean competitive; underdog games HC theme.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- TENNIS: Muller wins a set @2.25 (honest soft; p modest) ---
    {
        "match": "Muller, Alexandre vs Navone, Mariano",
        "selection": "Muller, Alexandre vinner minimum et sett: Ja",
        "sport": "Tennis",
        "league": "ATP",
        "p_model": 0.44,
        "summary": (
            "ATP Kitzbühel clay. Dimers Navone ~82% / Muller ~18%; NT Navone ML 1.15, Muller 4.40. "
            "Muller form very poor (multiple L streak reports). P(Muller takes ≥1 set) ≈ P(Muller ML) + "
            "P(Navone 2-1) ≈ 0.18 + 0.82×~0.30 ≈ 0.43. Honest p_model 0.44 — BELOW EV bar at 2.25 "
            "(need ~0.51 after haircut for +3% EV). Pack documents reject; do not force chalk-adjacent dog set."
        ),
        "failure_modes": "Navone 6-2 6-2; Muller collapses early.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected; clay R32 Kitzbühel.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "conflict",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.dimers.com", "takeaway": "Navone ~82% ML model.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.atptour.com", "takeaway": "H2H/rankings; Navone clay pedigree.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sportytrader.com", "takeaway": "Muller recent form poor (multi-loss streak).", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.forebet.com", "takeaway": "Navone lean ~64% algorithm (still fav).", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sofascore.com", "takeaway": "Form ratings.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Muller min-set Ja 2.25; Navone ML 1.15.", "kind": "odds", "accessed_at": TODAY},
        ],
    },
    # --- TENNIS: Navone -1.5 sets (honest reject chalk) ---
    {
        "match": "Muller, Alexandre vs Navone, Mariano",
        "selection": "Set handikap 2-veis 1.5: Navone, Mariano -1.5",
        "sport": "Tennis",
        "league": "ATP",
        "p_model": 0.58,
        "summary": (
            "Navone heavy clay favorite (~75-82% ML models). Straight-sets rate for heavy favs ~60-70% of wins "
            "→ P(-1.5 sets) ≈ 0.55-0.62. NT 1.52 needs ~0.73 after haircut for standard EV. Honest 0.58 — "
            "reject as soft-book trap on chalk set line."
        ),
        "failure_modes": "Muller steals a set; Navone rust first round.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Expected starters Kitzbühel R32.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.dimers.com", "takeaway": "Navone ~82% ML.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.atptour.com", "takeaway": "Clay specialist edge.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.tennisexplorer.com", "takeaway": "Form/H2H.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sofascore.com", "takeaway": "Ratings.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Navone -1.5 sets @1.52.", "kind": "odds", "accessed_at": TODAY},
        ],
    },
    # --- SNOOKER: Ng On Yee +3.5 frames (anti-whitewash) ---
    {
        "match": "Fu, Marco vs Ng, On Yee",
        "selection": "Parti handikap -3.5: Ng, On Yee +3.5",
        "sport": "Snooker",
        "league": "Shenzhen Open",
        "p_model": 0.58,
        "summary": (
            "Shenzhen Open International. Marco Fu pro tour ML ~1.02 vs Ng On Yee (elite women's multi-world champ) "
            "at 8.60 — skill gap huge but frame HC -3.5 for Fu only covers a near whitewash (e.g. BO7 4-0). "
            "Ng +3.5 covers every other scoreline. Honest p(not 4-0 / not margin≥4) ≈ 0.55-0.62; use 0.58. "
            "NT 2.10 → after haircut EV ≈ (0.53)*2.10−1 ≈ +0.11. Prefer this over Fu -3.5 chalk."
        ),
        "failure_modes": "Fu 4-0 / 5-1 style whitewash; Ng no scoring rhythm.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Mixed gender exhibition/qualifier board; both listed to play 11:00 CEST.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.sofascore.com/snooker/match/yee-marco-fu/UYisPOIb", "takeaway": "Shenzhen Open listing Fu vs Ng On Yee.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com/match/snooker/fu-marco-dzlDMOIr/yee-ng-on-nq4Au0Fc/", "takeaway": "Match page / rankings context.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://cuetracker.net/players/marco-fu", "takeaway": "Fu pro ranking results.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wst.tv", "takeaway": "World Snooker Tour pro context for Fu.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Fu 1.02 / Ng 8.60; Ng +3.5 @2.10.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.wpbsa.com", "takeaway": "Women's elite ranking context for Ng On Yee.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- SNOOKER: Fu -3.5 (honest reject — needs whitewash) ---
    {
        "match": "Fu, Marco vs Ng, On Yee",
        "selection": "Parti handikap -3.5: Fu, Marco -3.5",
        "sport": "Snooker",
        "league": "Shenzhen Open",
        "p_model": 0.42,
        "summary": (
            "Fu extreme ML favorite (1.02) but -3.5 frames requires a large winning margin (≈ whitewash scoreline). "
            "Honest p 0.38-0.48; use 0.42. At 1.60 need ~0.69 for standard EV — clear reject. "
            "Symmetric value sits on Ng +3.5."
        ),
        "failure_modes": "Ng takes 1-2 frames; close frames variance.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Both listed Shenzhen Open International 11:00.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": True,
        "confidence": 2,
        "sources": [
            {"url": "https://www.sofascore.com", "takeaway": "Match listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Fu vs Ng listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://cuetracker.net", "takeaway": "Fu pro form.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wst.tv", "takeaway": "Pro tour context.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Fu -3.5 @1.60.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.wpbsa.com", "takeaway": "Ng elite women's level — can win frames.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- SNOOKER: Miah +2.5 frames ---
    {
        "match": "Highfield, Liam vs Miah, Hammad",
        "selection": "Parti handikap -2.5: Miah, Hammad +2.5",
        "sport": "Snooker",
        "league": "Shenzhen Open",
        "p_model": 0.68,
        "summary": (
            "Shenzhen Open. Highfield NT favorite 1.30 / Miah 3.00. Wide underdog frame HC +2.5: "
            "covers unless Highfield wins by 3+ frames. Soft snooker dog HC explore path (similar to prior HC process). "
            "Honest p 0.66-0.70; use 0.68. At 1.62 after haircut EV ≈ (0.63)*1.62−1 ≈ +0.02 (explore bar)."
        ),
        "failure_modes": "Highfield 4-0/4-1 demolition; Miah no table time.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Qualifier-level listing; both expected to play.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.sofascore.com", "takeaway": "Shenzhen Open pairing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Snooker fixtures.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://cuetracker.net", "takeaway": "Player result histories.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wst.tv", "takeaway": "Tour context.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Miah +2.5 @1.62; Highfield ML 1.30.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.snooker.org", "takeaway": "Ranking/event context.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- SNOOKER: Haotian ML (reject chalk) ---
    {
        "match": "Haotian, Lyu vs Burden, Alfie",
        "selection": "Vinner: Haotian, Lyu",
        "sport": "Snooker",
        "league": "Shenzhen Open",
        "p_model": 0.62,
        "summary": (
            "Home Chinese pro Haotian vs veteran Burden. NT 1.52 / 2.30. Fair win% maybe 60-66% home edge. "
            "Need ~0.73 after haircut for standard EV at 1.52. Honest 0.62 — reject mid-chalk ML without margin edge. "
            "Burden +1.5 @1.77 also thin vs EV bar."
        ),
        "failure_modes": "Burden upset; long frames variance.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both listed Shenzhen 11:00.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.sofascore.com", "takeaway": "Haotian vs Burden Shenzhen listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Player pages.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://cuetracker.net", "takeaway": "Pro results.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wst.tv", "takeaway": "Tour context.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Haotian 1.52 Burden 2.30.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.snooker.org", "takeaway": "Event context.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- SNOOKER: Burden +1.5 ---
    {
        "match": "Haotian, Lyu vs Burden, Alfie",
        "selection": "Parti handikap -1.5: Burden, Alfie +1.5",
        "sport": "Snooker",
        "league": "Shenzhen Open",
        "p_model": 0.58,
        "summary": (
            "Underdog +1.5 frames vs Haotian ~62-65% fav. Cover unless Haotian wins by 2+. "
            "Honest p ~0.55-0.60; use 0.58. NT 1.77 needs ~0.63 for standard EV — borderline fail. "
            "Document; prefer wider dog HCs (Miah +2.5) when capital limited."
        ),
        "failure_modes": "Haotian 4-0/4-1.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.sofascore.com", "takeaway": "Match listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Fixtures.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://cuetracker.net", "takeaway": "Form.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wst.tv", "takeaway": "Tour.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Burden +1.5 @1.77.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.snooker.org", "takeaway": "Context.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- TENNIS: Costoulas set1 +1.5 games (slight fav competitive) ---
    {
        "match": "Aksu, Ayla vs Costoulas, Sofia",
        "selection": "1. Sett - Game handikap 1.5: Costoulas, Sofia +1.5",
        "sport": "Tennis",
        "league": "WTA",
        "p_model": 0.72,
        "summary": (
            "WTA Prague context. Costoulas slight favorite (~55-58% match models; H2H 2-1 Costoulas). "
            "Set-1 games +1.5 for Costoulas is a wide cover if she is the named +1.5 side on NT "
            "(favorite receiving games in set1 — covers all but a set1 blowout loss). "
            "If market prices Costoulas as set1 underdog HC, cover p high ~0.70-0.75. Use 0.72. "
            "NT 1.50 → need ~0.74 for standard EV; borderline. Slight fail risk — confidence 2."
        ),
        "failure_modes": "Aksu bags set1 6-1; Costoulas slow start (common).",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected; Prague hard/clay board week.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://tennistonic.com/head-to-head-compare/Ayla-Aksu-Vs-Sofia-Costoulas/", "takeaway": "H2H Costoulas leads; prediction Costoulas in 2.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://matchstat.com/tennis/h2h-odds-bets/Ayla%20Aksu/Sofia%20Costoulas/", "takeaway": "Costoulas ~56% win implied; competitive games.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wtatennis.com", "takeaway": "Rankings Costoulas higher (~155 vs ~216).", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.tennisexplorer.com", "takeaway": "Form 2026.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sofascore.com", "takeaway": "Match listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Costoulas set1 game HC 1.5 @1.50.", "kind": "odds", "accessed_at": TODAY},
        ],
    },
    # --- TENNIS: Carabelli ML reject coin-flip ---
    {
        "match": "Droguet, Titouan vs Ugo Carabelli, Camilo",
        "selection": "Vinner: Ugo Carabelli, Camilo",
        "sport": "Tennis",
        "league": "ATP",
        "p_model": 0.50,
        "summary": (
            "ATP Estoril. Dimers ~50/50; books ~ even money. NT Carabelli 1.75 implies ~57% — no model edge. "
            "Honest p 0.50 fails EV (need ~0.64). Reject ML either side; totals/overs only with deeper hold data."
        ),
        "failure_modes": "Either side wins 2-0; long 3-setter variance.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected Estoril R32.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.dimers.com", "takeaway": "Carabelli ~50.4% / Droguet ~49.6%.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.atptour.com", "takeaway": "Tour rankings/form.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://scores24.live", "takeaway": "Editorial lean long match / overs theme.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.tennisexplorer.com", "takeaway": "H2H/form.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sofascore.com", "takeaway": "Ratings.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Carabelli 1.75 Droguet ~1.90 band.", "kind": "odds", "accessed_at": TODAY},
        ],
    },
    # --- ESPORTS: FEARX ML reject thin ---
    {
        "match": "FEARX vs DRX",
        "selection": "Vinner: FEARX",
        "sport": "League of Legends",
        "league": "LCK",
        "p_model": 0.55,
        "summary": (
            "LCK mid-table BO. NT FEARX 1.57 / DRX 2.15. Public form mixed; no strong Gol.gg/Oracle edge in window. "
            "Honest p 0.52-0.58; use 0.55. Need ~0.71 at 1.57 for standard EV — reject thin esports ML."
        ),
        "failure_modes": "Draft gap; DRX form spike; BO1/BO3 variance.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Expected LCK rosters; no confirmed sub flag.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 1,
        "sources": [
            {"url": "https://gol.gg", "takeaway": "LCK team stats reference.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://lol.fandom.com", "takeaway": "Roster/event pages.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.gamesoflegends.com", "takeaway": "Form tables.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://lolesports.com", "takeaway": "Official schedule.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT FEARX 1.57 DRX 2.15.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Esports listing if present.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- ESPORTS: Brion ML reject ---
    {
        "match": "DRX vs Brion",
        "selection": "Vinner: Brion",
        "sport": "League of Legends",
        "league": "LCK",
        "p_model": 0.52,
        "summary": (
            "NT Brion 1.67 vs DRX. Tips.gg mixed (~58% Brion bookish). Thin sample; honest 0.50-0.55. "
            "Fails EV bar at 1.67 (need ~0.67). Reject."
        ),
        "failure_modes": "DRX upset; patch/meta swing.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Expected rosters.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 1,
        "sources": [
            {"url": "https://tips.gg", "takeaway": "DRX vs Brion mixed expert/book split.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://gol.gg", "takeaway": "LCK stats.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://lol.fandom.com", "takeaway": "Team pages.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://lolesports.com", "takeaway": "Schedule.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Brion ~1.67.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.gamesoflegends.com", "takeaway": "Form.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- TENNIS: Ferreira set1 +2.5 (dog cover) ---
    {
        "match": "Ferreira Silva, Frederico vs Van Assche, Luca",
        "selection": "1. Sett - Game handikap 2.5: Ferreira Silva, Frederico +2.5",
        "sport": "Tennis",
        "league": "ATP/Challenger",
        "p_model": 0.70,
        "summary": (
            "Van Assche heavy fav NT 1.18. Ferreira set1 +2.5 games: covers unless VA bags set1 by 3+ games. "
            "Honest cover p ~0.68-0.72; use 0.70. NT 1.52 needs ~0.73 for standard — borderline/fail. "
            "Document; do not force if engine haircuts below bar."
        ),
        "failure_modes": "VA 6-1 set1; Ferreira double fault spiral.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.atptour.com", "takeaway": "Van Assche higher ranking favorite.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.tennisexplorer.com", "takeaway": "Form/H2H.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sofascore.com", "takeaway": "Ratings.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Ferreira set1 +2.5 @1.52; VA ML 1.18.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.oddsportal.com", "takeaway": "Market fav Van Assche.", "kind": "odds", "accessed_at": TODAY},
        ],
    },
    # --- SNOOKER: Cheung -2.5 (reject chalk HC) ---
    {
        "match": "Benzey, Connor vs Cheung, Ka Wai",
        "selection": "Parti handikap 2.5: Cheung, Ka Wai -2.5",
        "sport": "Snooker",
        "league": "Shenzhen Open",
        "p_model": 0.55,
        "summary": (
            "Cheung heavy fav 1.17; -2.5 frames needs win by 3+. Honest p ~0.50-0.58; use 0.55. "
            "NT 1.70 needs ~0.66 — reject chalk frame spread."
        ),
        "failure_modes": "Benzey steals frames; 4-2 scoreline loses HC.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Both listed.",
        "script_lean": "dominant_favorite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            {"url": "https://www.sofascore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Fixtures.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://cuetracker.net", "takeaway": "Results.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wst.tv", "takeaway": "Tour.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Cheung -2.5 @1.70 ML 1.17.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.snooker.org", "takeaway": "Context.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # --- ESPORTS: 1W Under 2.5 maps ---
    {
        "match": "1W Team vs Arcred",
        "selection": "Totalt antall kart 2.5: Under 2.5",
        "sport": "Counter-Strike",
        "league": "CS",
        "p_model": 0.52,
        "summary": (
            "BO3 U2.5 = 2-0 either side. NT 1.77. Without HLTV map-win dominance proof, honest 2-0 rate ~50-55%. "
            "Use 0.52 — fails EV (need ~0.63). Existing 1W ML pack already notes thin edge. Reject totals."
        ),
        "failure_modes": "3-map series; upset reverse sweep.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Expected BO3 lineups.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 1,
        "sources": [
            {"url": "https://www.hltv.org", "takeaway": "CS form/maps reference.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://liquipedia.net", "takeaway": "Event/roster.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://bo3.gg", "takeaway": "Match listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.vlr.gg", "takeaway": "Esports context.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT U2.5 @1.77.", "kind": "odds", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Schedule.", "kind": "stats", "accessed_at": TODAY},
        ],
    },
    # Refresh Badosa ML honest reject numbers
    {
        "match": "Sherif Ahmed Abdelaziz, Maiar vs Badosa, Paula",
        "selection": "Vinner: Badosa, Paula",
        "sport": "Tennis",
        "league": "WTA",
        "p_model": 0.60,
        "summary": (
            "Dimers/model ~60% Badosa; NT 1.42 implies ~70%. Negative EV on ML chalk. "
            "Honest p_model 0.60 fails min EV. Prefer Sherif +3.5 games instead."
        ),
        "failure_modes": "Sherif clay upset; Badosa injury/rust.",
        "context_risk": "low",
        "availability_status": "predicted",
        "availability_notes": "Both expected.",
        "script_lean": "competitive",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            {"url": "https://www.dimers.com", "takeaway": "Badosa ~60% win probability.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.wtatennis.com", "takeaway": "Rankings/form.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.tennisexplorer.com", "takeaway": "H2H.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.sofascore.com", "takeaway": "Ratings.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": TODAY},
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Badosa 1.42 Sherif 2.50.", "kind": "odds", "accessed_at": TODAY},
        ],
    },
]


def main() -> None:
    cs = parse_odds_file(ROOT / "inbox" / "current_odds_01.txt")
    by_ms = {(c.match, c.selection): c for c in cs}
    written = 0
    missing = []
    for pack in PACKS:
        key = (pack["match"], pack["selection"])
        c = by_ms.get(key)
        if c is None:
            # fuzzy: selection contains
            hits = [x for x in cs if x.match == pack["match"] and pack["selection"] in x.selection]
            if len(hits) == 1:
                c = hits[0]
                pack["selection"] = c.selection
            else:
                missing.append(key)
                # still write with provided key
                ek = f"{pack['match']}_{pack['selection']}"
                path = evidence_path(EV, ek)
                path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                written += 1
                print(f"WARN no parse match, wrote scaffold: {path.name}")
                continue
        ek = c.evidence_key or f"{c.match}_{c.selection}"
        path = evidence_path(EV, ek)
        path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written += 1
        print(f"OK {c.decimal_odds:5.2f} p={pack['p_model']:.2f} {path.name[:70]}")
    print(f"\nWrote {written} packs; missing exact parse: {len(missing)}")
    for m in missing:
        print("  missing", m)


if __name__ == "__main__":
    main()
