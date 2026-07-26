from __future__ import annotations

"""
Ledger-driven learning loop.

After settle (and on `nt learn` / refresh), recomputes sport / market / band
multipliers from THIS book's settled history and persists them for recommend.

Design (conservative):
- Soft EV boost/penalty + stake multipliers (clamped)
- Min sample before leaving 1.0× / 0 boost
- Blend all-time + recent window so form moves without overreacting
- Hard soft-block only when sample is large AND ROI is deep red
- Never rewrites config.yaml — live knobs live in data/state/learning.json
"""

import json
from pathlib import Path
from typing import Any

from nt.analytics import infer_market
from nt.bets_io import fnum, load_bets, odds_band, utc_now
from nt.config import path_from_config
from nt.sport_taxonomy import normalize_sport


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _settled_sorted(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    # Performance samples only — exclude Pending/ConfirmedPlaced/Abandoned
    from nt.bets_io import is_performance_settled

    settled = [r for r in rows if is_performance_settled(r.get("result"))]
    settled.sort(key=lambda r: (r.get("date") or "", r.get("updated_at") or r.get("created_at") or ""))
    return settled


def _bucket_stats(items: list[dict[str, str]]) -> dict[str, float]:
    stake = sum(fnum(r.get("stake_nok")) or 0.0 for r in items)
    pl = sum(fnum(r.get("p_l_nok")) or 0.0 for r in items)
    wins = sum(1 for r in items if r.get("result") == "Win")
    losses = sum(1 for r in items if r.get("result") == "Loss")
    decided = wins + losses
    return {
        "n": float(len(items)),
        "stake": round(stake, 2),
        "pl": round(pl, 2),
        "roi": (pl / stake) if stake else 0.0,
        "winrate": (wins / decided) if decided else 0.0,
        "wins": float(wins),
        "losses": float(losses),
    }


def load_settlement_taxonomy_by_bet(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Latest settlement_reviews taxonomy fields keyed by bet_id.
    Later lines for the same bet_id overwrite earlier ones.
    """
    out: dict[str, dict[str, Any]] = {}
    try:
        from nt.settlement_review import settlement_reviews_path

        path = settlement_reviews_path(cfg)
        if not path.is_file():
            return out
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                bid = str(rec.get("bet_id") or "").strip()
                if not bid:
                    continue
                lw = rec.get("learning_weight")
                try:
                    lw_f = float(lw) if lw is not None else None
                except (TypeError, ValueError):
                    lw_f = None
                out[bid] = {
                    "predictability": rec.get("predictability"),
                    "variance_class": rec.get("variance_class"),
                    "learning_weight": lw_f,
                    "classified_by": rec.get("classified_by"),
                    "classification_notes": rec.get("classification_notes"),
                }
    except Exception:
        return out
    return out


def _process_weight(
    r: dict[str, str],
    learn_cfg: dict[str, Any],
    decisions: dict[str, Any],
    taxonomy_by_bet: dict[str, dict[str, Any]] | None = None,
) -> float:
    """How much this row should influence learning mults.

    Multiplies process×recency base by settlement taxonomy learning_weight
    when available (one-offs barely move mults).
    """
    mode = str(learn_cfg.get("weight_mode") or "weighted")
    if mode == "equal":
        # Still apply taxonomy so one-offs don't dominate even in equal mode
        tax_w = 1.0
        bid = r.get("bet_id") or ""
        tax = (taxonomy_by_bet or {}).get(bid) if taxonomy_by_bet else None
        if tax and tax.get("learning_weight") is not None:
            try:
                tax_w = max(0.0, min(1.0, float(tax["learning_weight"])))
            except (TypeError, ValueError):
                tax_w = 1.0
        return tax_w
    bid = r.get("bet_id") or ""
    dec = decisions.get(bid) if decisions else None
    src = (r.get("source") or "").strip()
    grade = (r.get("research_grade") or (dec or {}).get("grade") or "").upper()
    has_model = bool(dec and dec.get("p_model") is not None)

    if mode == "process_only":
        if has_model and grade in ("A", "B"):
            base = float(learn_cfg.get("full_process_weight", 1.0))
        else:
            return 0.0
    else:
        # weighted (default)
        if has_model and grade in ("A", "B"):
            base = float(learn_cfg.get("full_process_weight", 1.0))
        elif src == "era_archive":
            base = float(learn_cfg.get("archive_process_weight", 0.35))
        elif src == "recommend" or grade:
            base = float(learn_cfg.get("live_no_model_weight", 0.60))
        else:
            base = float(learn_cfg.get("archive_process_weight", 0.35))

    # half-life decay by date
    half = float(learn_cfg.get("half_life_days", 60) or 60)
    d = (r.get("date") or "").strip()
    if half > 0 and len(d) >= 10:
        try:
            from datetime import date as date_cls

            age = (date_cls.today() - date_cls.fromisoformat(d[:10])).days
            decay = 0.5 ** (max(0, age) / half)
            base *= decay
        except ValueError:
            pass

    # Taxonomy learning_weight: one-offs / true randomness barely move mults
    tax = (taxonomy_by_bet or {}).get(bid) if taxonomy_by_bet else None
    if tax and tax.get("learning_weight") is not None:
        try:
            tax_w = max(0.0, min(1.0, float(tax["learning_weight"])))
            base *= tax_w
        except (TypeError, ValueError):
            pass
    return max(0.0, base)


def _bucket_stats_weighted(
    items: list[dict[str, str]],
    learn_cfg: dict[str, Any],
    decisions: dict[str, Any],
    taxonomy_by_bet: dict[str, dict[str, Any]] | None = None,
) -> dict[str, float]:
    """ROI using process×recency×taxonomy weights; n remains raw count for min_sample gates."""
    raw = _bucket_stats(items)
    w_stake = 0.0
    w_pl = 0.0
    w_sum = 0.0
    for r in items:
        w = _process_weight(r, learn_cfg, decisions, taxonomy_by_bet)
        if w <= 0:
            continue
        st = fnum(r.get("stake_nok")) or 0.0
        pl = fnum(r.get("p_l_nok")) or 0.0
        w_stake += st * w
        w_pl += pl * w
        w_sum += w
    roi = (w_pl / w_stake) if w_stake > 1e-9 else float(raw["roi"])
    raw["roi"] = roi
    raw["roi_weighted"] = roi
    raw["weight_sum"] = round(w_sum, 2)
    return raw


def _blend_roi(all_roi: float, all_n: float, rec_roi: float, rec_n: float, recent_weight: float) -> float:
    if all_n <= 0:
        return 0.0
    if rec_n < 5:
        return all_roi
    w = _clamp(recent_weight, 0.0, 0.7)
    return (1.0 - w) * all_roi + w * rec_roi


def _signal_from_roi(
    roi: float,
    n: int,
    *,
    min_sample: int,
    stake_mult_min: float,
    stake_mult_max: float,
    stake_roi_scale: float,
    ev_boost_min: float,
    ev_boost_max: float,
    ev_roi_scale: float,
    block_min_sample: int,
    block_roi_below: float,
) -> dict[str, Any]:
    """Map blended ROI + sample → stake_mult, ev_boost, blocked, status."""
    if n < min_sample:
        return {
            "stake_mult": 1.0,
            "ev_boost": 0.0,
            "blocked": False,
            "status": "thin",
            "confidence": round(n / max(min_sample, 1), 2),
        }

    conf = _clamp(n / (min_sample * 2.5), 0.35, 1.0)
    stake_mult = _clamp(1.0 + roi * stake_roi_scale * conf, stake_mult_min, stake_mult_max)
    ev_boost = _clamp(roi * ev_roi_scale * conf, ev_boost_min, ev_boost_max)

    blocked = bool(n >= block_min_sample and roi <= block_roi_below)
    if blocked:
        status = "blocked"
    elif roi >= 0.08:
        status = "strong"
    elif roi >= 0.02:
        status = "good"
    elif roi >= -0.05:
        status = "neutral"
    elif roi >= -0.12:
        status = "weak"
    else:
        status = "poor"

    return {
        "stake_mult": round(stake_mult, 3),
        "ev_boost": round(ev_boost, 4),
        "blocked": blocked,
        "status": status,
        "confidence": round(conf, 2),
    }


def _group_learning(
    settled: list[dict[str, str]],
    key_fn,
    recent_n: int,
    learn_cfg: dict[str, Any],
    decisions: dict[str, Any] | None = None,
    taxonomy_by_bet: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    from collections import defaultdict

    decisions = decisions or {}
    taxonomy_by_bet = taxonomy_by_bet or {}
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in settled:
        k = key_fn(r)
        if not k:
            continue
        buckets[k].append(r)

    out: dict[str, dict[str, Any]] = {}
    min_sample = int(learn_cfg.get("min_sample", 12))
    recent_weight = float(learn_cfg.get("recent_weight", 0.4))
    for name, items in buckets.items():
        all_s = _bucket_stats_weighted(items, learn_cfg, decisions, taxonomy_by_bet)
        recent_items = items[-recent_n:] if recent_n > 0 else items
        rec_s = _bucket_stats_weighted(recent_items, learn_cfg, decisions, taxonomy_by_bet)
        blended = _blend_roi(
            float(all_s["roi"]),
            float(all_s["n"]),
            float(rec_s["roi"]),
            float(rec_s["n"]),
            recent_weight,
        )
        sig = _signal_from_roi(
            blended,
            int(all_s["n"]),
            min_sample=min_sample,
            stake_mult_min=float(learn_cfg.get("stake_mult_min", 0.72)),
            stake_mult_max=float(learn_cfg.get("stake_mult_max", 1.18)),
            stake_roi_scale=float(learn_cfg.get("stake_roi_scale", 0.9)),
            ev_boost_min=float(learn_cfg.get("ev_boost_min", -0.045)),
            ev_boost_max=float(learn_cfg.get("ev_boost_max", 0.035)),
            ev_roi_scale=float(learn_cfg.get("ev_roi_scale", 0.12)),
            block_min_sample=int(learn_cfg.get("block_min_sample", 20)),
            block_roi_below=float(learn_cfg.get("block_roi_below", -0.18)),
        )
        # Layered ROIs: short = last ~10 (or half recent window), medium = recent_window, long = all-time
        short_n = max(5, min(10, recent_n // 2 if recent_n else 10))
        short_items = items[-short_n:] if short_n > 0 else items
        short_s = _bucket_stats_weighted(short_items, learn_cfg, decisions, taxonomy_by_bet)
        # Explicit blend used by recommend (existing) + expose layers for UI / proposals
        layer_short = float(short_s["roi"])
        layer_medium = float(rec_s["roi"])
        layer_long = float(all_s["roi"])
        # Triple blend: short 0.35 / medium 0.40 / long 0.25 when enough sample
        if int(all_s["n"]) >= min_sample and int(rec_s["n"]) >= 5:
            triple = 0.35 * layer_short + 0.40 * layer_medium + 0.25 * layer_long
            # Keep recommend blend as primary; triple stored for transparency
            blended_out = blended
        else:
            triple = blended
            blended_out = blended
        out[name] = {
            **sig,
            "n": int(all_s["n"]),
            "roi": round(float(all_s["roi"]), 4),
            "roi_blended": round(blended_out, 4),
            "roi_recent": round(float(rec_s["roi"]), 4),
            "n_recent": int(rec_s["n"]),
            "roi_short": round(layer_short, 4),
            "n_short": int(short_s["n"]),
            "roi_long": round(layer_long, 4),
            "roi_layered": round(triple, 4),
            "pl": float(all_s["pl"]),
            "winrate": round(float(all_s["winrate"]), 4),
            "stake": float(all_s["stake"]),
            "layers": {
                "short": {"n": int(short_s["n"]), "roi": round(layer_short, 4)},
                "medium": {"n": int(rec_s["n"]), "roi": round(layer_medium, 4)},
                "long": {"n": int(all_s["n"]), "roi": round(layer_long, 4)},
                "recommend_blend": round(blended_out, 4),
                "triple_blend": round(triple, 4),
            },
        }
    return dict(sorted(out.items(), key=lambda kv: kv[1].get("n", 0), reverse=True))


def _lessons(
    settled: list[dict[str, str]],
    sports: dict[str, dict[str, Any]],
    markets: dict[str, dict[str, Any]],
    bands: dict[str, dict[str, Any]],
    *,
    max_lessons: int = 12,
) -> list[dict[str, str]]:
    lessons: list[dict[str, str]] = []

    for name, s in sports.items():
        if s.get("status") == "blocked":
            lessons.append(
                {
                    "level": "warn",
                    "scope": "sport",
                    "title": f"{name}: soft-blocked",
                    "detail": (
                        f"n={s['n']} ROI {s['roi_blended']*100:+.1f}% blended · "
                        f"stake×{s['stake_mult']} · raise bar / prefer other sports"
                    ),
                }
            )
        elif s.get("status") == "strong" and s.get("n", 0) >= 15:
            lessons.append(
                {
                    "level": "good",
                    "scope": "sport",
                    "title": f"{name}: edge working",
                    "detail": (
                        f"n={s['n']} ROI {s['roi_blended']*100:+.1f}% · "
                        f"stake×{s['stake_mult']} EV{s['ev_boost']*100:+.1f}pp"
                    ),
                }
            )
        elif s.get("status") in ("poor", "weak") and s.get("n", 0) >= 12:
            lessons.append(
                {
                    "level": "warn",
                    "scope": "sport",
                    "title": f"{name}: underperforming",
                    "detail": (
                        f"n={s['n']} ROI {s['roi_blended']*100:+.1f}% · "
                        f"stake×{s['stake_mult']} (sized down)"
                    ),
                }
            )

    for name, s in markets.items():
        if s.get("status") in ("poor", "blocked") and s.get("n", 0) >= 15:
            lessons.append(
                {
                    "level": "warn",
                    "scope": "market",
                    "title": f"Market {name}: soft",
                    "detail": f"n={s['n']} ROI {s['roi_blended']*100:+.1f}% · stake×{s['stake_mult']}",
                }
            )
        elif s.get("status") == "strong" and s.get("n", 0) >= 15:
            lessons.append(
                {
                    "level": "good",
                    "scope": "market",
                    "title": f"Market {name}: strong",
                    "detail": f"n={s['n']} ROI {s['roi_blended']*100:+.1f}% · stake×{s['stake_mult']}",
                }
            )

    for name, s in bands.items():
        if s.get("n", 0) < 15:
            continue
        if s.get("roi_blended", 0) <= -0.12:
            lessons.append(
                {
                    "level": "warn",
                    "scope": "band",
                    "title": f"Odds band {name}: cold",
                    "detail": f"n={s['n']} ROI {s['roi_blended']*100:+.1f}% · EV boost {s['ev_boost']*100:+.1f}pp",
                }
            )
        elif s.get("roi_blended", 0) >= 0.10:
            lessons.append(
                {
                    "level": "good",
                    "scope": "band",
                    "title": f"Odds band {name}: hot",
                    "detail": f"n={s['n']} ROI {s['roi_blended']*100:+.1f}% · EV boost {s['ev_boost']*100:+.1f}pp",
                }
            )

    # Recent settlement micro-lessons
    for r in settled[-5:]:
        pl = fnum(r.get("p_l_nok")) or 0.0
        res = r.get("result") or ""
        if res not in ("Win", "Loss"):
            continue
        lessons.append(
            {
                "level": "info" if res == "Win" else "warn",
                "scope": "recent",
                "title": f"{res}: {(r.get('match') or '')[:40]}",
                "detail": (
                    f"{r.get('selection')} @ {r.get('decimal_odds')} · "
                    f"P/L {pl:+.2f} · {(r.get('sport') or '?')} · band {r.get('odds_band') or odds_band(fnum(r.get('decimal_odds')) or 0)}"
                ),
            }
        )

    # Prefer warn/good, cap
    order = {"warn": 0, "good": 1, "info": 2}
    lessons.sort(key=lambda x: order.get(x.get("level", "info"), 9))
    # de-dupe titles
    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for L in lessons:
        t = L.get("title") or ""
        if t in seen:
            continue
        seen.add(t)
        uniq.append(L)
        if len(uniq) >= max_lessons:
            break
    return uniq


def _group_moves(
    prev_groups: dict[str, Any] | None,
    curr_groups: dict[str, Any],
    *,
    kind: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Compare previous vs current mults so the UI can show what actually moved."""
    prev_groups = prev_groups or {}
    moves: list[dict[str, Any]] = []
    names = set(prev_groups) | set(curr_groups)
    for name in names:
        p = prev_groups.get(name) or {}
        c = curr_groups.get(name) or {}
        if not c and not p:
            continue
        old_m = float(p.get("stake_mult") if p.get("stake_mult") is not None else 1.0)
        new_m = float(c.get("stake_mult") if c.get("stake_mult") is not None else 1.0)
        old_ev = float(p.get("ev_boost") or 0.0)
        new_ev = float(c.get("ev_boost") or 0.0)
        old_n = int(p.get("n") or 0)
        new_n = int(c.get("n") or 0)
        old_st = str(p.get("status") or "")
        new_st = str(c.get("status") or "")
        n_changed = new_n != old_n
        mult_changed = abs(new_m - old_m) >= 0.005
        ev_changed = abs(new_ev - old_ev) >= 0.0005
        st_changed = old_st != new_st and (old_st or new_st)
        if not (n_changed or mult_changed or ev_changed or st_changed):
            continue
        # Human reason
        reasons: list[str] = []
        if n_changed:
            reasons.append(f"n {old_n}→{new_n}")
        if mult_changed:
            reasons.append(f"stake ×{old_m:.3f}→×{new_m:.3f}")
        if ev_changed:
            reasons.append(f"EV {old_ev*100:+.1f}→{new_ev*100:+.1f}pp")
        if st_changed:
            reasons.append(f"status {old_st or '—'}→{new_st or '—'}")
        moves.append(
            {
                "kind": kind,
                "name": name,
                "n_from": old_n,
                "n_to": new_n,
                "stake_from": round(old_m, 3),
                "stake_to": round(new_m, 3),
                "ev_from": round(old_ev, 4),
                "ev_to": round(new_ev, 4),
                "status_from": old_st or None,
                "status_to": new_st or None,
                "delta_stake": round(new_m - old_m, 3),
                "delta_ev": round(new_ev - old_ev, 4),
                "summary": " · ".join(reasons),
            }
        )
    moves.sort(key=lambda x: (abs(float(x.get("delta_stake") or 0)), abs(float(x.get("delta_ev") or 0))), reverse=True)
    return moves[:limit]


def _recent_settlement_impacts(
    settled: list[dict[str, str]],
    sports: dict[str, dict[str, Any]],
    markets: dict[str, dict[str, Any]],
    *,
    limit: int = 12,
    taxonomy_by_bet: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Last settled bets with the group mults they currently push."""
    taxonomy_by_bet = taxonomy_by_bet or {}
    out: list[dict[str, Any]] = []
    for r in reversed(settled[-limit:]):
        sport = normalize_sport(r.get("sport"), default="unknown")
        market = infer_market(r.get("selection") or "", r.get("market_type") or "")
        sp = sports.get(sport) or {}
        mk = markets.get(market) or {}
        pl = fnum(r.get("p_l_nok")) or 0.0
        bid = str(r.get("bet_id") or "")
        tax = taxonomy_by_bet.get(bid) or {}
        out.append(
            {
                "date": r.get("date") or "",
                "match": r.get("match") or "",
                "selection": r.get("selection") or "",
                "result": r.get("result") or "",
                "pl": round(pl, 2),
                "odds": r.get("decimal_odds") or "",
                "stake_nok": r.get("stake_nok") or "",
                "sport": sport,
                "market": market,
                "sport_stake_now": sp.get("stake_mult"),
                "sport_status": sp.get("status"),
                "market_stake_now": mk.get("stake_mult"),
                "market_status": mk.get("status"),
                "predictability": tax.get("predictability"),
                "variance_class": tax.get("variance_class"),
                "learning_weight": tax.get("learning_weight"),
                "impact_hint": (
                    f"{sport} ×{sp.get('stake_mult', 1.0)} · {market} ×{mk.get('stake_mult', 1.0)}"
                    if sp or mk
                    else "new/thin group"
                ),
            }
        )
    return out


def compute_learning(
    rows: list[dict[str, str]],
    cfg: dict[str, Any],
    *,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    learn_cfg = cfg.get("learning") or {}
    if learn_cfg.get("enabled", True) is False:
        return {
            "enabled": False,
            "updated_at": utc_now(),
            "sports": {},
            "markets": {},
            "bands": {},
            "lessons": [],
            "summary": {"n_settled": 0},
            "recent_settlements": [],
            "multiplier_moves": [],
            "previous_updated_at": None,
        }

    settled = _settled_sorted(rows)
    recent_n = int(learn_cfg.get("recent_window", 30))
    try:
        from nt.decisions import load_decisions

        decisions = load_decisions(cfg)
    except Exception:
        decisions = {}

    taxonomy_by_bet = load_settlement_taxonomy_by_bet(cfg)

    sports = _group_learning(
        settled,
        lambda r: normalize_sport(r.get("sport"), default="unknown"),
        recent_n,
        learn_cfg,
        decisions,
        taxonomy_by_bet,
    )
    markets = _group_learning(
        # Prefer selection text so NT market_type strings don't fragment families
        settled,
        lambda r: infer_market(r.get("selection") or "", r.get("market_type") or ""),
        recent_n,
        learn_cfg,
        decisions,
        taxonomy_by_bet,
    )
    bands = _group_learning(
        settled,
        lambda r: (r.get("odds_band") or "").strip() or odds_band(fnum(r.get("decimal_odds")) or 0),
        recent_n,
        learn_cfg,
        decisions,
        taxonomy_by_bet,
    )

    lessons = _lessons(settled, sports, markets, bands, max_lessons=int(learn_cfg.get("max_lessons", 14)))

    # Concentration warning — healthy to explore other sports/markets
    n_all = len(settled) or 1
    foot_n = int((sports.get("football") or {}).get("n") or 0)
    foot_share = foot_n / n_all
    if foot_share >= 0.70 and foot_n >= 40:
        lessons.insert(
            0,
            {
                "level": "warn",
                "scope": "diversify",
                "title": f"Football concentration {foot_share*100:.0f}%",
                "detail": (
                    f"{foot_n}/{n_all} settled are football. Round caps: "
                    f"max {((learn_cfg.get('diversification') or {}).get('max_per_sport', 2))} "
                    f"per sport · explore boost active for thin markets/sports."
                ),
            },
        )

    min_s = int(learn_cfg.get("min_sample", 12))
    # Best: allow slightly thinner samples for early signal (explore sports)
    highlight_n = max(6, min_s // 2)
    sized_items = [(k, s) for k, s in sports.items() if s.get("n", 0) >= highlight_n]
    full_items = [(k, s) for k, s in sports.items() if s.get("n", 0) >= min_s]
    # Best = highest ROI among sized sample (positive-leaning preferred)
    best_items = sorted(
        sized_items,
        key=lambda kv: kv[1].get("roi_blended", 0),
        reverse=True,
    )[:3]
    best_names = {k for k, _ in best_items}

    # Worst must NEVER overlap best. Prefer full min-sample; only list
    # sports that are actually weak (negative ROI) or soft-blocked.
    # Previously football could be "worst" solely because it was the only
    # sport with n >= min_sample — even with strong positive ROI.
    base_worst = full_items if full_items else sized_items
    worst_pool = [(k, s) for k, s in base_worst if k not in best_names]
    weak = [
        (k, s)
        for k, s in worst_pool
        if bool(s.get("blocked")) or float(s.get("roi_blended") or 0) < 0
    ]
    worst_items = sorted(
        weak if weak else [],
        key=lambda kv: kv[1].get("roi_blended", 0),
    )[:3]

    stake_all = sum(fnum(r.get("stake_nok")) or 0.0 for r in settled)
    pl_all = sum(fnum(r.get("p_l_nok")) or 0.0 for r in settled)

    def _pack(name: str, s: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": name,
            "n": s.get("n"),
            "roi_blended": s.get("roi_blended"),
            "stake_mult": s.get("stake_mult"),
            "ev_boost": s.get("ev_boost"),
            "status": s.get("status"),
        }

    prev = previous or {}
    # Keep a fair quota per kind so market renames don't crowd out sport/band moves
    moves = (
        _group_moves(prev.get("sports"), sports, kind="sport", limit=12)
        + _group_moves(prev.get("markets"), markets, kind="market", limit=12)
        + _group_moves(prev.get("bands"), bands, kind="band", limit=12)
    )
    moves.sort(
        key=lambda x: (
            abs(float(x.get("delta_stake") or 0)),
            abs(float(x.get("delta_ev") or 0)),
            abs(int(x.get("n_to") or 0) - int(x.get("n_from") or 0)),
        ),
        reverse=True,
    )

    recent_settlements = _recent_settlement_impacts(
        settled, sports, markets, limit=12, taxonomy_by_bet=taxonomy_by_bet
    )

    # Compact taxonomy rollup for learning_history
    tax_classes: dict[str, int] = {}
    tax_weights: list[float] = []
    for bid, tax in taxonomy_by_bet.items():
        vc = str(tax.get("variance_class") or "unknown")
        tax_classes[vc] = tax_classes.get(vc, 0) + 1
        if tax.get("learning_weight") is not None:
            try:
                tax_weights.append(float(tax["learning_weight"]))
            except (TypeError, ValueError):
                pass
    mean_lw = round(sum(tax_weights) / len(tax_weights), 4) if tax_weights else None

    return {
        "enabled": True,
        "updated_at": utc_now(),
        "previous_updated_at": prev.get("updated_at"),
        "config_snapshot": {
            "min_sample": min_s,
            "recent_window": recent_n,
            "recent_weight": float(learn_cfg.get("recent_weight", 0.4)),
            "weight_mode": str(learn_cfg.get("weight_mode") or "weighted"),
            "half_life_days": float(learn_cfg.get("half_life_days", 60) or 60),
            "archive_process_weight": float(learn_cfg.get("archive_process_weight", 0.35)),
            "full_process_weight": float(learn_cfg.get("full_process_weight", 1.0)),
            "stake_mult_min": float(learn_cfg.get("stake_mult_min", 0.72)),
            "stake_mult_max": float(learn_cfg.get("stake_mult_max", 1.18)),
            "block_min_sample": int(learn_cfg.get("block_min_sample", 20)),
            "block_roi_below": float(learn_cfg.get("block_roi_below", -0.18)),
            "taxonomy_weighting": True,
        },
        "sports": sports,
        "markets": markets,
        "bands": bands,
        "lessons": lessons,
        "recent_settlements": recent_settlements,
        "multiplier_moves": moves,
        "taxonomy_summary": {
            "n_classified": len(taxonomy_by_bet),
            "mean_learning_weight": mean_lw,
            "by_variance_class": tax_classes,
        },
        "summary": {
            "n_settled": len(settled),
            "era_roi": round((pl_all / stake_all) if stake_all else 0.0, 4),
            "era_pl": round(pl_all, 2),
            "n_sports_active": len([s for s in sports.values() if s.get("n", 0) >= 5]),
            "n_blocked_sports": len([s for s in sports.values() if s.get("blocked")]),
            "n_moves": len(moves),
            "best_sports": [_pack(k, s) for k, s in best_items],
            "worst_sports": [_pack(k, s) for k, s in worst_items],
            "n_taxonomy": len(taxonomy_by_bet),
            "mean_learning_weight": mean_lw,
            "layers": {
                "short_window": max(5, min(10, recent_n // 2 if recent_n else 10)),
                "medium_window": recent_n,
                "long": "all_settled",
                "weights": {"short": 0.35, "medium": 0.40, "long": 0.25},
                "note": (
                    "Recommend still uses recent_weight blend; "
                    "roi_layered / layers.* are for UI + settlement proposals; "
                    "sample influence × settlement learning_weight (taxonomy)"
                ),
            },
        },
        "version": 4,
    }


def learning_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("learning_json"):
        return path_from_config(cfg, "learning_json")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "learning.json"


def learning_history_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("learning_history_jsonl"):
        return path_from_config(cfg, "learning_history_jsonl")
    return learning_path(cfg).parent / "learning_history.jsonl"


def append_learning_history(cfg: dict[str, Any], payload: dict[str, Any]) -> None:
    """Append compact mult snapshot for timeline charts."""
    path = learning_history_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    sports = payload.get("sports") or {}
    tax_sum = payload.get("taxonomy_summary") or {}
    snap = {
        "ts": payload.get("updated_at") or utc_now(),
        "n_settled": (payload.get("summary") or {}).get("n_settled"),
        "era_roi": (payload.get("summary") or {}).get("era_roi"),
        "n_moves": (payload.get("summary") or {}).get("n_moves"),
        "mean_learning_weight": (payload.get("summary") or {}).get("mean_learning_weight"),
        "taxonomy_summary": tax_sum,
        "sports": {
            k: {
                "n": v.get("n"),
                "stake_mult": v.get("stake_mult"),
                "ev_boost": v.get("ev_boost"),
                "roi_blended": v.get("roi_blended"),
                "status": v.get("status"),
            }
            for k, v in list(sports.items())[:20]
        },
        "markets": {
            k: {
                "n": v.get("n"),
                "stake_mult": v.get("stake_mult"),
                "ev_boost": v.get("ev_boost"),
                "roi_blended": v.get("roi_blended"),
                "status": v.get("status"),
            }
            for k, v in list((payload.get("markets") or {}).items())[:20]
        },
        "bands": {
            k: {
                "n": v.get("n"),
                "stake_mult": v.get("stake_mult"),
                "ev_boost": v.get("ev_boost"),
                "roi_blended": v.get("roi_blended"),
                "status": v.get("status"),
            }
            for k, v in list((payload.get("bands") or {}).items())[:12]
        },
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(snap, ensure_ascii=False) + "\n")


def load_learning_history(cfg: dict[str, Any], *, limit: int = 60) -> list[dict[str, Any]]:
    path = learning_history_path(cfg)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows[-limit:]


def write_learning(cfg: dict[str, Any], payload: dict[str, Any]) -> Path:
    path = learning_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Append history when mults/sample moved, or once to upgrade schema (bands, etc.)
    prev = payload.get("previous_updated_at")
    n_moves = int((payload.get("summary") or {}).get("n_moves") or 0)
    n_settled = int((payload.get("summary") or {}).get("n_settled") or 0)
    should_append = n_moves > 0 or not prev
    if not should_append:
        try:
            last = load_learning_history(cfg, limit=1)
            if not last or "bands" not in last[-1]:
                should_append = True  # schema upgrade: persist sports+markets+bands
            elif int(last[-1].get("n_settled") or 0) != n_settled:
                should_append = True
        except Exception:
            should_append = True
    if should_append:
        try:
            append_learning_history(cfg, payload)
        except Exception:
            pass

    # Markdown summary for humans / outbox-adjacent
    summary_key = "edges_summary"
    try:
        md_path = path_from_config(cfg, summary_key)
    except Exception:
        md_path = path.parent / "edges_summary.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_learning_markdown(payload), encoding="utf-8")
    return path


def load_learning(cfg: dict[str, Any]) -> dict[str, Any]:
    path = learning_path(cfg)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def run_learning(cfg: dict[str, Any], rows: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Recompute + persist learning from ledger. Safe to call after every settle."""
    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))
    previous = load_learning(cfg)
    payload = compute_learning(rows, cfg, previous=previous)
    write_learning(cfg, payload)
    return payload


def render_learning_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Learning summary (auto)",
        "",
        f"Updated: **{payload.get('updated_at', '—')}**",
        f"Settled sample: **{(payload.get('summary') or {}).get('n_settled', 0)}** · "
        f"era ROI **{((payload.get('summary') or {}).get('era_roi') or 0)*100:+.1f}%**",
        "",
        "## Sport multipliers",
        "",
        "| Sport | n | ROI (blend) | Stake × | EV boost | Status |",
        "|-------|---|-------------|---------|----------|--------|",
    ]
    for name, s in (payload.get("sports") or {}).items():
        lines.append(
            f"| {name} | {s.get('n')} | {float(s.get('roi_blended') or 0)*100:+.1f}% | "
            f"{s.get('stake_mult')} | {float(s.get('ev_boost') or 0)*100:+.1f}pp | {s.get('status')} |"
        )
    lines.extend(["", "## Market multipliers", ""])
    lines.append("| Market | n | ROI (blend) | Stake × | EV boost | Status |")
    lines.append("|--------|---|-------------|---------|----------|--------|")
    for name, s in list((payload.get("markets") or {}).items())[:20]:
        lines.append(
            f"| {name} | {s.get('n')} | {float(s.get('roi_blended') or 0)*100:+.1f}% | "
            f"{s.get('stake_mult')} | {float(s.get('ev_boost') or 0)*100:+.1f}pp | {s.get('status')} |"
        )
    lines.extend(["", "## Multiplier moves (vs previous snapshot)", ""])
    moves = payload.get("multiplier_moves") or []
    if not moves:
        lines.append("_No material mult changes vs previous file._")
    for m in moves[:15]:
        lines.append(f"- **{m.get('kind')}** `{m.get('name')}`: {m.get('summary')}")
    lines.extend(["", "## Recent settlements feeding the loop", ""])
    for r in (payload.get("recent_settlements") or [])[:10]:
        lines.append(
            f"- {r.get('date')} **{r.get('result')}** {r.get('match')} / {r.get('selection')} "
            f"P/L {r.get('pl'):+} · now {r.get('impact_hint')}"
        )
    lines.extend(["", "## Lessons", ""])
    for L in payload.get("lessons") or []:
        lines.append(f"- **[{L.get('level')}]** {L.get('title')}: {L.get('detail')}")
    lines.append("")
    return "\n".join(lines)


def lookup_sport(learning: dict[str, Any], sport: str) -> dict[str, Any]:
    if not learning:
        return {}
    key = normalize_sport(sport, default="unknown")
    sports = learning.get("sports") or {}
    if key in sports:
        return sports[key]
    # Legacy ledger keys (nba/wnba before Phase 3 collapse)
    raw = (sport or "").strip().lower()
    if raw and raw in sports:
        return sports[raw]
    return {}


def lookup_market(learning: dict[str, Any], market: str, selection: str = "") -> dict[str, Any]:
    if not learning:
        return {}
    markets = learning.get("markets") or {}
    if market and market in markets:
        return markets[market]
    inferred = infer_market(selection, market or "")
    return markets.get(inferred) or {}


def lookup_band(learning: dict[str, Any], band: str) -> dict[str, Any]:
    if not learning:
        return {}
    return (learning.get("bands") or {}).get(band) or {}


def learning_adjustments(
    learning: dict[str, Any],
    *,
    sport: str,
    market: str,
    selection: str,
    band: str,
    enabled: bool = True,
    learn_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Combine sport + market + band signals for portfolio.
    Stake mults multiply (capped). EV boosts add (capped).
    Thin groups can get a small exploration boost so we don't only bet football HUB forever.
    """
    if not enabled or not learning or not learning.get("enabled", True):
        return {
            "ev_boost": 0.0,
            "ev_boost_other": 0.0,
            "ev_boost_explore": 0.0,
            "stake_mult": 1.0,
            "blocked": False,
            "block_reason": "",
            "notes": [],
            "explored": False,
            "market_key": "",
        }

    sp = lookup_sport(learning, sport)
    mk = lookup_market(learning, market, selection)
    bd = lookup_band(learning, band)
    market_key = ""
    if mk:
        # reverse-lookup is hard; infer from selection
        market_key = infer_market(selection, market or "")
    else:
        market_key = infer_market(selection, market or "")

    notes: list[str] = []
    # Split: non-explore sport/market/band vs explore/virgin/thin extras (PR2)
    ev_other = 0.0
    ev_explore = 0.0
    stake = 1.0
    blocked = False
    block_reason = ""
    explored = False

    if sp:
        ev_other += float(sp.get("ev_boost") or 0)
        stake *= float(sp.get("stake_mult") or 1.0)
        if sp.get("n", 0) >= 8:
            notes.append(f"sport {sport or '?'}×{sp.get('stake_mult')} EV{float(sp.get('ev_boost') or 0):+.3f}")
        if sp.get("blocked"):
            blocked = True
            block_reason = f"sport '{sport}' soft-blocked (n={sp.get('n')} ROI {float(sp.get('roi_blended') or 0)*100:+.1f}%)"

    if mk:
        # Market is softer: half weight on EV, stake mult pulled toward 1
        m_ev = float(mk.get("ev_boost") or 0) * 0.6
        m_st = 1.0 + (float(mk.get("stake_mult") or 1.0) - 1.0) * 0.5
        ev_other += m_ev
        stake *= m_st
        if mk.get("n", 0) >= 12:
            notes.append(f"mkt {mk.get('status')}×{m_st:.2f}")
        if mk.get("blocked") and not blocked:
            blocked = True
            block_reason = f"market soft-blocked ({market_key or market or selection})"

    if bd:
        # Band: EV only (stake already has static high-odds mult)
        b_ev = float(bd.get("ev_boost") or 0) * 0.5
        ev_other += b_ev
        if bd.get("n", 0) >= 15:
            notes.append(f"band {band} EV{b_ev:+.3f}")

    # Exploration: under-sampled sport OR market gets a nudge so football
    # volume cannot starve thin sports/markets of sample forever.
    # All virgin/thin/prop extras go into ev_boost_explore (gated at portfolio score).
    div = (learn_cfg or {}).get("diversification") or {}
    exp_lo = int(div.get("explore_min_n", 0))  # 0 = allow virgin groups
    exp_hi = int(div.get("explore_max_n", 14))
    exp_boost = float(div.get("explore_ev_boost", 0.018))
    exp_floor = float(div.get("explore_stake_floor", 0.92))
    exp_min_roi = float(div.get("explore_min_roi", -0.15))
    virgin_boost = float(div.get("explore_virgin_ev_boost", 0.022))

    def _try_explore(group: dict[str, Any] | None, label: str, *, n_hint: int | None = None) -> None:
        nonlocal ev_explore, stake, explored
        n = int((group or {}).get("n") or 0) if group else int(n_hint or 0)
        roi = 0.0
        blocked_g = False
        if group:
            roi = float(
                group.get("roi_blended")
                if group.get("roi_blended") is not None
                else group.get("roi")
                or 0
            )
            blocked_g = bool(group.get("blocked"))
        if blocked_g:
            return
        if n == 0 and exp_lo <= 0:
            ev_explore += virgin_boost
            stake = max(stake, exp_floor)
            explored = True
            notes.append(f"explore virgin {label}")
            return
        if exp_lo <= n <= exp_hi and roi >= exp_min_roi:
            # Extra boost for thin non-football sports
            boost = exp_boost
            if label.startswith("sport:") and "football" not in label and n < 12:
                boost = exp_boost + 0.008
            # Props / period market keys
            if any(x in label.lower() for x in ("player", "period", "corner", "prop", "clean")):
                boost = exp_boost + 0.006
            ev_explore += boost
            stake = max(stake, exp_floor)
            explored = True
            notes.append(f"explore {label} n={n}")

    if not blocked:
        if not mk or int(mk.get("n") or 0) <= exp_hi:
            _try_explore(mk if mk else None, f"market:{market_key or market or 'new'}", n_hint=0 if not mk else None)
        if not sp or int(sp.get("n") or 0) <= exp_hi:
            _try_explore(sp if sp else None, f"sport:{sport or 'new'}", n_hint=0 if not sp else None)

    # Global safety clamps: keep other in range; explore only fills remaining headroom
    ev_other = _clamp(ev_other, -0.06, 0.065)
    ev_explore = max(0.0, float(ev_explore))
    headroom = 0.065 - float(ev_other)
    if headroom < 0:
        headroom = 0.0
    if ev_explore > headroom:
        ev_explore = headroom
    ev = float(ev_other) + float(ev_explore)
    stake = _clamp(stake, 0.65, 1.25)

    return {
        "ev_boost": round(ev, 4),  # sum — backward compatible
        "ev_boost_other": round(ev_other, 4),
        "ev_boost_explore": round(ev_explore, 4),
        "stake_mult": round(stake, 3),
        "blocked": blocked,
        "block_reason": block_reason,
        "notes": notes,
        "explored": explored,
        "market_key": market_key,
        "sport": sp,
        "market": mk,
        "band": bd,
    }


def diversification_limits(cfg: dict[str, Any]) -> dict[str, Any]:
    """Caps + exploration policy for portfolio construction."""
    div = dict((cfg.get("learning") or {}).get("diversification") or {})

    # Form continuity / anti-flip (PR2 portfolio wire-up enables via config.yaml)
    fc_defaults = {
        "enabled": False,  # setdefault only; config.yaml sets true after PR2
        "live_ledger_only": True,
        "anchor_scan_limit": 30,
        "max_hours": 48,
        "max_games": 2,
        "heavy_fav_max_odds": 2.10,
        "include_pending_anchors": True,
        "base_penalty": 0.035,
        "win_penalty": 0.035,
        "pending_penalty": 0.015,
        "weak_extra_penalty": 0.025,
        "convincing_win_mult": 1.25,
        "weak_flip_action": "soft_reject",
        "strong_flip_min_ev": 0.06,
        "weak_phrase_blocklist": [],
        "heavy_line_by_sport": {
            "baseball": 1.5,
            "basketball": 5.5,
            "football": 1.5,
            "ice_hockey": 1.5,
            "tennis": 2.5,
            "darts": 2.5,
            "esports": 1.5,
            "default": 1.5,
        },
    }
    fc = dict(fc_defaults)
    fc_in = div.get("form_continuity") if isinstance(div.get("form_continuity"), dict) else {}
    fc.update(fc_in)
    # Nested heavy_line_by_sport merge
    hlines = dict(fc_defaults["heavy_line_by_sport"])
    if isinstance(fc_in.get("heavy_line_by_sport"), dict):
        hlines.update(fc_in["heavy_line_by_sport"])
    fc["heavy_line_by_sport"] = hlines
    # Alias: win_penalty ↔ base_penalty
    if "base_penalty" in fc_in and "win_penalty" not in fc_in:
        fc["win_penalty"] = fc["base_penalty"]
    if "win_penalty" in fc_in and "base_penalty" not in fc_in:
        fc["base_penalty"] = fc["win_penalty"]

    rg_defaults = {
        "enabled": False,
        "max_per_slip": 1,
        "ev_slack": 0.015,
        "soft_skip_reason": "ranking_gap_hc: soft cap 1 per slip",
    }
    rg = dict(rg_defaults)
    rg_in = div.get("ranking_gap_hc") if isinstance(div.get("ranking_gap_hc"), dict) else {}
    rg.update(rg_in)

    sort_in = div.get("sort") if isinstance(div.get("sort"), dict) else {}
    sort_cfg = {
        "similar_penalty_weight": float(sort_in.get("similar_penalty_weight", 1.0)),
        "macro_underrep_bonus": float(sort_in.get("macro_underrep_bonus", 0.004)),
        "explore_tiebreak": bool(sort_in.get("explore_tiebreak", True)),
        "continuity_penalty_weight": float(sort_in.get("continuity_penalty_weight", 1.0)),
    }

    return {
        "max_per_sport": int(div.get("max_per_sport", 2)),
        "max_per_market": int(div.get("max_per_market", 2)),
        "max_per_band": int(div.get("max_per_band", 3)),
        "max_per_match": int(div.get("max_per_match", 1)),
        # When non-football candidates exist, leave room for them
        "max_football_per_round": int(div.get("max_football_per_round", 1)),
        "min_non_football_per_round": int(div.get("min_non_football_per_round", 1)),
        "explore_min_ev": float(div.get("explore_min_ev", 0.012)),
        "explore_base_ev_min": float(div.get("explore_base_ev_min", 0.005)),
        "prefer_explore_first": bool(div.get("prefer_explore_first", True)),
        # P1 soft correlation
        "max_per_league": int(div.get("max_per_league", 2)),
        "max_per_script_family": int(div.get("max_per_script_family", 2)),
        "ko_window_hours": float(div.get("ko_window_hours", 3)),
        "max_per_ko_window": int(div.get("max_per_ko_window", 2)),
        # Form continuity + ranking-gap (nested; enabled false in PR1)
        "form_continuity": fc,
        "ranking_gap_hc": rg,
        "sort": sort_cfg,
    }
