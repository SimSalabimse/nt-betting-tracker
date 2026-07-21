"""
P2: Indexed past failures (losses, process_errors, evidence failure_modes).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from nt.bets_io import load_bets, utc_now
from nt.config import path_from_config
from nt.edges import load_edges
from nt.evidence import load_evidence


def failure_index_path(cfg: dict[str, Any]) -> Path:
    paths = cfg.get("paths") or {}
    if paths.get("failure_index_json"):
        return path_from_config(cfg, "failure_index_json")
    return path_from_config(cfg, "state_dir") / "failure_index.json"


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) >= 3]


def _doc(
    *,
    id: str,
    kind: str,
    text: str,
    match: str = "",
    selection: str = "",
    sport: str = "",
    bet_id: str = "",
    ts: str = "",
) -> dict[str, Any]:
    return {
        "id": id,
        "kind": kind,
        "match": match,
        "selection": selection,
        "sport": sport,
        "bet_id": bet_id,
        "ts": ts,
        "text": text[:2000],
    }


def rebuild_failure_index(cfg: dict[str, Any]) -> dict[str, Any]:
    docs: list[dict[str, Any]] = []

    # 1) Loss bets
    try:
        rows = load_bets(path_from_config(cfg, "bets"))
    except Exception:
        rows = []
    for r in rows:
        if str(r.get("result") or "") != "Loss":
            continue
        bid = str(r.get("bet_id") or "")
        text = " ".join(
            str(r.get(k) or "")
            for k in ("match", "selection", "sport", "notes", "research_grade", "market_type")
        )
        docs.append(
            _doc(
                id=f"bet:{bid}",
                kind="bet",
                text=text + " loss",
                match=str(r.get("match") or ""),
                selection=str(r.get("selection") or ""),
                sport=str(r.get("sport") or ""),
                bet_id=bid,
                ts=str(r.get("updated_at") or r.get("date") or ""),
            )
        )

    # 2) Edges
    try:
        for i, e in enumerate(load_edges(cfg)):
            res = str(e.get("result") or "")
            note = str(e.get("note") or e.get("notes") or e.get("lesson") or "")
            if res != "Loss" and "process" not in note.lower() and "fail" not in note.lower():
                continue
            docs.append(
                _doc(
                    id=f"edge:{i}:{e.get('bet_id') or i}",
                    kind="edge",
                    text=" ".join(
                        str(e.get(k) or "")
                        for k in ("match", "selection", "sport", "note", "notes", "lesson", "result")
                    ),
                    match=str(e.get("match") or ""),
                    selection=str(e.get("selection") or ""),
                    sport=str(e.get("sport") or ""),
                    bet_id=str(e.get("bet_id") or ""),
                    ts=str(e.get("ts") or ""),
                )
            )
    except Exception:
        pass

    # 3) Evidence failure_modes
    try:
        ev_dir = path_from_config(cfg, "evidence")
        if ev_dir.is_dir():
            for p in sorted(ev_dir.glob("*.json"))[:800]:
                data = load_evidence(p)
                if not data:
                    continue
                fm = str(data.get("failure_modes") or "")
                if not fm.strip():
                    continue
                docs.append(
                    _doc(
                        id=f"ev:{p.name}",
                        kind="evidence",
                        text=f"{data.get('match')} {data.get('selection')} {fm} {data.get('summary') or ''}",
                        match=str(data.get("match") or ""),
                        selection=str(data.get("selection") or ""),
                        sport=str(data.get("sport") or ""),
                        ts="",
                    )
                )
    except Exception:
        pass

    # 4) Settlement reviews process_error
    try:
        paths = cfg.get("paths") or {}
        if paths.get("settlement_reviews_jsonl"):
            rp = path_from_config(cfg, "settlement_reviews_jsonl")
        else:
            rp = path_from_config(cfg, "state_dir") / "settlement_reviews.jsonl"
        if rp.is_file():
            for i, line in enumerate(rp.read_text(encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(r.get("variance_class") or "") != "process_error":
                    continue
                docs.append(
                    _doc(
                        id=f"review:{i}:{r.get('bet_id')}",
                        kind="review",
                        text=" ".join(
                            str(r.get(k) or "")
                            for k in (
                                "match",
                                "selection",
                                "variance_detail",
                                "notes",
                                "sport",
                            )
                        )
                        + " process_error",
                        match=str(r.get("match") or ""),
                        selection=str(r.get("selection") or ""),
                        sport=str((r.get("factors") or {}).get("sport") or ""),
                        bet_id=str(r.get("bet_id") or ""),
                        ts=str(r.get("ts") or ""),
                    )
                )
    except Exception:
        pass

    tokens: dict[str, list[str]] = defaultdict(list)
    for d in docs:
        seen: set[str] = set()
        for t in _tokens(d["text"]):
            if t in seen:
                continue
            seen.add(t)
            tokens[t].append(d["id"])

    payload = {
        "updated_at": utc_now(),
        "n_docs": len(docs),
        "docs": docs,
        "tokens": dict(tokens),
    }
    path = failure_index_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "n_docs": len(docs), "n_tokens": len(tokens)}


def load_failure_index(cfg: dict[str, Any]) -> dict[str, Any]:
    path = failure_index_path(cfg)
    if not path.is_file():
        return {"docs": [], "tokens": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"docs": [], "tokens": {}}


def query_failures(
    cfg: dict[str, Any],
    *,
    q: str = "",
    sport: str | None = None,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    idx = load_failure_index(cfg)
    docs = {d["id"]: d for d in (idx.get("docs") or []) if isinstance(d, dict)}
    if not docs:
        return []

    q_tokens = _tokens(q) if q else []
    if q_tokens:
        token_map = idx.get("tokens") or {}
        id_sets = []
        for t in q_tokens:
            id_sets.append(set(token_map.get(t) or []))
        if not id_sets:
            cand_ids: set[str] = set()
        else:
            cand_ids = set.intersection(*id_sets) if id_sets else set()
        candidates = [docs[i] for i in cand_ids if i in docs]
    else:
        # recent losses: take last docs
        candidates = list(docs.values())

    out: list[dict[str, Any]] = []
    for d in candidates:
        if sport and str(d.get("sport") or "").lower() != sport.lower():
            continue
        if kind and str(d.get("kind") or "") != kind:
            continue
        out.append(d)
    # Prefer newer ts last
    out.sort(key=lambda d: str(d.get("ts") or ""), reverse=True)
    return out[: max(1, int(limit))]
