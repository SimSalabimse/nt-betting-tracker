"""Recommend with WC final football pending stakes excluded from daily risk (user-authorized one-time)."""
from __future__ import annotations

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

ODDS = ROOT / "inbox" / "current_odds_01.txt"

# WC final one-time football tickets — ignore stake against daily risk
EXCLUDE_BET_IDS = {
    "52ca413481b3",  # Spania BTTS Nei
    "d910b991bba6",  # 1H U0.5 (already settled Win, but keep for safety)
}


def main() -> None:
    cfg = load_config()
    _orig = risk_mod.evaluate_risk

    def risk_excl(cfg_, equity, phase, rows=None):
        if rows is None:
            rows = load_bets(path_from_config(cfg_, "bets"))
        r = _orig(cfg_, equity, phase, rows)
        # Recompute pending excluding WC football one-offs
        pending_ex = 0.0
        for row in rows:
            if row.get("result") != "Pending":
                continue
            if (row.get("bet_id") or "") in EXCLUDE_BET_IDS:
                continue
            if (row.get("sport") or "").lower() == "football" and "Spania" in (
                row.get("match") or ""
            ):
                continue
            pending_ex += fnum(row.get("stake_nok")) or 0.0
        cap = float(r["daily_risk_cap_nok"])
        remaining = round(cap - pending_ex, 2)
        r["open_pending_risk_nok"] = round(pending_ex, 2)
        r["remaining_risk_nok"] = max(0.0, remaining)
        r["can_bet"] = (not r.get("stopped")) and remaining >= float(
            cfg_["norsk_tipping"]["min_stake_nok"]
        )
        r["reasons"] = [
            x
            for x in (r.get("reasons") or [])
            if "exhausted" not in x.lower()
        ]
        if remaining <= 0 and not r["can_bet"]:
            r["reasons"].append(
                f"daily risk exhausted (ex-WC-football): pending {pending_ex:.2f} / cap {cap:.2f}"
            )
        r["formula"] = (
            r.get("formula", "")
            + " | USER: ignore pending Spania WC football stakes in risk"
        )
        print(
            f"Risk excl WC football pending: counted_pending={pending_ex:.2f} "
            f"remaining={r['remaining_risk_nok']:.2f} cap={cap:.2f} can_bet={r['can_bet']}"
        )
        return r

    risk_mod.evaluate_risk = risk_excl
    recommend_mod.evaluate_risk = risk_excl
    try:
        result = run_recommend(cfg, ODDS, log_pending=True)
    finally:
        risk_mod.evaluate_risk = _orig
        recommend_mod.evaluate_risk = _orig

    print("n_picked", result.get("n_picked"), "ids", result.get("logged_bet_ids"))
    print("remaining", result.get("remaining_risk"), "equity", result.get("equity"))
    place = ROOT / "outbox" / "PLACE_THESE.md"
    if place.exists():
        print(place.read_text(encoding="utf-8")[:4500])


if __name__ == "__main__":
    main()
