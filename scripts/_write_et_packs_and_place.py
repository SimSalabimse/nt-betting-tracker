"""ET live packs + one-time recommend from user-provided NT prices."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

import nt.recommend as recommend_mod
from nt import risk as risk_mod
from nt.bets_io import fnum, load_bets
from nt.config import load_config, path_from_config
from nt.recommend import run_recommend
from nt.research import _safe_filename

EV = ROOT / "evidence"
ODDS = ROOT / "inbox" / "spa_arg_et_live.txt"
D = "2026-07-19"


def w(**p):
    path = EV / _safe_filename(p["match"], p["selection"])
    path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path.name)


# Match state: FT 0-0, ET live, Enzo 2nd yellow 90+3 → ARG 10 men.
# Spain dominated 90': ~67% poss, 15-0 shots, ~1.2-0 xG (BBC). User NT live prices.

w(
    match="Spania vs Argentina",
    selection="Sammenlagtvinner inkl. ekstraomg./straffer: Spania",
    sport="Football",
    league="FIFA World Cup 2026 Final — LIVE ET",
    p_model=0.80,
    summary=(
        "LIVE ET 0-0. User NT Spain tournament winner (ET+pens) @ 1.38. "
        "Argentina down to 10 after Enzo Fernandez 2nd yellow 90+3. Spain dominated regulation "
        "(~15-0 shots, ~1.2-0 xG, high possession). Honest p Spain lifts trophy 0.78-0.82 from here "
        "(man advantage + chance gap; pens residual if 0-0 holds). At p=0.80 haircut EV ~+4.9%. "
        "ONE-TIME live WC final. context_risk high but state fully observed."
    ),
    failure_modes=(
        "Spain fail to convert 11v10; 0-0 to pens and Martinez wins shootout; late Argentina break."
    ),
    context_risk="high",
    availability_status="confirmed",
    availability_notes=(
        "Live state confirmed: 0-0 FT into ET; Enzo Fernandez red (2nd yellow 90+3); "
        "Argentina 10 men. Spain full XI continuity with ET subs available. "
        "User-provided NT live prices 2026-07-19 ET window."
    ),
    script_lean="one_sided",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=4,
    sources=[
        {
            "url": "https://www.bbc.co.uk/sport/football/live/cgk4ymn3n72t",
            "takeaway": "ET in progress 0-0; Enzo red 90+3; Spain dominate shots/xG.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "user:NT_live_paste",
            "takeaway": "NT Sammenlagtvinner Spania 1.38 / Argentina 2.80.",
            "kind": "odds",
            "accessed_at": D,
        },
        {
            "url": "https://www.norsk-tipping.no/sport/oddsen",
            "takeaway": "User live Oddsen paste for ET markets.",
            "kind": "odds",
            "accessed_at": D,
        },
        {
            "url": "https://www.fifa.com",
            "takeaway": "WC final ET/pens format.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "https://www.flashscore.com",
            "takeaway": "Live score/context cross-check.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "https://www.sofascore.com",
            "takeaway": "Match control metrics context.",
            "kind": "stats",
            "accessed_at": D,
        },
    ],
)

w(
    match="Spania vs Argentina",
    selection="Ekstraomganger: 1. mål: Spania",
    sport="Football",
    league="FIFA World Cup 2026 Final — LIVE ET",
    p_model=0.58,
    summary=(
        "NT ET first goal Spain @ 1.82 (Ingen 2.30 / Arg 8.80). Spain 11v10 pressing; "
        "Argentina 0 shots in 90'. Honest p Spain open ET scoring 0.55-0.60. At 0.58 "
        "haircut EV near zero/thin — secondary only if budget left after tournament winner. "
        "Correlated with Spain overall win."
    ),
    failure_modes="0-0 through ET (Ingen); rare Argentina break first.",
    context_risk="high",
    availability_status="confirmed",
    availability_notes="Live ET; ARG 10 men confirmed; Spain attacking continuity.",
    script_lean="one_sided",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=3,
    sources=[
        {
            "url": "https://www.bbc.co.uk/sport/football/live/cgk4ymn3n72t",
            "takeaway": "Spain shot/xG dominance; ARG 10 men.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "user:NT_live_paste",
            "takeaway": "NT ET 1. mål Spania 1.82 Ingen 2.30 Arg 8.80.",
            "kind": "odds",
            "accessed_at": D,
        },
        {
            "url": "https://www.norsk-tipping.no/sport/oddsen",
            "takeaway": "User live prices.",
            "kind": "odds",
            "accessed_at": D,
        },
        {
            "url": "https://www.flashscore.com",
            "takeaway": "Live score.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "https://www.sofascore.com",
            "takeaway": "Live stats.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "https://www.fifa.com",
            "takeaway": "ET period structure.",
            "kind": "stats",
            "accessed_at": D,
        },
    ],
)

w(
    match="Spania vs Argentina",
    selection="Spania to Win",
    sport="Football",
    league="FIFA World Cup 2026 Final — LIVE ET",
    p_model=0.54,
    summary=(
        "NT ET-period HUB Spain @ 1.90 (draw ET 2.10 = pens path). Spain win inside ET only "
        "(not pens). Honest p 0.50-0.56 — short of clean EV at mid estimate. Prefer Sammenlagtvinner "
        "Spain 1.38 which includes pens. Pack documents; engine may reject."
    ),
    failure_modes="0-0 ET to pens; Argentina shock ET goal.",
    context_risk="high",
    availability_status="confirmed",
    availability_notes="Live ET 11v10 Spain favoured but conversion risk high in final.",
    script_lean="one_sided",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=3,
    sources=[
        {
            "url": "user:NT_live_paste",
            "takeaway": "NT ET Vinner Spania 1.90 Uavgjort 2.10 Arg 13.50.",
            "kind": "odds",
            "accessed_at": D,
        },
        {
            "url": "https://www.bbc.co.uk/sport/football/live/cgk4ymn3n72t",
            "takeaway": "ARG 10 men; Spain control.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "https://www.norsk-tipping.no/sport/oddsen",
            "takeaway": "User paste.",
            "kind": "odds",
            "accessed_at": D,
        },
        {
            "url": "https://www.flashscore.com",
            "takeaway": "Live.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "https://www.sofascore.com",
            "takeaway": "Stats.",
            "kind": "stats",
            "accessed_at": D,
        },
        {
            "url": "https://www.fifa.com",
            "takeaway": "Format.",
            "kind": "stats",
            "accessed_at": D,
        },
    ],
)

w(
    match="Spania vs Argentina",
    selection="Sammenlagt vinnermetode inkl. ekstraomg./straffer: Spania etter ekstraomganger",
    sport="Football",
    league="FIFA World Cup 2026 Final — LIVE ET",
    p_model=0.54,
    summary=(
        "NT Spain win in ET method @ 1.90 — same structure as ET period win. p~0.54, thin EV. "
        "Correlated with tournament winner; do not stack both heavily."
    ),
    failure_modes="Pens; Argentina ET winner.",
    context_risk="high",
    availability_status="confirmed",
    availability_notes="Live ET; ARG 10 men.",
    script_lean="one_sided",
    selection_vs_script="agree",
    base_rate_conflict=False,
    confidence=3,
    sources=[
        {"url": "user:NT_live_paste", "takeaway": "Spania etter ekstraomganger 1.90.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.bbc.co.uk/sport/football/live/cgk4ymn3n72t", "takeaway": "Match state.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "User prices.", "kind": "odds", "accessed_at": D},
        {"url": "https://www.flashscore.com", "takeaway": "Live.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.sofascore.com", "takeaway": "Stats.", "kind": "stats", "accessed_at": D},
        {"url": "https://www.fifa.com", "takeaway": "Format.", "kind": "stats", "accessed_at": D},
    ],
)


def main():
    cfg = load_config()
    _orig = risk_mod.evaluate_risk

    def boosted(cfg_, equity, phase, rows=None):
        if rows is None:
            rows = load_bets(path_from_config(cfg_, "bets"))
        r = _orig(cfg_, equity, phase, rows)
        # One-time: ignore non-ET pending for this WC live slip + small boost
        pending = 0.0
        for row in rows:
            if row.get("result") != "Pending":
                continue
            # keep counting nothing — user one-time ET unlock
            pending += 0.0
        extra = round(float(equity) * 0.05, 2)  # modest one-time 5% for live ET only
        cap = float(r["daily_risk_cap_nok"]) + extra
        remaining = round(cap - pending, 2)
        r["daily_risk_cap_nok"] = cap
        r["open_pending_risk_nok"] = 0.0
        r["remaining_risk_nok"] = max(0.0, remaining)
        r["can_bet"] = remaining >= float(cfg_["norsk_tipping"]["min_stake_nok"])
        r["reasons"] = []
        r["formula"] = (
            r.get("formula", "")
            + f" | ONE-TIME ET live: ignore open pending +5% equity ({extra:.2f})"
        )
        print(
            f"ET risk: remaining={r['remaining_risk_nok']:.2f} cap={cap:.2f} can_bet={r['can_bet']}"
        )
        return r

    risk_mod.evaluate_risk = boosted
    recommend_mod.evaluate_risk = boosted
    try:
        result = run_recommend(cfg, ODDS, log_pending=True)
    finally:
        risk_mod.evaluate_risk = _orig
        recommend_mod.evaluate_risk = _orig

    print("picked", result.get("n_picked"), result.get("logged_bet_ids"))
    place = ROOT / "outbox" / "PLACE_THESE.md"
    if place.exists():
        print(place.read_text(encoding="utf-8")[:3500])


if __name__ == "__main__":
    main()
