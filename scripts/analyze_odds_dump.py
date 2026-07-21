#!/usr/bin/env python3
"""Parse NT odds dump, score with band history, write shortlist + evidence stubs, optional recommend."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nt_bootstrap  # noqa: F401

from nt.analytics import band_stats, overall_stats
from nt.bets_io import load_bets, odds_band
from nt.config import load_config, path_from_config
from nt.evidence import ev_after_haircut
from nt.odds_parse import parse_odds_file
from nt.recommend import refresh_state, run_recommend


def main() -> int:
    odds_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "inbox" / "odds_13-07.2026.txt"
    cfg = load_config()
    bankroll, phase, risk = refresh_state(cfg)
    rows = load_bets(path_from_config(cfg, "bets"))
    bands = band_stats(rows)
    overall = overall_stats(rows)

    candidates = parse_odds_file(odds_path)
    by_match: dict[str, list] = defaultdict(list)
    for c in candidates:
        by_match[c.match].append(c)

    print("=== NT ODDS DUMP ANALYSIS ===")
    print(f"File: {odds_path}")
    print(f"Equity: {bankroll['equity_nok']:.2f} NOK | Phase: {phase['phase_id']} | Daily cap: {risk['daily_risk_cap_nok']:.2f} | Can bet: {risk['can_bet']}")
    print(f"Candidates parsed: {len(candidates)} across {len(by_match)} matches")
    print(f"Ledger ROI: {overall['roi']*100:+.1f}% | winrate {overall['winrate']*100:.1f}%")
    print()
    print("Band history (this era):")
    for b in sorted(bands.keys()):
        s = bands[b]
        print(f"  {b:8} n={int(s['n']):3} ROI={s['roi']*100:+6.1f}% P/L={s['pl']:+7.1f}")
    print()

    # Implied probs with simple 5% haircut reverse for EV scan without p_model
    haircut = float(cfg["selection"]["probability_haircut"])
    print("=== MATCHES ===")
    for match, cs in by_match.items():
        print(f"\n## {match}  ({cs[0].sport})  markets={len(cs)}")
        # show main HUB + key totals/BTTS
        interesting = []
        for c in cs:
            sel_l = c.selection.lower()
            mt = (c.market_type or "").lower()
            if mt == "hub" or "to win" in sel_l or sel_l == "uavgjort":
                interesting.append(c)
            elif "btts" in sel_l or "over 2.5" in sel_l or "under 2.5" in sel_l or "over 3.5" in sel_l:
                interesting.append(c)
            elif "dnb" in sel_l or "uavgjort tilbakebetales" in mt:
                interesting.append(c)
        # always show first 8 by odds proximity to 1.5-2.2 sweet spot
        scored = sorted(cs, key=lambda c: abs(c.decimal_odds - 1.85))
        show = interesting[:12] if interesting else scored[:10]
        for c in show:
            band = odds_band(c.decimal_odds)
            hist = bands.get(band, {})
            imp = 1.0 / c.decimal_odds
            print(
                f"  {c.selection[:55]:55} @ {c.decimal_odds:5.2f}  "
                f"imp={imp*100:4.1f}%  band={band:7} histROI={hist.get('roi',0)*100:+5.1f}%"
            )

    # Shortlist: liquid markets in historically good bands, odds 1.45-2.20, not crazy longshots
    shortlist = []
    for c in candidates:
        o = c.decimal_odds
        band = odds_band(o)
        if o < 1.35 or o > 2.45:
            continue
        sel = c.selection.lower()
        mt = (c.market_type or "").lower()
        # skip exotic correct score / HTFT
        if any(x in mt for x in ("korrekt resultat", "pause/fulltid", "halvtid/fulltid")):
            continue
        if any(x in sel for x in ("og under", "og over", "og ja", "og nei")) and "btts" not in sel:
            # combo markets still ok for analysis but lower priority
            pass
        hist = bands.get(band, {})
        hist_roi = hist.get("roi", 0)
        # prefer good bands
        score = hist_roi * 10 - abs(o - 1.75)
        if band in ("1.8-2.2", "<1.5"):
            score += 0.5
        if band == "2.2-2.5":
            score -= 1.0
        shortlist.append((score, c, band, hist_roi))

    shortlist.sort(key=lambda x: x[0], reverse=True)
    print("\n=== ENGINE SHORTLIST (band-history guided, no p_model yet) ===")
    for score, c, band, hroi in shortlist[:25]:
        print(f"  score={score:+.2f}  {c.match[:40]:40} | {c.selection[:40]:40} @ {c.decimal_odds:.2f} band={band} histROI={hroi*100:+.1f}%")

    out_dir = ROOT / "outbox"
    out_dir.mkdir(exist_ok=True)
    summary_path = out_dir / f"ANALYSIS_{odds_path.stem}.md"
    lines = [
        f"# Full odds analysis — {odds_path.name}",
        "",
        f"- Equity: **{bankroll['equity_nok']:.2f} NOK** | Phase **{phase['phase_id']}** | Daily cap **{risk['daily_risk_cap_nok']:.2f}**",
        f"- Parsed **{len(candidates)}** lines across **{len(by_match)}** matches",
        f"- Ledger: ROI {overall['roi']*100:+.1f}% | {int(overall['n_settled'])} settled",
        "",
        "## Matches",
    ]
    for match, cs in by_match.items():
        lines.append(f"\n### {match}\n")
        lines.append(f"Sport: {cs[0].sport} · lines: {len(cs)}\n")
        lines.append("| Selection | Odds | Imp% | Band | Hist band ROI |")
        lines.append("|-----------|------|------|------|---------------|")
        for c in sorted(cs, key=lambda x: x.decimal_odds)[:40]:
            band = odds_band(c.decimal_odds)
            h = bands.get(band, {})
            lines.append(
                f"| {c.selection.replace('|','/')} | {c.decimal_odds:.2f} | {100/c.decimal_odds:.1f}% | {band} | {h.get('roi',0)*100:+.1f}% |"
            )
    lines.append("\n## Shortlist (history-guided)\n")
    for score, c, band, hroi in shortlist[:20]:
        lines.append(f"- `{c.match}` / **{c.selection}** @ {c.decimal_odds:.2f} (band {band}, hist ROI {hroi*100:+.1f}%, score {score:+.2f})")
    lines.append("\n## Note on p_model / recommend\n")
    lines.append(
        "CLI `recommend` requires `p_model` + evidence grade B+ (A for odds>2.5). "
        "Raw dump lines alone → all rejected with `no p_model`. "
        "Evidence packs must be added under `evidence/` for place-slip generation."
    )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {summary_path}")

    # Export structured candidates for further research
    export = []
    for c in candidates:
        export.append(
            {
                "match": c.match,
                "selection": c.selection,
                "decimal_odds": c.decimal_odds,
                "sport": c.sport,
                "market_type": c.market_type,
                "odds_band": odds_band(c.decimal_odds),
            }
        )
    exp_path = out_dir / f"PARSED_{odds_path.stem}.json"
    exp_path.write_text(json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {exp_path}")

    # Dry-run score only — do not overwrite outbox/PLACE_THESE.md (live slip)
    from nt.odds_parse import attach_evidence
    from nt.portfolio import build_portfolio

    candidates2 = parse_odds_file(odds_path)
    attach_evidence(candidates2, path_from_config(cfg, "evidence"))
    rows2 = load_bets(path_from_config(cfg, "bets"))
    picked, rejects = build_portfolio(cfg, candidates2, phase, risk, rows2)
    print("\n=== portfolio dry-score (does not write PLACE_THESE) ===")
    print(f"picked={len(picked)} rejects={len(rejects)} remaining_risk={risk['remaining_risk_nok']:.2f}")
    for r in picked:
        print(f"  {r.match} | {r.selection} @ {r.decimal_odds:.2f} stake={r.stake_nok:.0f} EV={r.ev:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
