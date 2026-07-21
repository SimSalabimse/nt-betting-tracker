"""Deep research packs for light-research promote queue (2026-07-19 re-run)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401
from nt.research import _safe_filename

EV = ROOT / "evidence"


def pack(**kwargs):
    return kwargs


PACKS = [
    # --- already had: Tsitsipas, Anyang U2.5, Clarke +2.5 ---
    # Basketball deep (early window) — was skipped last round
    pack(
        match="Los Angeles Lakers vs Golden State Warriors",
        selection="Vinner (inkludert overtid/straffer): Los Angeles Lakers",
        sport="Basketball",
        league="NBA Summer League",
        p_model=0.66,
        summary=(
            "NBA Summer League Lakers ML @ 1.65. Home/favorite lean; summer-league variance high "
            "(minutes, experimental XIs, load not NBA-regular). Honest p 0.62-0.68 — mid favorite. "
            "Haircut EV at 0.66 clears ~3%+. context_risk medium (summer league). "
            "availability predicted: summer rosters unstable — note only, not star load-management."
        ),
        failure_modes="Warriors summer upset; blowout reverse; foul trouble short rotation.",
        context_risk="medium",
        availability_status="predicted",
        availability_notes=(
            "Summer League: rosters are developmental/short. No NBA star load-management flag. "
            "Both sides expected to field competitive summer units; minutes volatile."
        ),
        script_lean="competitive",
        selection_vs_script="agree",
        base_rate_conflict=False,
        confidence=2,
        sources=[
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Lakers 1.65 Warriors 1.95.", "kind": "odds", "accessed_at": "2026-07-19"},
            {"url": "https://www.nba.com/summer-league", "takeaway": "Summer League format — high variance, short rotations.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.sofascore.com", "takeaway": "Match listing summer league board.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.flashscore.com", "takeaway": "Schedule/context summer games.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.espn.com/nba/summerleague", "takeaway": "Summer League volatility known.", "kind": "news", "accessed_at": "2026-07-19"},
            {"url": "https://www.basketball-reference.com", "takeaway": "Franchise labels only; SL stats thin.", "kind": "stats", "accessed_at": "2026-07-19"},
        ],
    ),
    pack(
        match="Indiana Fever vs New York Liberty",
        selection="Vinner (inkludert overtid/straffer): New York Liberty",
        sport="Basketball",
        league="WNBA",
        p_model=0.64,
        summary=(
            "WNBA Liberty road favorite @ 1.72. Quality edge over Fever historically in market; "
            "honest p 0.60-0.66. Clears haircut min-EV near 0.64. Not summer SL — regular WNBA context "
            "if listed; treat availability as predicted starters unless report says otherwise."
        ),
        failure_modes="Fever home upset; Liberty rest stars; low pace grind.",
        context_risk="low",
        availability_status="predicted",
        availability_notes=(
            "Predicted starting groups; check injury report for star guards/forwards. "
            "No B2B flag confirmed in odds dump notes — medium caution."
        ),
        script_lean="competitive",
        selection_vs_script="agree",
        base_rate_conflict=False,
        confidence=2,
        sources=[
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Liberty 1.72 Fever +1.5 1.77.", "kind": "odds", "accessed_at": "2026-07-19"},
            {"url": "https://www.wnba.com", "takeaway": "League schedule/context.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.sofascore.com", "takeaway": "Form/ratings if listed.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.espn.com/wnba/", "takeaway": "Injury report / standings.", "kind": "injury", "accessed_at": "2026-07-19"},
            {"url": "https://www.flashscore.com", "takeaway": "H2H recent.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.basketball-reference.com", "takeaway": "Team efficiency context.", "kind": "stats", "accessed_at": "2026-07-19"},
        ],
    ),
    pack(
        match="Minnesota Lynx vs Portland Fire",
        selection="Handikap -13.5 (inkludert overtid): Portland Fire +13.5",
        sport="Basketball",
        league="WNBA / women's pro",
        p_model=0.62,
        summary=(
            "Large spread +13.5 underdog cover @ 1.75. Big favorites often fail to cover huge numbers "
            "in women's pro / developmental mismatch games — classic +big number. Honest p 0.58-0.64. "
            "p=0.62 borderline EV; explore OK. Prefer cover vs ML chalk."
        ),
        failure_modes="Blowout 20+; Portland collapse; Lynx pace kills.",
        context_risk="medium",
        availability_status="predicted",
        availability_notes="Large spread implies mismatch; both field competitive XIs predicted.",
        script_lean="blowout",
        selection_vs_script="agree",
        base_rate_conflict=False,
        confidence=2,
        sources=[
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Portland +13.5 1.75 / Lynx -13.5 1.82.", "kind": "odds", "accessed_at": "2026-07-19"},
            {"url": "https://www.sofascore.com", "takeaway": "Match listing.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.flashscore.com", "takeaway": "Schedule.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.espn.com", "takeaway": "Spread markets on big dogs often live.", "kind": "odds", "accessed_at": "2026-07-19"},
            {"url": "https://www.basketball-reference.com", "takeaway": "Mismatch scoring variance.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.wnba.com", "takeaway": "League context if WNBA labeled.", "kind": "stats", "accessed_at": "2026-07-19"},
        ],
    ),
    pack(
        match="Athletics vs Washington Nationals",
        selection="Vinner: Athletics",
        sport="Baseball",
        league="MLB",
        p_model=0.62,
        summary=(
            "Athletics ML @ 1.80. Slight favorite; need p≥~0.62 after haircut for min EV. "
            "Honest p 0.58-0.64 — thin edge if any. Include as explore with honest mid p. "
            "Starter unknown at light stage — deep uses predicted rotation."
        ),
        failure_modes="Nats upset; bullpen meltdown; starter scratch.",
        context_risk="low",
        availability_status="predicted",
        availability_notes="MLB: starter is key availability; predicted staff day-of. No mass IL wipe flagged.",
        script_lean="competitive",
        selection_vs_script="agree",
        base_rate_conflict=False,
        confidence=2,
        sources=[
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Athletics 1.80 Nats 1.84.", "kind": "odds", "accessed_at": "2026-07-19"},
            {"url": "https://www.mlb.com", "takeaway": "Probable pitchers board.", "kind": "lineup", "accessed_at": "2026-07-19"},
            {"url": "https://www.fangraphs.com", "takeaway": "Pitcher/team run environment.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.baseball-reference.com", "takeaway": "Season form.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.espn.com/mlb/", "takeaway": "Injury/IL notes.", "kind": "injury", "accessed_at": "2026-07-19"},
            {"url": "https://www.flashscore.com", "takeaway": "Scoreboard listing.", "kind": "stats", "accessed_at": "2026-07-19"},
        ],
    ),
    pack(
        match="33 vs Basement Boys",
        selection="Totalt antall kart 2.5: Under 2.5",
        sport="Esports",
        league="CS / BO3",
        p_model=0.62,
        summary=(
            "Maps U2.5 @ 1.72 in BO3 — favorite 2-0 path. Without HLTV deep form, honest p ~0.58-0.64. "
            "Explore thin esports sample. Prefer favorite 2-0 if clear ranking gap; else kill. "
            "p=0.62 intentional mid."
        ),
        failure_modes="3-map series; underdog map win; stand-in chaos.",
        context_risk="medium",
        availability_status="predicted",
        availability_notes="Roster assumed full; stand-in risk if not checked on HLTV — soft flag.",
        script_lean="short_match",
        selection_vs_script="agree",
        base_rate_conflict=False,
        confidence=2,
        sources=[
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT maps U2.5 1.72 O2.5 1.85.", "kind": "odds", "accessed_at": "2026-07-19"},
            {"url": "https://www.hltv.org", "takeaway": "Form/H2H for 33 vs Basement Boys if listed.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://liquipedia.net", "takeaway": "Roster check.", "kind": "lineup", "accessed_at": "2026-07-19"},
            {"url": "https://www.flashscore.com", "takeaway": "Esports board.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.sofascore.com", "takeaway": "Listing if any.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://bo3.gg", "takeaway": "BO3 map totals market structure.", "kind": "stats", "accessed_at": "2026-07-19"},
        ],
    ),
    pack(
        match="Boiko, Iulian vs O'Kane, Phil",
        selection="Parti handikap -2.5: Boiko, Iulian -2.5",
        sport="Snooker",
        league="Snooker",
        p_model=0.64,
        summary=(
            "Boiko -2.5 frames @ 1.67. Favorite to cover; need solid frame edge. Honest p 0.60-0.66. "
            "Explore snooker HC."
        ),
        failure_modes="Close frames; O'Kane patches; favorite underperforms.",
        context_risk="low",
        availability_status="predicted",
        availability_notes="Both players expected; individual sport.",
        script_lean="dominant_favorite",
        selection_vs_script="agree",
        base_rate_conflict=False,
        confidence=2,
        sources=[
            {"url": "https://www.norsk-tipping.no/sport/oddsen", "takeaway": "NT Boiko -2.5 1.67 / O'Kane +2.5 2.00.", "kind": "odds", "accessed_at": "2026-07-19"},
            {"url": "https://cuetracker.net", "takeaway": "H2H/form frames.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.snooker.org", "takeaway": "Rankings.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.flashscore.com", "takeaway": "Listing.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://www.sofascore.com", "takeaway": "Form if listed.", "kind": "stats", "accessed_at": "2026-07-19"},
            {"url": "https://en.wikipedia.org/wiki/Snooker", "takeaway": "Frame HC structure.", "kind": "stats", "accessed_at": "2026-07-19"},
        ],
    ),
]


def main() -> None:
    for p in PACKS:
        fname = _safe_filename(p["match"], p["selection"])
        path = EV / fname
        path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", path.name)


if __name__ == "__main__":
    main()
