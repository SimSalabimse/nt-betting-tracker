#!/usr/bin/env python3
"""Deep evidence packs — 2026-07-21 KO window 17:55–22:00 CEST."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.evidence import evidence_path

EV = ROOT / "evidence"
TODAY = "2026-07-21"

SRC = lambda url, take, kind="stats": {
    "url": url,
    "takeaway": take,
    "kind": kind,
    "accessed_at": TODAY,
}

PACKS: list[dict] = [
    # ── Darts World Matchplay R2 ──────────────────────────────────────────
    {
        "match": "Clayton, Jonny vs Anderson, Gary",
        "selection": "Totalt antall runder 18.5: Over 18.5",
        "sport": "Darts",
        "league": "World Matchplay",
        "p_model": 0.62,
        "summary": (
            "WMP R2 first-to-11 (max 21 legs). NT Over 18.5 @1.80. "
            "Anderson demolished Joyce 10-2 at ~110 avg in R1 but that pace rarely "
            "repeats; Clayton beat Heta 10-7 at 97.6 and called Anderson his hero — "
            "expect competitive scoring. Public tip lean O18.5 for wire match. "
            "Honest p 0.60-0.64; use 0.62. After 5% haircut EV ≈ 0.589*1.80−1 ≈ +0.06."
        ),
        "failure_modes": "Anderson re-runs 105+ and wins 11-5/11-6; one-sided early whitewash.",
        "context_risk": "medium",
        "availability_status": "confirmed",
        "availability_notes": "Both through R1; scheduled WMP Blackpool evening session.",
        "script_lean": "competitive_long_match",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            SRC(
                "https://www.thestatszone.com/jonny-clayton-vs-gary-anderson-preview-prediction-2026-world-matchplay-second-round-207342",
                "Tip Over 18.5 legs; Anderson 109.96 R1 but drop-off expected; Clayton ~95-100.",
            ),
            SRC(
                "https://sports.yahoo.com/articles/2026-world-matchplay-darts-day-100004272.html",
                "R1: Anderson 10-2 Joyce; Clayton 10-7 Heta.",
            ),
            SRC("https://dartsnews.com/pdc/world-matchplay-2026-draw-schedule-field-history-format-and-predictions", "R2 schedule Clayton vs Anderson."),
            SRC("https://www.pdc.tv", "World Matchplay format first-to-11 R2.", "official"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT O18.5 1.80; Anderson ML 1.65.", "odds"),
        ],
    },
    {
        "match": "Clayton, Jonny vs Anderson, Gary",
        "selection": "Vinner: Anderson, Gary",
        "sport": "Darts",
        "league": "World Matchplay",
        "p_model": 0.58,
        "summary": (
            "Anderson ML @1.65 (implied ~60.6%). R1 avg 110 is elite but mean-reversion "
            "risk high; Clayton solid 97+ and matchplay pedigree. Fair p ~0.55-0.60. "
            "Need ~0.66 after haircut for clean EV at 1.65. Honest 0.58 — reject as primary; "
            "prefer Over 18.5 at better price/edge."
        ),
        "failure_modes": "Anderson holds form and wins comfortably; or Clayton wins outright.",
        "context_risk": "medium",
        "availability_status": "confirmed",
        "availability_notes": "Both confirmed through to R2.",
        "script_lean": "competitive_long_match",
        "selection_vs_script": "neutral",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC(
                "https://www.thestatszone.com/jonny-clayton-vs-gary-anderson-preview-prediction-2026-world-matchplay-second-round-207342",
                "Anderson superb R1 but averages not always sticky; close match expected.",
            ),
            SRC("https://sports.yahoo.com/articles/2026-world-matchplay-darts-day-100004272.html", "Anderson 10-2 R1."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Anderson 1.65.", "odds"),
        ],
    },
    {
        "match": "van Gerwen, Michael vs van Duijvenbode, Dirk",
        "selection": "Vinner: van Gerwen, Michael",
        "sport": "Darts",
        "league": "World Matchplay",
        "p_model": 0.70,
        "summary": (
            "WMP R2 Dutch derby. NT MvG @1.50 (implied 66.7%). MvG 10-6 Gilding (94.85, "
            "missed 9-darter) — not peak form but still class edge vs DVD who scraped "
            "13-11 past Dobey after surviving match darts. Public tips lean MvG. "
            "Honest p 0.68-0.72; use 0.70. After haircut EV ≈ 0.665*1.50−1 ≈ −0.00 — "
            "borderline/reject if engine min EV 0.03 strict; slightly soft if explore."
        ),
        "failure_modes": "MvG stuck ~92 avg and DVD high 180 volume; DVD push to decider.",
        "context_risk": "medium",
        "availability_status": "confirmed",
        "availability_notes": "Both through R1; evening Blackpool session ~21:15 CEST.",
        "script_lean": "favourite_control",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 3,
        "sources": [
            SRC(
                "https://www.thestatszone.com/michael-van-gerwen-vs-dirk-van-duijvenbode-preview-prediction-2026-world-matchplay-second-round-207446",
                "Tip MvG to win; DVD battling but limited deep runs; MvG not peak but favoured.",
            ),
            SRC(
                "https://www.sportytrader.com/en/betting-tips/michael-van-gerwen-dirk-van-duijvenbode-360160/",
                "Prediction MvG; recent H2H lean MvG.",
            ),
            SRC("https://sports.yahoo.com/articles/2026-world-matchplay-darts-day-100004272.html", "R1: MvG 10-6; DVD 13-11 Dobey."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT MvG 1.50.", "odds"),
        ],
    },
    {
        "match": "van Gerwen, Michael vs van Duijvenbode, Dirk",
        "selection": "Legs handikap -2.5: van Duijvenbode, Dirk +2.5",
        "sport": "Darts",
        "league": "World Matchplay",
        "p_model": 0.58,
        "summary": (
            "DVD +2.5 @1.67. Covers if DVD loses by ≤2 or wins. Given tight R1 for both "
            "and MvG form not elite, cover rate elevated vs pure ML. Fair p ~0.55-0.60. "
            "Need ~0.65 for EV at 1.67 after haircut — honest 0.58 may fail EV; keep as "
            "secondary research, not forced stake."
        ),
        "failure_modes": "MvG wins 11-6 or better (cover fails).",
        "context_risk": "medium",
        "availability_status": "confirmed",
        "availability_notes": "Same match as ML pack.",
        "script_lean": "favourite_control",
        "selection_vs_script": "conflict",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC(
                "https://www.thestatszone.com/michael-van-gerwen-vs-dirk-van-duijvenbode-preview-prediction-2026-world-matchplay-second-round-207446",
                "MvG favoured but not flying; DVD competitive R1.",
            ),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT DVD +2.5 1.67.", "odds"),
        ],
    },
    # ── Football ──────────────────────────────────────────────────────────
    {
        "match": "Falkenberg vs Helsingborg",
        "selection": "BTTS Ja",
        "sport": "Football",
        "league": "Superettan",
        "p_model": 0.62,
        "summary": (
            "Superettan 19:00. Models cluster BTTS ~60% and O2.5 ~60%+. Falkenberg slight "
            "home fav (~48-51% win). NT board rich on props. Honest BTTS p 0.60-0.64. "
            "If NT BTTS ~1.55-1.70, EV possible; verify live price. Use 0.62."
        ),
        "failure_modes": "0-1/1-0 cagey derby; one side parks bus.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Domestic Superettan midweek; expect near full XIs. Confirm 1h pre-KO.",
        "script_lean": "open_game",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://oddspedia.com/football/helsingborg-falkenberg-2725/predictions", "Home ~48% win; goals markets active."),
            SRC("https://www.bettingclosed.com/prediction/1973696/falkenberg-helsingborg", "BTTS Gol lean; O2.5 lean."),
            SRC("https://footystats.org/sweden/helsingborgs-if-vs-falkenbergs-ff-h2h-stats", "O2.5 ~1.61 market; Superettan week 15."),
            SRC("https://www.sofascore.com", "Form Superettan.", "stats"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Superettan board Falkenberg-HIF.", "odds"),
        ],
    },
    {
        "match": "Falkenberg vs Helsingborg",
        "selection": "Totalt antall mål - over/under 2.5: Over 2.5",
        "sport": "Football",
        "league": "Superettan",
        "p_model": 0.60,
        "summary": (
            "O2.5 market often ~1.55-1.65 Superettan. Models ~60% O2.5. Honest 0.60. "
            "Need odds ≥1.80 after haircut for +3% EV; if NT shorter, reject chalk total."
        ),
        "failure_modes": "1-0 / 0-1 low event.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Same XI context as BTTS pack.",
        "script_lean": "open_game",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.bettingclosed.com/prediction/1973696/falkenberg-helsingborg", "O2.5 recommended."),
            SRC("https://footystats.org/sweden/helsingborgs-if-vs-falkenbergs-ff-h2h-stats", "O2.5 price ~1.61."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT O2.5 Falkenberg board.", "odds"),
        ],
    },
    {
        "match": "Fenerbahce vs Gornik Zabrze",
        "selection": "Fenerbahce to Win",
        "sport": "Football",
        "league": "UEFA Champions League",
        "p_model": 0.72,
        "summary": (
            "UCL Q2 1st leg Istanbul. Fenerbahce heavy home favourite vs Polish Górnik. "
            "Class/budget gap large; home European nights. If NT ~1.35-1.45, need p≥0.78 "
            "for EV — likely reject chalk. If price ≥1.55, 0.72 can work. Honest 0.70-0.75."
        ),
        "failure_modes": "Cagey 0-0/1-1 first leg; rotation/rest key attackers.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "European midweek; check late XI. No confirmed mass rest flag in window.",
        "script_lean": "home_favourite_control",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.uefa.com/uefachampionsleague/match/2048725--fenerbahce-vs-gornik-zabrze/", "UCL Q2 1st leg Istanbul."),
            SRC("https://www.transfermarkt.co.in/fenerbahce-sk_gornik-zabrze/index/spielbericht/4897896", "Match sheet / squad context."),
            SRC("https://www.sofascore.com", "Form ratings.", "stats"),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Fenerbahce board.", "odds"),
        ],
    },
    {
        "match": "Fenerbahce vs Gornik Zabrze",
        "selection": "Totalt antall mål - Over/Under 2.5: Over 2.5",
        "sport": "Football",
        "league": "UEFA Champions League",
        "p_model": 0.58,
        "summary": (
            "Home favourite often scores 2+ but first-leg UCL can be controlled. "
            "Honest O2.5 ~0.55-0.60. Only bet if NT price ≥1.85."
        ),
        "failure_modes": "1-0 professional home win.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "Same as ML pack.",
        "script_lean": "home_favourite_control",
        "selection_vs_script": "neutral",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.uefa.com/uefachampionsleague/match/2048725--fenerbahce-vs-gornik-zabrze/", "UCL Q2 context."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT totals Fenerbahce.", "odds"),
        ],
    },
    {
        "match": "Sturm Graz vs Hearts",
        "selection": "BTTS Ja",
        "sport": "Football",
        "league": "UEFA Champions League",
        "p_model": 0.58,
        "summary": (
            "UCL Q Sturm home vs Hearts. NT BTTS Ja ~1.67. Both can score in open European "
            "ties but not locked. Fair ~0.55-0.60. Need ~0.65 for EV at 1.67 — borderline."
        ),
        "failure_modes": "1-0 Sturm clean sheet.",
        "context_risk": "medium",
        "availability_status": "predicted",
        "availability_notes": "European night; confirm XI.",
        "script_lean": "mixed",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC("https://www.uefa.com", "UCL qualifying context."),
            SRC("https://www.sofascore.com", "Form."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT BTTS Ja ~1.67 Sturm-Hearts.", "odds"),
        ],
    },
    # ── Tennis ────────────────────────────────────────────────────────────
    {
        "match": "Van de Zandschulp, Botic vs Faria, Jaime",
        "selection": "Vinner: Faria, Jaime",
        "sport": "Tennis",
        "league": "ATP Estoril",
        "p_model": 0.55,
        "summary": (
            "ATP Estoril R1 clay. NT Faria fav @1.57; Dimers model ~53% Faria. "
            "Honest 0.53-0.57. Need ~0.69 for EV at 1.57 after haircut — reject chalk ML. "
            "Recorded for audit; do not force stake."
        ),
        "failure_modes": "BVDZ level rises on clay; Faria nerves R1.",
        "context_risk": "high",
        "availability_status": "predicted",
        "availability_notes": "KO ~18:10 — may already be on court by place time; skip if live.",
        "script_lean": "slight_favourite",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 2,
        "sources": [
            SRC(
                "https://www.dimers.com/news/botic-van-de-zandschulp-vs-jaime-faria-tennis-prediction-atp-estoril-open-2026-ac",
                "Model ~53% Faria.",
            ),
            SRC(
                "https://www.thestatszone.com/botic-van-de-zandschulp-vs-jaime-faria-preview-prediction-2026-estoril-open-first-round-207083",
                "Estoril R1 preview clay.",
            ),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Faria 1.57.", "odds"),
        ],
    },
    {
        "match": "Brockmann, Tessa Johanna vs Jacquemot, Elsa",
        "selection": "1. Sett - Game handikap 1.5: Jacquemot, Elsa -1.5",
        "sport": "Tennis",
        "league": "WTA Hamburg",
        "p_model": 0.52,
        "summary": (
            "WTA Hamburg. Jacquemot fav set/game lines. -1.5 games set1 is aggressive. "
            "Honest ~0.50-0.54. Unlikely to clear EV at 1.52 without stronger edge — reject."
        ),
        "failure_modes": "Tight first set; Brockmann holds serve cluster.",
        "context_risk": "high",
        "availability_status": "predicted",
        "availability_notes": "19:00 KO; confirm not started.",
        "script_lean": "favourite_set",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 1,
        "sources": [
            SRC("https://www.sofascore.com", "WTA Hamburg form."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT Jacquemot set hcap 1.52.", "odds"),
        ],
    },
    # ── Esports (thin; honest, likely reject EV) ──────────────────────────
    {
        "match": "E Wie Einfach E-Sports vs Berlin International Gaming",
        "selection": "Totalt antall kart 2.5: Under 2.5",
        "sport": "LoL",
        "league": "Prime League",
        "p_model": 0.55,
        "summary": (
            "Prime League BO3 U2.5 @1.52. Thin public data; favourite often 2-0. "
            "Honest 0.52-0.58. Hard to clear 3% EV at 1.52 without strong form edge — "
            "conservative 0.55, expect reject or explore-only."
        ),
        "failure_modes": "Competitive series goes 2-1.",
        "context_risk": "high",
        "availability_status": "stable_guess",
        "availability_notes": "Lineups expected full BO3; no stand-in flag in window.",
        "script_lean": "favourite_2_0",
        "selection_vs_script": "agree",
        "base_rate_conflict": False,
        "confidence": 1,
        "sources": [
            SRC("https://gol.gg", "LoL form reference."),
            SRC("https://www.norsk-tipping.no/sport/oddsen", "NT U2.5 maps 1.52.", "odds"),
        ],
    },
]


def _slug_key(match: str, selection: str) -> str:
    return f"{match}_{selection}"


def write_pack(p: dict, *, evidence_key: str | None = None) -> Path:
    match = p["match"]
    selection = p["selection"]
    body = {
        "match": match,
        "selection": selection,
        "sport": p.get("sport") or "",
        "league": p.get("league") or "",
        "date": TODAY,
        "p_model": float(p["p_model"]),
        "summary": p["summary"],
        "failure_modes": p.get("failure_modes") or "",
        "sources": p.get("sources") or [],
        "availability_status": p.get("availability_status") or "missing",
        "availability_notes": p.get("availability_notes") or "",
        "context_risk": p.get("context_risk") or "unknown",
        "script_lean": p.get("script_lean") or "",
        "selection_vs_script": p.get("selection_vs_script") or "unknown",
        "base_rate_conflict": bool(p.get("base_rate_conflict")),
        "confidence": int(p.get("confidence") or 2),
        "notes": p.get("notes") or "Deep pack 2026-07-21 evening window 17:55-22:00.",
    }
    ek = evidence_key or _slug_key(match, selection)
    path = evidence_path(EV, ek)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> None:
    from nt.odds_parse import parse_odds_file

    EV.mkdir(parents=True, exist_ok=True)
    cands = parse_odds_file(ROOT / "inbox" / "current_odds_01.txt")
    written = 0
    for p in PACKS:
        match = p["match"]
        selection = p["selection"]
        hits = [
            c
            for c in cands
            if c.match == match
            and (
                c.selection == selection
                or selection.lower() in (c.selection or "").lower()
                or (c.selection or "").lower() in selection.lower()
            )
        ]
        if len(hits) == 1:
            c = hits[0]
            p = dict(p)
            p["selection"] = c.selection
            path = write_pack(p, evidence_key=c.evidence_key or _slug_key(c.match, c.selection))
            print(f"OK {c.decimal_odds:5.2f} p={p['p_model']:.2f} {c.selection[:55]}")
            written += 1
            continue
        # fuzzy match on match name fragment
        m_key = match.split(" vs ")[0][:12].lower()
        hits2 = [
            c
            for c in cands
            if m_key in (c.match or "").lower()
            and any(
                tok in (c.selection or "").lower()
                for tok in selection.lower().replace(":", " ").split()
                if len(tok) > 3
            )
        ]
        if len(hits2) == 1:
            c = hits2[0]
            p = dict(p)
            p["match"] = c.match
            p["selection"] = c.selection
            path = write_pack(p, evidence_key=c.evidence_key or _slug_key(c.match, c.selection))
            print(f"OK~{c.decimal_odds:5.2f} p={p['p_model']:.2f} {c.selection[:55]}")
            written += 1
            continue
        path = write_pack(p)
        print(f"SOFT {path.name} hits={len(hits)}/{len(hits2)} {selection[:50]}")
        written += 1
    print(f"Wrote {written} deep packs")


if __name__ == "__main__":
    main()
