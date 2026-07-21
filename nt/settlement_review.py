from __future__ import annotations

"""
Post-settlement analysis + learning proposals.

After settle, evaluates research quality vs outcome, separates skill vs variance,
and proposes multiplier / reliability updates for human accept/reject.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from nt.analytics import infer_market
from nt.bets_io import fnum, load_bets, odds_band, utc_now
from nt.config import path_from_config
from nt.learning import load_learning, learning_path


def settlement_reviews_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("settlement_reviews_jsonl"):
        return path_from_config(cfg, "settlement_reviews_jsonl")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "settlement_reviews.jsonl"


def learning_proposals_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("learning_proposals_json"):
        return path_from_config(cfg, "learning_proposals_json")
    state = path_from_config(cfg, "state_dir") if paths.get("state_dir") else Path("data/state")
    return state / "learning_proposals.json"


def _load_decisions(cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        from nt.decisions import load_decisions

        return load_decisions(cfg) or {}
    except Exception:
        return {}


def _classify_variance(
    *,
    result: str,
    p_model: float | None,
    odds: float,
    variance_tag: str | None,
    research_quality_retro: str | None,
) -> dict[str, Any]:
    """
    Heuristic skill vs variance label.
    - variance_tag from user overrides when present
    - else: high p_model loss → bad luck / process miss; low p_model win → variance up
    """
    tag = (variance_tag or "").strip().lower()
    if tag in ("variance", "luck", "noise", "random"):
        return {"label": "variance", "weight": 0.35, "detail": "User marked as variance/luck"}
    if tag in ("skill", "edge", "expected", "process"):
        return {"label": "skill", "weight": 1.0, "detail": "User marked as expected/skill"}
    if tag in ("process_error", "research_miss", "miss"):
        return {"label": "process_error", "weight": 1.15, "detail": "User marked research miss"}

    retro = (research_quality_retro or "").strip().lower()
    if retro in ("poor", "wrong", "miss"):
        return {"label": "process_error", "weight": 1.2, "detail": "Retro research quality poor"}
    if retro in ("good", "solid", "correct"):
        base_w = 0.9
    else:
        base_w = 1.0

    if p_model is None or not (0 < p_model < 1):
        return {"label": "unknown", "weight": 0.7 * base_w, "detail": "No p_model — moderate weight"}

    implied = (1.0 / odds) if odds and odds > 1 else 0.5
    edge = p_model - implied

    if result == "Win":
        if p_model >= 0.62:
            return {"label": "skill", "weight": 1.0 * base_w, "detail": f"Win with p={p_model:.2f} (edge {edge:+.2f})"}
        if p_model <= 0.48:
            return {"label": "variance", "weight": 0.4 * base_w, "detail": f"Upset win p={p_model:.2f} — downweight"}
        return {"label": "mixed", "weight": 0.75 * base_w, "detail": f"Win p={p_model:.2f}"}
    if result == "Loss":
        if p_model >= 0.68:
            return {
                "label": "variance",
                "weight": 0.45 * base_w,
                "detail": f"Loss despite high p={p_model:.2f} — protect edge",
            }
        if p_model <= 0.52 and edge < 0.02:
            return {
                "label": "process_error",
                "weight": 1.1 * base_w,
                "detail": f"Loss on thin/no edge p={p_model:.2f}",
            }
        return {"label": "skill", "weight": 0.95 * base_w, "detail": f"Loss p={p_model:.2f} — learning signal"}
    return {"label": "neutral", "weight": 0.5, "detail": result}


def analyze_settled_batch(
    cfg: dict[str, Any],
    settled_items: list[dict[str, Any]],
    *,
    rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Analyze just-settled bets (list of dicts with bet_id + optional rich fields).
    """
    if rows is None:
        rows = load_bets(path_from_config(cfg, "bets"))
    by_id = {r.get("bet_id"): r for r in rows}
    decisions = _load_decisions(cfg)
    learning = load_learning(cfg)

    reviews: list[dict[str, Any]] = []
    skill_pl = 0.0
    var_pl = 0.0
    process_hits = 0
    process_misses = 0

    for item in settled_items:
        bid = item.get("bet_id") or ""
        bet = by_id.get(bid) or {}
        if not bet:
            continue
        dec = decisions.get(bid) or {}
        p_model = dec.get("p_model")
        if p_model is None:
            # try notes recovery
            try:
                p_model = float(item.get("p_model")) if item.get("p_model") is not None else None
            except (TypeError, ValueError):
                p_model = None
        try:
            p_model_f = float(p_model) if p_model is not None else None
        except (TypeError, ValueError):
            p_model_f = None

        odds = fnum(bet.get("decimal_odds")) or 0.0
        pl = fnum(bet.get("p_l_nok")) or 0.0
        result = bet.get("result") or item.get("result") or ""
        implied = (1.0 / odds) if odds > 1 else None
        edge = (p_model_f - implied) if (p_model_f is not None and implied is not None) else None

        cls = _classify_variance(
            result=result,
            p_model=p_model_f,
            odds=odds,
            variance_tag=item.get("variance_tag") or item.get("feel"),
            research_quality_retro=item.get("research_quality_retro")
            or item.get("research_retro"),
        )

        research_ok = None
        if result == "Win" and p_model_f and p_model_f >= 0.55:
            research_ok = True
            process_hits += 1
        elif result == "Loss" and p_model_f and p_model_f < 0.55:
            research_ok = True  # correctly low confidence
            process_hits += 1
        elif result == "Loss" and edge is not None and edge > 0.05 and cls["label"] == "process_error":
            research_ok = False
            process_misses += 1
        elif result == "Loss" and p_model_f and p_model_f >= 0.65 and cls["label"] == "variance":
            research_ok = True  # process ok, variance
            process_hits += 1

        if cls["label"] == "variance":
            var_pl += pl
        else:
            skill_pl += pl * float(cls.get("weight") or 1)

        factors = {
            "sport": (bet.get("sport") or "").lower() or "unknown",
            "market": infer_market(bet.get("selection") or "", bet.get("market_type") or ""),
            "band": bet.get("odds_band") or odds_band(odds),
            "grade": bet.get("research_grade") or dec.get("grade") or "",
            "phase": bet.get("phase") or "",
        }

        review = {
            "ts": utc_now(),
            "bet_id": bid,
            "match": bet.get("match"),
            "selection": bet.get("selection"),
            "result": result,
            "pl": pl,
            "odds": odds,
            "p_model": p_model_f,
            "implied": round(implied, 4) if implied else None,
            "edge": round(edge, 4) if edge is not None else None,
            "score": item.get("score") or item.get("actual_score"),
            "key_events": item.get("key_events"),
            "variance_class": cls["label"],
            "learning_weight": round(float(cls["weight"]), 3),
            "variance_detail": cls["detail"],
            "research_ok": research_ok,
            "research_quality_retro": item.get("research_quality_retro")
            or item.get("research_retro"),
            "confidence_retro": item.get("confidence_retro"),
            "factors": factors,
            "notes": item.get("notes") or item.get("settlement_notes"),
            "auto_fetched": bool(item.get("auto_fetched")),
        }
        reviews.append(review)

    # Aggregate factor notes
    sport_pl: dict[str, float] = defaultdict(float)
    market_pl: dict[str, float] = defaultdict(float)
    for r in reviews:
        f = r.get("factors") or {}
        sport_pl[str(f.get("sport"))] += float(r.get("pl") or 0)
        market_pl[str(f.get("market"))] += float(r.get("pl") or 0)

    predictive = sorted(sport_pl.items(), key=lambda kv: kv[1], reverse=True)
    anti = sorted(sport_pl.items(), key=lambda kv: kv[1])

    summary = {
        "n": len(reviews),
        "total_pl": round(sum(float(r.get("pl") or 0) for r in reviews), 2),
        "skill_weighted_pl": round(skill_pl, 2),
        "variance_pl": round(var_pl, 2),
        "process_hits": process_hits,
        "process_misses": process_misses,
        "most_predictive_sports": [{"name": k, "pl": round(v, 2)} for k, v in predictive[:3] if v != 0],
        "least_predictive_sports": [{"name": k, "pl": round(v, 2)} for k, v in anti[:3] if v != 0],
        "markets": [{"name": k, "pl": round(v, 2)} for k, v in sorted(market_pl.items(), key=lambda x: -x[1])[:5]],
    }

    proposals = build_learning_proposals(cfg, reviews, learning)

    report = {
        "ts": utc_now(),
        "summary": summary,
        "reviews": reviews,
        "proposals": proposals,
        "narrative": _narrative(summary, reviews, proposals),
    }

    # Persist reviews
    path = settlement_reviews_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in reviews:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Persist proposals for UI accept/reject
    if proposals:
        pp = learning_proposals_path(cfg)
        existing = load_learning_proposals(cfg)
        # merge by id
        by_key = {p.get("id"): p for p in existing.get("proposals") or [] if p.get("status") == "pending"}
        for p in proposals:
            by_key[p["id"]] = p
        payload = {
            "updated_at": utc_now(),
            "proposals": list(by_key.values()),
            "last_batch_summary": summary,
            "last_narrative": report["narrative"],
        }
        pp.parent.mkdir(parents=True, exist_ok=True)
        pp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # Auto-resolve proposals (agent/operator not required to click accept)
        learn_cfg = cfg.get("learning") or {}
        if bool(learn_cfg.get("auto_apply_proposals", True)):
            auto = auto_resolve_learning_proposals(cfg)
            report["auto_learning"] = auto

    # Human receipt
    try:
        outbox = path_from_config(cfg, "outbox")
        outbox.mkdir(parents=True, exist_ok=True)
        md = render_review_markdown(report)
        (outbox / "SETTLEMENT_ANALYSIS.md").write_text(md, encoding="utf-8")
    except Exception:
        pass

    return report


def _narrative(summary: dict[str, Any], reviews: list[dict[str, Any]], proposals: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    n = summary.get("n") or 0
    if n == 0:
        return ["No settlements to analyze."]
    lines.append(
        f"Settled **{n}** · total P/L **{summary.get('total_pl'):+}** · "
        f"skill-weighted ≈ **{summary.get('skill_weighted_pl'):+}** · "
        f"variance bucket **{summary.get('variance_pl'):+}**."
    )
    if summary.get("process_misses"):
        lines.append(
            f"{summary['process_misses']} look like **process/research misses** "
            f"(not pure variance) — review evidence quality."
        )
    if summary.get("process_hits"):
        lines.append(f"{summary['process_hits']} aligned with model/process expectations.")
    for r in reviews:
        if r.get("variance_class") == "variance" and r.get("result") == "Loss":
            lines.append(
                f"Protect edge on **{(r.get('match') or '')[:40]}**: high-p loss tagged variance "
                f"(p={r.get('p_model')})."
            )
        if r.get("research_ok") is False:
            lines.append(
                f"Research miss signal: **{(r.get('match') or '')[:40]}** / {r.get('selection')} "
                f"— consider lower grade or tighter EV bar."
            )
    if proposals:
        lines.append(f"**{len(proposals)} learning proposal(s)** ready to accept/reject in Research → Learnings.")
    return lines


def build_learning_proposals(
    cfg: dict[str, Any],
    reviews: list[dict[str, Any]],
    learning: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Propose stake/EV tweaks from this batch + layered context.
    Does NOT apply automatically.
    """
    learning = learning or {}
    learn_cfg = cfg.get("learning") or {}
    proposals: list[dict[str, Any]] = []

    # Per sport aggregate in this batch with learning weights
    sport_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"pl": 0.0, "w": 0.0, "n": 0.0})
    market_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"pl": 0.0, "w": 0.0, "n": 0.0})

    for r in reviews:
        f = r.get("factors") or {}
        sp = str(f.get("sport") or "unknown")
        mk = str(f.get("market") or "unknown")
        w = float(r.get("learning_weight") or 1.0)
        pl = float(r.get("pl") or 0.0)
        sport_stats[sp]["pl"] += pl * w
        sport_stats[sp]["w"] += w
        sport_stats[sp]["n"] += 1
        market_stats[mk]["pl"] += pl * w
        market_stats[mk]["w"] += w
        market_stats[mk]["n"] += 1

    sports_live = learning.get("sports") or {}
    markets_live = learning.get("markets") or {}

    for sp, st in sport_stats.items():
        if st["n"] < 1:
            continue
        live = sports_live.get(sp) or {}
        cur_mult = float(live.get("stake_mult") or 1.0)
        cur_ev = float(live.get("ev_boost") or 0.0)
        n_hist = int(live.get("n") or 0)
        # Short-term nudge from this batch
        batch_roi_proxy = st["pl"] / max(st["w"] * 12.0, 1.0)  # rough
        # Layer blend: short (batch) 0.45, medium (live recent) 0.35, long (live all) 0.20
        long_roi = float(live.get("roi") or live.get("roi_blended") or 0.0)
        med_roi = float(live.get("roi_recent") or long_roi)
        short_roi = max(-0.5, min(0.5, batch_roi_proxy))
        layered = 0.45 * short_roi + 0.35 * med_roi + 0.20 * long_roi

        # Confidence lower when history thin
        conf = min(1.0, (n_hist + st["n"]) / max(int(learn_cfg.get("min_sample", 12)), 1))
        delta_stake = max(-0.08, min(0.08, layered * 0.5 * conf))
        delta_ev = max(-0.02, min(0.02, layered * 0.08 * conf))

        if abs(delta_stake) < 0.01 and abs(delta_ev) < 0.003:
            continue

        proposed_stake = round(max(0.72, min(1.18, cur_mult + delta_stake)), 3)
        proposed_ev = round(max(-0.045, min(0.035, cur_ev + delta_ev)), 4)

        if proposed_stake == cur_mult and abs(proposed_ev - cur_ev) < 0.0005:
            continue

        proposals.append(
            {
                "id": f"sport:{sp}:{utc_now()[:13]}",
                "kind": "sport",
                "name": sp,
                "status": "pending",
                "created_at": utc_now(),
                "current": {"stake_mult": cur_mult, "ev_boost": cur_ev, "n": n_hist},
                "proposed": {"stake_mult": proposed_stake, "ev_boost": proposed_ev},
                "delta": {
                    "stake_mult": round(proposed_stake - cur_mult, 3),
                    "ev_boost": round(proposed_ev - cur_ev, 4),
                },
                "layers": {
                    "short_roi": round(short_roi, 4),
                    "medium_roi": round(med_roi, 4),
                    "long_roi": round(long_roi, 4),
                    "blended": round(layered, 4),
                    "confidence": round(conf, 2),
                },
                "reason": (
                    f"Batch n={int(st['n'])} weighted P/L {st['pl']:+.1f} · "
                    f"layered ROI {layered*100:+.1f}% · hist n={n_hist}"
                ),
                "source": "settlement_review",
            }
        )

    for mk, st in market_stats.items():
        if st["n"] < 1 or mk in ("", "unknown"):
            continue
        live = markets_live.get(mk) or {}
        cur_mult = float(live.get("stake_mult") or 1.0)
        cur_ev = float(live.get("ev_boost") or 0.0)
        n_hist = int(live.get("n") or 0)
        batch_roi_proxy = st["pl"] / max(st["w"] * 12.0, 1.0)
        long_roi = float(live.get("roi") or live.get("roi_blended") or 0.0)
        med_roi = float(live.get("roi_recent") or long_roi)
        short_roi = max(-0.5, min(0.5, batch_roi_proxy))
        layered = 0.50 * short_roi + 0.30 * med_roi + 0.20 * long_roi
        conf = min(1.0, (n_hist + st["n"]) / max(int(learn_cfg.get("min_sample", 12)), 1))
        delta_stake = max(-0.06, min(0.06, layered * 0.45 * conf))
        delta_ev = max(-0.015, min(0.015, layered * 0.07 * conf))
        if abs(delta_stake) < 0.012 and abs(delta_ev) < 0.004:
            continue
        proposed_stake = round(max(0.72, min(1.18, cur_mult + delta_stake)), 3)
        proposed_ev = round(max(-0.045, min(0.035, cur_ev + delta_ev)), 4)
        proposals.append(
            {
                "id": f"market:{mk}:{utc_now()[:13]}",
                "kind": "market",
                "name": mk,
                "status": "pending",
                "created_at": utc_now(),
                "current": {"stake_mult": cur_mult, "ev_boost": cur_ev, "n": n_hist},
                "proposed": {"stake_mult": proposed_stake, "ev_boost": proposed_ev},
                "delta": {
                    "stake_mult": round(proposed_stake - cur_mult, 3),
                    "ev_boost": round(proposed_ev - cur_ev, 4),
                },
                "layers": {
                    "short_roi": round(short_roi, 4),
                    "medium_roi": round(med_roi, 4),
                    "long_roi": round(long_roi, 4),
                    "blended": round(layered, 4),
                    "confidence": round(conf, 2),
                },
                "reason": f"Market batch n={int(st['n'])} · layered {layered*100:+.1f}%",
                "source": "settlement_review",
            }
        )

    return proposals


def load_learning_proposals(cfg: dict[str, Any]) -> dict[str, Any]:
    path = learning_proposals_path(cfg)
    if not path.is_file():
        return {"proposals": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"proposals": []}
    except Exception:
        return {"proposals": []}


def auto_resolve_learning_proposals(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Agent-owned learning decisions — no human approve step.

    Policy (conservative on thin samples):
    - Always resolve every *pending* proposal (accept or reject) so nothing sits idle.
    - Accept when |delta stake| or |delta EV| is non-trivial and confidence ≥ 0.15.
    - Soften large haircuts when hist n < 3: clamp stake delta to ±0.04, EV to ±0.01.
    - Reject noise when both deltas are essentially zero (should not appear).
    """
    payload = load_learning_proposals(cfg)
    pending = [p for p in (payload.get("proposals") or []) if p.get("status") == "pending"]
    accepted: list[str] = []
    rejected: list[str] = []
    modified: list[str] = []

    for p in pending:
        pid = str(p.get("id") or "")
        layers = p.get("layers") or {}
        conf = float(layers.get("confidence") or 0.0)
        cur = p.get("current") or {}
        prop = dict(p.get("proposed") or {})
        d_stake = float(prop.get("stake_mult", 1.0)) - float(cur.get("stake_mult", 1.0))
        d_ev = float(prop.get("ev_boost", 0.0)) - float(cur.get("ev_boost", 0.0))
        n_hist = int(cur.get("n") or 0)

        if abs(d_stake) < 0.005 and abs(d_ev) < 0.001:
            res = apply_learning_proposal(cfg, pid, action="reject")
            if res.get("ok"):
                rejected.append(pid)
            continue

        # Thin sample: shrink overreaction
        soft = conf < 0.25 or n_hist < 3
        if soft:
            cur_s = float(cur.get("stake_mult") or 1.0)
            cur_e = float(cur.get("ev_boost") or 0.0)
            d_stake = max(-0.04, min(0.04, d_stake))
            d_ev = max(-0.01, min(0.01, d_ev))
            mod = {
                "stake_mult": round(max(0.72, min(1.18, cur_s + d_stake)), 3),
                "ev_boost": round(max(-0.045, min(0.035, cur_e + d_ev)), 4),
            }
            res = apply_learning_proposal(cfg, pid, action="modify", modified=mod)
            if res.get("ok"):
                modified.append(pid)
            continue

        if conf < 0.15:
            res = apply_learning_proposal(cfg, pid, action="reject")
            if res.get("ok"):
                rejected.append(pid)
            continue

        res = apply_learning_proposal(cfg, pid, action="accept")
        if res.get("ok"):
            accepted.append(pid)

    return {
        "accepted": accepted,
        "modified": modified,
        "rejected": rejected,
        "n_resolved": len(accepted) + len(modified) + len(rejected),
        "policy": "auto_agent_no_human_approve",
    }


def apply_learning_proposal(
    cfg: dict[str, Any],
    proposal_id: str,
    *,
    action: str = "accept",
    modified: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Accept / reject / modify a pending proposal.
    Accept writes into learning.json sports/markets mults.
    """
    payload = load_learning_proposals(cfg)
    proposals = payload.get("proposals") or []
    found = None
    for p in proposals:
        if p.get("id") == proposal_id:
            found = p
            break
    if not found:
        return {"ok": False, "error": "proposal not found"}

    if action == "reject":
        found["status"] = "rejected"
        found["resolved_at"] = utc_now()
        _save_proposals(cfg, payload)
        return {"ok": True, "action": "reject", "proposal": found}

    learning = load_learning(cfg)
    if not learning:
        from nt.learning import run_learning

        learning = run_learning(cfg)

    kind = found.get("kind")
    name = found.get("name")
    prop = dict(found.get("proposed") or {})
    if action == "modify" and modified:
        prop.update(modified)

    group_key = "sports" if kind == "sport" else "markets" if kind == "market" else "bands"
    groups = learning.setdefault(group_key, {})
    bucket = dict(groups.get(name) or {})
    bucket["stake_mult"] = float(prop.get("stake_mult") or bucket.get("stake_mult") or 1.0)
    bucket["ev_boost"] = float(prop.get("ev_boost") or bucket.get("ev_boost") or 0.0)
    bucket["proposal_applied_at"] = utc_now()
    bucket["proposal_id"] = proposal_id
    # mark status lightly
    if bucket.get("n", 0) < 12:
        bucket["status"] = bucket.get("status") or "thin"
    groups[name] = bucket
    learning["updated_at"] = utc_now()
    learning.setdefault("summary", {})["last_proposal_action"] = action

    path = learning_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(learning, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    found["status"] = "accepted" if action == "accept" else "modified"
    found["resolved_at"] = utc_now()
    found["applied"] = prop
    _save_proposals(cfg, payload)

    return {"ok": True, "action": action, "proposal": found, "learning_path": str(path)}


def _save_proposals(cfg: dict[str, Any], payload: dict[str, Any]) -> None:
    path = learning_proposals_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = utc_now()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_review_markdown(report: dict[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        "# Settlement analysis",
        "",
        f"Generated: **{report.get('ts')}**",
        "",
        "## Summary",
        f"- Settled: **{s.get('n')}** · P/L **{s.get('total_pl'):+}**",
        f"- Skill-weighted P/L: **{s.get('skill_weighted_pl'):+}**",
        f"- Variance bucket P/L: **{s.get('variance_pl'):+}**",
        f"- Process hits / misses: **{s.get('process_hits')}** / **{s.get('process_misses')}**",
        "",
        "## Narrative",
    ]
    for n in report.get("narrative") or []:
        lines.append(f"- {n}")
    lines.extend(["", "## Per-bet review", ""])
    for r in report.get("reviews") or []:
        lines.append(
            f"- **{r.get('result')}** `{r.get('bet_id')}` {(r.get('match') or '')[:48]} / "
            f"{r.get('selection')} · P/L {r.get('pl'):+} · p={r.get('p_model')} · "
            f"**{r.get('variance_class')}** (w={r.get('learning_weight')}) · {r.get('variance_detail')}"
        )
        if r.get("score"):
            lines.append(f"  - Score: {r.get('score')}")
    lines.extend(["", "## Learning proposals", ""])
    props = report.get("proposals") or []
    if not props:
        lines.append("_No material proposals from this batch._")
    for p in props:
        lines.append(
            f"- **{p.get('kind')}** `{p.get('name')}`: "
            f"stake ×{p.get('current', {}).get('stake_mult')} → ×{p.get('proposed', {}).get('stake_mult')} · "
            f"EV {float(p.get('current', {}).get('ev_boost') or 0)*100:+.1f} → "
            f"{float(p.get('proposed', {}).get('ev_boost') or 0)*100:+.1f}pp"
        )
        lines.append(f"  - {p.get('reason')}")
    lines.append("")
    return "\n".join(lines)
