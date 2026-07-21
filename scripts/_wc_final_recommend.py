"""WC final recommend with one-time +10% equity risk boost (user-authorized)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

import nt.recommend as recommend_mod
from nt.config import load_config
from nt.odds_parse import attach_evidence, parse_odds_file
from nt.paths import ROOT as NT_ROOT
from nt import risk as risk_mod
from nt.recommend import run_recommend
from nt.evidence import grade_evidence

ODDS = NT_ROOT / "inbox" / "current_odds_01.txt"
BOOST_FRAC = 0.10  # user: another 10% of bankroll this time only


def main() -> None:
    cfg = load_config()
    cands = parse_odds_file(ODDS)
    attach_evidence(cands, NT_ROOT / "evidence")

    print("=== Attached evidence (this board) ===")
    for c in cands:
        if c.p_model is None:
            continue
        grade, issues = grade_evidence(
            c.evidence or {}, cfg, float(c.decimal_odds), selection=c.selection, sport=c.sport
        )
        print(
            f"  {c.match} | {c.selection} @ {c.decimal_odds} "
            f"p={c.p_model:.3f} grade={grade} issues={issues}"
        )

    _orig = risk_mod.evaluate_risk

    def boosted_risk(cfg, equity, phase, rows=None):
        r = _orig(cfg, equity, phase, rows)
        extra = round(float(equity) * BOOST_FRAC, 2)
        r["daily_risk_cap_nok"] = round(float(r["daily_risk_cap_nok"]) + extra, 2)
        r["remaining_risk_nok"] = round(float(r["remaining_risk_nok"]) + extra, 2)
        r["can_bet"] = (not r.get("stopped")) and r["remaining_risk_nok"] >= float(
            cfg["norsk_tipping"]["min_stake_nok"]
        )
        r["reasons"] = [
            x for x in (r.get("reasons") or []) if "exhausted" not in x.lower()
        ]
        r["wc_final_risk_boost_nok"] = extra
        r["formula"] = (
            r.get("formula", "")
            + f" | ONE-TIME +{BOOST_FRAC:.0%} equity WC-final boost (+{extra:.2f} NOK)"
        )
        print(
            f"=== Risk boost: +{extra:.2f} NOK → remaining {r['remaining_risk_nok']:.2f} "
            f"/ cap {r['daily_risk_cap_nok']:.2f} can_bet={r['can_bet']} ==="
        )
        return r

    # recommend binds evaluate_risk at import — patch both modules
    risk_mod.evaluate_risk = boosted_risk
    recommend_mod.evaluate_risk = boosted_risk
    try:
        result = run_recommend(cfg, ODDS, log_pending=True)
    finally:
        risk_mod.evaluate_risk = _orig
        recommend_mod.evaluate_risk = _orig

    print(
        "\n=== Recommend result keys ===",
        list(result.keys()) if isinstance(result, dict) else type(result),
    )
    if isinstance(result, dict):
        for k in (
            "n_picked",
            "n_rejects",
            "logged_bet_ids",
            "remaining_risk",
            "daily_cap",
            "place_path",
            "blocked",
            "message",
        ):
            if k in result:
                print(f"  {k}: {result[k]}")
    place = NT_ROOT / "outbox" / "PLACE_THESE.md"
    if place.exists():
        print("\n" + place.read_text(encoding="utf-8")[:5000])


if __name__ == "__main__":
    main()
