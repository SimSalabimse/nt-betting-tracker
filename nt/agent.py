from __future__ import annotations

"""
Optional AI agent — assist only, rules-enforced.

- Never writes bets.csv or settles without human-driven CLI paths.
- Tool calling is local-first; LLM is optional (xAI / OpenAI).
- All turns can be audited to data/state/agent_audit.jsonl.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from nt.analytics import deep_dive, filter_rows, overall_stats
from nt.bankroll import compute_bankroll
from nt.bets_io import load_bets, utc_now
from nt.config import load_config, path_from_config
from nt.defaults import agent_cfg
from nt.edges import query_edges, summarize_edges
from nt.evidence import grade_evidence, load_evidence
from nt.paths import ROOT, resolve
from nt.phase import evaluate_phase, load_phase_state
from nt.recommend import refresh_state, run_recommend
from nt.research import critique_pack, p_model_report
from nt.risk import evaluate_risk


def _audit_path(cfg: dict[str, Any]) -> Path:
    ac = agent_cfg(cfg)
    return resolve(ac.get("audit_log") or "data/state/agent_audit.jsonl")


def audit(cfg: dict[str, Any], record: dict[str, Any]) -> None:
    path = _audit_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(record)
    rec.setdefault("ts", utc_now())
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def tool_get_status(cfg: dict[str, Any], _args: dict[str, Any] | None = None) -> dict[str, Any]:
    bankroll, phase, risk = refresh_state(cfg)
    return {
        "equity_nok": bankroll["equity_nok"],
        "realized_pl_nok": bankroll["realized_pl_nok"],
        "pending_at_risk_nok": bankroll["pending_at_risk_nok"],
        "phase_id": phase["phase_id"],
        "label": phase.get("label"),
        "daily_risk_cap_nok": risk["daily_risk_cap_nok"],
        "remaining_risk_nok": risk["remaining_risk_nok"],
        "can_bet": risk["can_bet"],
        "reasons": risk.get("reasons"),
        "rolling_roi": phase.get("rolling_roi"),
    }


def tool_ledger_summary(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    rows = load_bets(path_from_config(cfg, "bets"))
    baseline = float(cfg["bankroll"]["baseline_nok"])
    bankroll = compute_bankroll(cfg)
    prev = load_phase_state(cfg)
    phase = evaluate_phase(
        cfg,
        bankroll["equity_nok"],
        bankroll["settled_count"],
        rows,
        current_phase=prev["phase_id"] if prev else None,
    )
    dive = deep_dive(rows, baseline, cfg, phase)
    return {
        "overall": dive["overall"],
        "max_drawdown": dive["max_drawdown"],
        "streaks": dive["streaks"],
        "concentration": dive.get("concentration"),
        "by_sport_keys": list((dive.get("by_sport") or {}).keys())[:20],
        "hints_note": "Use nt analyze for full attribution markdown.",
    }


def tool_query_bets(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    rows = load_bets(path_from_config(cfg, "bets"))
    filtered = filter_rows(
        rows,
        sport=args.get("sport"),
        odds_band=args.get("odds_band"),
        result=args.get("result"),
        phase=args.get("phase"),
        grade=args.get("grade"),
        source=args.get("source"),
        market=args.get("market"),
        date_from=args.get("date_from"),
        date_to=args.get("date_to"),
        query=args.get("query"),
    )
    limit = int(args.get("limit") or 30)
    slim = []
    for r in filtered[-limit:]:
        slim.append(
            {
                "bet_id": r.get("bet_id"),
                "date": r.get("date"),
                "match": r.get("match"),
                "selection": r.get("selection"),
                "decimal_odds": r.get("decimal_odds"),
                "stake_nok": r.get("stake_nok"),
                "result": r.get("result"),
                "p_l_nok": r.get("p_l_nok"),
                "sport": r.get("sport"),
                "odds_band": r.get("odds_band"),
                "research_grade": r.get("research_grade"),
                "phase": r.get("phase"),
            }
        )
    return {"n_matched": len(filtered), "returned": len(slim), "rows": slim}


def tool_query_edges(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    rows = query_edges(
        cfg,
        last=int(args.get("last") or 30),
        result=args.get("result"),
        phase=args.get("phase"),
        grade=args.get("grade"),
        q=args.get("q"),
        sport=args.get("sport"),
    )
    return {"summary": summarize_edges(rows), "rows": rows}


def tool_get_learning(cfg: dict[str, Any], _args: dict[str, Any] | None = None) -> dict[str, Any]:
    from nt.learning import load_learning

    learn = load_learning(cfg) or {}
    summary = learn.get("summary") or {}
    return {
        "updated_at": learn.get("updated_at"),
        "summary": summary,
        "lessons": learn.get("lessons") or [],
        "blocked_sports": list((learn.get("sports") or {}).keys())[:5],
    }


def tool_grade_evidence(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    path = Path(args.get("path") or "")
    if not path.is_absolute():
        path = ROOT / path
    odds = float(args.get("odds") or 1.90)
    return critique_pack(cfg, path, odds=odds)


def tool_dry_run_recommend(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    ac = agent_cfg(cfg)
    if not ac.get("allow_cli_dry_run", True):
        return {"error": "dry_run_recommend disabled in config"}
    args = args or {}
    odds = Path(args.get("odds") or "")
    if not odds.is_absolute():
        odds = ROOT / odds
    if not odds.exists():
        return {"error": f"odds file not found: {odds}"}
    result = run_recommend(cfg, odds, log_pending=False)
    return result


def tool_list_evidence(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    d = path_from_config(cfg, "evidence")
    if not d.is_dir():
        return {"files": []}
    files = sorted(p.name for p in d.glob("*.json"))
    limit = int(args.get("limit") or 50)
    return {"n": len(files), "files": files[:limit]}


def tool_ev_calc(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    return p_model_report(cfg, float(args["odds"]), float(args["p_model"]))


def tool_project_bankroll(cfg: dict[str, Any], args: dict[str, Any] | None = None) -> dict[str, Any]:
    from nt.project import simulate_paths

    args = args or {}
    result = simulate_paths(
        cfg,
        years=args.get("years"),
        sims=int(args.get("sims") or 500),
        roi=args.get("roi"),
        bets_per_week=args.get("bets_per_week"),
    )
    return {
        "start_equity": result["start_equity"],
        "assumptions": result["assumptions"],
        "final_equity": result["final_equity"],
        "stress_hit_rate": result["stress_hit_rate"],
        "disclaimer": result["disclaimer"],
    }


TOOL_REGISTRY: dict[str, Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]]] = {
    "get_status": tool_get_status,
    "get_ledger_summary": tool_ledger_summary,
    "query_bets": tool_query_bets,
    "query_edges": tool_query_edges,
    "get_learning": tool_get_learning,
    "grade_evidence_file": tool_grade_evidence,
    "dry_run_recommend": tool_dry_run_recommend,
    "list_evidence": tool_list_evidence,
    "ev_calc": tool_ev_calc,
    "project_bankroll": tool_project_bankroll,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Live equity, phase, daily risk, can_bet",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ledger_summary",
            "description": "Overall stats, drawdown, streaks from era ledger",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_bets",
            "description": "Filter bets from data/bets.csv (capped)",
            "parameters": {
                "type": "object",
                "properties": {
                    "sport": {"type": "string"},
                    "result": {"type": "string"},
                    "phase": {"type": "string"},
                    "grade": {"type": "string"},
                    "odds_band": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_edges",
            "description": "Query edges.jsonl lessons",
            "parameters": {
                "type": "object",
                "properties": {
                    "last": {"type": "integer"},
                    "result": {"type": "string"},
                    "q": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learning",
            "description": "Learning mults and lessons from learning.json",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grade_evidence_file",
            "description": "Grade an evidence JSON pack",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "odds": {"type": "number"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dry_run_recommend",
            "description": "Run recommend without logging Pending rows",
            "parameters": {
                "type": "object",
                "properties": {"odds": {"type": "string"}},
                "required": ["odds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_evidence",
            "description": "List evidence/*.json filenames",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ev_calc",
            "description": "Compute haircut EV for p_model and odds",
            "parameters": {
                "type": "object",
                "properties": {
                    "odds": {"type": "number"},
                    "p_model": {"type": "number"},
                },
                "required": ["odds", "p_model"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "project_bankroll",
            "description": "Monte Carlo bankroll projection summary",
            "parameters": {
                "type": "object",
                "properties": {
                    "years": {"type": "number"},
                    "sims": {"type": "integer"},
                    "roi": {"type": "number"},
                    "bets_per_week": {"type": "number"},
                },
            },
        },
    },
]


def run_tool(cfg: dict[str, Any], name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"error": f"unknown tool: {name}"}
    try:
        result = fn(cfg, args or {})
    except Exception as e:
        result = {"error": str(e)}
    audit(cfg, {"role": "tool", "name": name, "args": args or {}, "result_digest": _digest(result)})
    return result


def _digest(obj: Any, n: int = 400) -> str:
    try:
        s = json.dumps(obj, default=str)
    except TypeError:
        s = str(obj)
    return s[:n]


def status_brief(cfg: dict[str, Any]) -> str:
    s = tool_get_status(cfg)
    return (
        f"Equity {s['equity_nok']:.2f} NOK | Phase {s['phase_id']} ({s.get('label')}) | "
        f"Cap {s['daily_risk_cap_nok']:.2f} remaining {s['remaining_risk_nok']:.2f} | "
        f"Can bet: {s['can_bet']}"
    )


def list_tools() -> list[str]:
    return sorted(TOOL_REGISTRY.keys())


def offline_answer(cfg: dict[str, Any], question: str, context_path: str | None = None) -> str:
    """
    No-API fallback: run a fixed toolbox and produce a structured brief.
    """
    parts = [
        "# Agent offline brief (no LLM)",
        "",
        f"Question: {question}",
        "",
        "## Status",
        status_brief(cfg),
        "",
    ]
    summary = tool_ledger_summary(cfg)
    o = summary.get("overall") or {}
    parts.append(
        f"## Ledger\n- Settled: {int(o.get('n_settled', 0))} | ROI {float(o.get('roi') or 0)*100:.1f}% | "
        f"P/L {float(o.get('pl') or 0):+.1f} | Max DD {summary.get('max_drawdown')}"
    )
    parts.append(f"- Streaks: {summary.get('streaks')}")
    learn = tool_get_learning(cfg)
    if learn.get("lessons"):
        parts.append("\n## Learning lessons")
        for L in (learn.get("lessons") or [])[:8]:
            parts.append(f"- {L}")
    if context_path:
        crit = tool_grade_evidence(cfg, {"path": context_path, "odds": 1.90})
        parts.append(f"\n## Evidence context\n```json\n{json.dumps(crit, indent=2)[:2000]}\n```")
    parts.extend(
        [
            "",
            "## Rules reminder",
            "- Empty slip is success.",
            "- Agent does not place bets or write the ledger.",
            "- Use `nt recommend --dry-run` before placing.",
            "",
        ]
    )
    text = "\n".join(parts)
    audit(cfg, {"role": "user", "content": question, "mode": "offline"})
    audit(cfg, {"role": "assistant", "content": text[:2000], "mode": "offline"})
    return text


def _resolve_provider(cfg: dict[str, Any]) -> tuple[str | None, str, str]:
    """Return (provider, base_url, api_key) or (None, '', '')."""
    ac = agent_cfg(cfg)
    provider = (os.environ.get("NT_AGENT_PROVIDER") or ac.get("provider") or "auto").lower()
    xai_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or ""
    oai_key = os.environ.get("OPENAI_API_KEY") or ""

    if provider == "none":
        return None, "", ""
    if provider == "xai" or (provider == "auto" and xai_key):
        return "xai", str(ac.get("base_url_xai") or "https://api.x.ai/v1"), xai_key
    if provider == "openai" or (provider == "auto" and oai_key):
        return "openai", str(ac.get("base_url_openai") or "https://api.openai.com/v1"), oai_key
    if provider == "auto":
        return None, "", ""
    return None, "", ""


def _default_model(provider: str, cfg: dict[str, Any]) -> str:
    ac = agent_cfg(cfg)
    if os.environ.get("NT_AGENT_MODEL"):
        return os.environ["NT_AGENT_MODEL"]
    if ac.get("model"):
        return str(ac["model"])
    if provider == "xai":
        return "grok-3"
    return "gpt-4o-mini"


SYSTEM_PROMPT = """You are the NT Betting Tracker assist agent for Norsk Tipping Oddsen.
Rules you must obey:
1. Code is law — phase, risk, evidence grades, and portfolio engines decide stakes.
2. Empty slip is success when nothing clears the bar.
3. You NEVER place bets or instruct silent ledger writes. Recommend human uses CLI.
4. Prefer tools for facts about this book over inventing statistics.
5. High odds need grade A evidence; do not invent p_model to force EV.
6. Be concise, disciplined, and risk-aware. Speak in clear English (Norwegian terms OK for markets).
7. Multi-sport + multi-market is mandatory: do not research only football HUB/BTTS/O-U.
   Treat player props, 1H/period markets, handicaps, tennis, NBA, esports as equal candidates when data supports edge.
8. Thin sports need sample — prefer researching shortlisted non-football lines so learning can update.
"""


def ask_llm(cfg: dict[str, Any], question: str, context_path: str | None = None) -> str:
    ac = agent_cfg(cfg)
    if not ac.get("enabled"):
        return offline_answer(
            cfg,
            question + "\n\n(Note: agent.enabled=false — offline brief only. Set agent.enabled true + API key for LLM.)",
            context_path=context_path,
        )

    provider, base_url, api_key = _resolve_provider(cfg)
    if not provider or not api_key:
        return offline_answer(
            cfg,
            question + "\n\n(Note: no API key — offline brief. Set XAI_API_KEY or OPENAI_API_KEY.)",
            context_path=context_path,
        )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    if context_path:
        messages.append({"role": "user", "content": f"Context file path: {context_path}"})

    audit(cfg, {"role": "user", "content": question, "mode": "llm", "provider": provider})
    model = _default_model(provider, cfg)
    max_rounds = int(ac.get("max_tool_rounds") or 6)

    for _ in range(max_rounds):
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOL_SCHEMAS,
            "temperature": float(ac.get("temperature") or 0.2),
        }
        data = _chat_completions(base_url, api_key, payload)
        if "error" in data:
            return offline_answer(cfg, question + f"\n\n(LLM error: {data['error']})", context_path=context_path)

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls = msg.get("tool_calls") or []
        if tool_calls:
            messages.append(msg)
            for tc in tool_calls:
                fn = (tc.get("function") or {})
                name = fn.get("name") or ""
                raw_args = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    args = {}
                result = run_tool(cfg, name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id") or name,
                        "content": json.dumps(result, default=str)[:8000],
                    }
                )
            continue

        content = msg.get("content") or "(empty response)"
        audit(cfg, {"role": "assistant", "content": content[:3000], "mode": "llm", "provider": provider})
        return content

    return offline_answer(cfg, question + "\n\n(Max tool rounds reached.)", context_path=context_path)


def _chat_completions(base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        return {"error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"error": str(e)}


def ask(cfg: dict[str, Any], question: str, context_path: str | None = None) -> str:
    """Public entry: LLM if enabled+keyed, else offline brief."""
    ac = agent_cfg(cfg)
    provider, _, key = _resolve_provider(cfg)
    if ac.get("enabled") and provider and key:
        return ask_llm(cfg, question, context_path=context_path)
    return offline_answer(cfg, question, context_path=context_path)
