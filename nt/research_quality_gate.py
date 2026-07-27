"""
Research Quality Challenger — hard_veto pack mutation (KD-quality-veto / KD-place-law).

v1 mechanism (engine-aligned):
  Challenger writes outbox/quality_veto_YYYY-MM-DD.json
  → CLI apply-quality-veto nulls p_model on resolved packs
  → recommend attach_evidence sees no p_model → seat not placeable

Notes-only research_quality flags are insufficient; portfolio does not honor them.
"""
from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nt.config import path_from_config
from nt.evidence import evidence_path, load_evidence
from nt.odds_common import evidence_pair_key, normalize_match_key, normalize_selection_key
from nt.paths import ROOT

log = logging.getLogger(__name__)

# Closed-enum hard_veto reasons (design §4.5). Unknown strings → reject row.
HARD_VETO_REASONS: frozenset[str] = frozenset(
    {
        "mic_missing",
        "mic_grade_D",
        "mic_grade_F",
        "opposite_side_thin",
        "form_continuity_weak_flip",
        "evidence_quality_insufficient",
    }
)

# MIC-scoped reasons (sport ∈ v1_sports after PR6); still accepted in enum here.
MIC_SCOPED_REASONS: frozenset[str] = frozenset(
    {"mic_missing", "mic_grade_D", "mic_grade_F"}
)


def evidence_pair_key_str(match: str | None, selection: str | None) -> str:
    """JSON/log form of evidence_pair_key: ``{norm_match}||{norm_selection}``."""
    m, s = evidence_pair_key(match, selection)
    return f"{m}||{s}"


def build_evidence_path_indexes(
    evidence_dir: Path,
) -> tuple[dict[tuple[str, str], Path], dict[tuple[str, str], Path]]:
    """
    Index top-level evidence/*.json exactly like attach_evidence.

    Returns (path_by_key exact, path_by_soft). First pack wins on soft collision.
    """
    path_by_key: dict[tuple[str, str], Path] = {}
    path_by_soft: dict[tuple[str, str], Path] = {}
    if not evidence_dir.exists():
        return path_by_key, path_by_soft
    for p in evidence_dir.glob("*.json"):
        if p.parent != evidence_dir:
            continue
        try:
            data = load_evidence(p)
        except Exception:
            continue
        if not data:
            continue
        m = str(data.get("match") or "").strip()
        s = str(data.get("selection") or "").strip()
        if not m or not s:
            continue
        path_by_key[(m, s)] = p
        soft = evidence_pair_key(m, s)
        path_by_soft.setdefault(soft, p)
    return path_by_key, path_by_soft


def resolve_evidence_pack_path(
    match: str | None,
    selection: str | None,
    evidence_dir: Path,
    *,
    evidence_key: str | None = None,
    path_by_key: dict[tuple[str, str], Path] | None = None,
    path_by_soft: dict[tuple[str, str], Path] | None = None,
) -> Path | None:
    """
    Resolve pack path with the same order as ``attach_evidence`` (design §4.5.1):

    1. exact (raw match, raw selection)
    2. soft evidence_pair_key
    3. evidence_path(evidence_dir, evidence_key or f"{match}_{selection}")
    4. evidence_dir / f"{match with spaces→underscores}.json"
    5. none → unresolved
    """
    if path_by_key is None or path_by_soft is None:
        path_by_key, path_by_soft = build_evidence_path_indexes(evidence_dir)

    m = (match or "").strip()
    s = (selection or "").strip()
    exact = (m, s)
    used = path_by_key.get(exact)
    if used is not None and used.is_file():
        return used

    soft = evidence_pair_key(m, s)
    used = path_by_soft.get(soft)
    if used is not None and used.is_file():
        return used

    key = evidence_key or f"{m}_{s}"
    path = evidence_path(evidence_dir, key)
    if path.is_file():
        return path

    alt = evidence_dir / f"{m.replace(' ', '_')}.json"
    if alt.is_file():
        return alt
    return None


def _rel_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        try:
            return path.as_posix()
        except Exception:
            return str(path)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def quality_veto_paths(cfg: dict[str, Any], day: str) -> dict[str, Path]:
    outbox = path_from_config(cfg, "outbox")
    return {
        "veto": outbox / f"quality_veto_{day}.json",
        "undo": outbox / f"quality_veto_undo_{day}.jsonl",
        "applied": outbox / f"quality_veto_applied_{day}.json",
    }


def load_veto_doc(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "date": None,
            "vetoes": [],
            "demotes": [],
            "_missing": True,
            "_path": str(path),
        }
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"veto doc must be object: {path}")
    data.setdefault("vetoes", [])
    data.setdefault("demotes", [])
    data["_path"] = str(path)
    data["_missing"] = False
    return data


def validate_hard_veto_reasons(reasons: Any) -> tuple[list[str], list[str]]:
    """
    Split reasons into (valid closed-enum, unknown).

    Row is rejected if any unknown reason is present or no valid reasons remain.
    """
    if not reasons:
        return [], []
    if isinstance(reasons, str):
        reasons = [reasons]
    valid: list[str] = []
    unknown: list[str] = []
    for r in reasons:
        s = str(r or "").strip()
        if not s:
            continue
        if s in HARD_VETO_REASONS:
            if s not in valid:
                valid.append(s)
        else:
            if s not in unknown:
                unknown.append(s)
    return valid, unknown


def is_already_hard_vetoed(pack: dict[str, Any] | None) -> bool:
    if not pack:
        return False
    rq = pack.get("research_quality")
    if not isinstance(rq, dict):
        return False
    return str(rq.get("action") or "").strip().lower() == "hard_veto"


def mutate_pack_hard_veto(
    pack: dict[str, Any],
    *,
    reasons: list[str],
    veto_date: str,
    resolved_path: str,
) -> dict[str, Any]:
    """
    Null p_model and set research_quality block (preferred v1; not quarantine).
    Mutates a shallow copy and returns it.
    """
    out = dict(pack)
    prior = out.get("p_model")
    try:
        prior_f = float(prior) if prior is not None else None
    except (TypeError, ValueError):
        prior_f = None
    out["p_model"] = None
    out["research_quality"] = {
        "action": "hard_veto",
        "reasons": list(reasons),
        "veto_date": veto_date,
        "prior_p_model": prior_f,
        "applied_by": "apply-quality-veto",
        "resolved_path": resolved_path,
    }
    return out


def write_pack_atomic(path: Path, pack: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(pack, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# data_coverage / evidence_quality helpers (pack schema §3.3)
# ---------------------------------------------------------------------------


def build_data_coverage(
    *,
    mic_grade: str | None = None,
    both_sides: bool | None = None,
    form: bool | None = None,
    h2h: bool | None = None,
    rank_or_table: bool | None = None,
    injuries_checked: bool | None = None,
    evidence_quality: str = "unknown",
    evidence_quality_notes: str = "",
    mic_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build optional ``data_coverage`` block for deep evidence packs.

    ``evidence_quality`` free-text labels (e.g. adequate / thin / insufficient);
    hard place removal still goes through closed-enum hard_veto, not this field alone.
    """
    grade = mic_grade
    if grade is None and isinstance(mic_coverage, dict):
        grade = mic_coverage.get("grade")
    return {
        "mic_grade": grade,
        "both_sides": both_sides,
        "form": form,
        "h2h": h2h,
        "rank_or_table": rank_or_table,
        "injuries_checked": injuries_checked,
        "evidence_quality": evidence_quality,
        "evidence_quality_notes": evidence_quality_notes or "",
    }


def attach_data_coverage(pack: dict[str, Any], coverage: dict[str, Any] | None) -> dict[str, Any]:
    """Return pack with data_coverage merged (no-op if coverage is None)."""
    if not coverage:
        return pack
    out = dict(pack)
    out["data_coverage"] = dict(coverage)
    return out


# ---------------------------------------------------------------------------
# apply_quality_veto
# ---------------------------------------------------------------------------


def apply_quality_veto(
    cfg: dict[str, Any],
    date: str,
    veto_doc: dict[str, Any] | None = None,
    *,
    dry_run: bool = False,
    veto_file: str | Path | None = None,
) -> dict[str, Any]:
    """
    Apply hard_veto pack mutations for a calendar day.

    - Prefer null ``p_model`` (not quarantine).
    - Idempotent when ``research_quality.action == hard_veto``.
    - Unknown reason strings → warn + skip row.
    - Always writes ``quality_veto_applied_*.json`` when not dry_run (incl. zero vetoes).
    - soft_demote entries are counted only (no pack mutation).
    """
    paths = quality_veto_paths(cfg, date)
    if veto_doc is None:
        src = Path(veto_file) if veto_file else paths["veto"]
        veto_doc = load_veto_doc(src)
    else:
        src = Path(veto_file) if veto_file else paths["veto"]
        veto_doc = dict(veto_doc)
        veto_doc.setdefault("vetoes", [])
        veto_doc.setdefault("demotes", [])
        veto_doc["_path"] = str(src)
        veto_doc.setdefault("_missing", False)

    source_rel = _rel_posix(Path(veto_doc.get("_path") or paths["veto"]))
    evidence_dir = path_from_config(cfg, "evidence")
    path_by_key, path_by_soft = build_evidence_path_indexes(evidence_dir)

    vetoes = list(veto_doc.get("vetoes") or [])
    demotes = list(veto_doc.get("demotes") or [])

    results: list[dict[str, Any]] = []
    undo_lines: list[dict[str, Any]] = []
    n_applied = 0
    n_unresolved = 0
    n_idempotent_skip = 0
    n_rejected = 0
    n_hard = 0

    for raw in vetoes:
        if not isinstance(raw, dict):
            n_rejected += 1
            results.append({"status": "rejected", "error": "not_an_object", "row": raw})
            continue

        action = str(raw.get("action") or "hard_veto").strip().lower()
        if action and action not in ("hard_veto", "hard-veto"):
            # Only hard_veto mutates; soft entries in vetoes[] are skipped
            n_rejected += 1
            results.append(
                {
                    "status": "rejected",
                    "error": f"unsupported_action:{action}",
                    "match": raw.get("match"),
                    "selection": raw.get("selection"),
                }
            )
            continue

        match = str(raw.get("match") or "").strip()
        selection = str(raw.get("selection") or "").strip()
        reasons_raw = raw.get("reasons")
        valid, unknown = validate_hard_veto_reasons(reasons_raw)
        if unknown or not valid:
            msg = (
                f"reject hard_veto row match={match!r} selection={selection!r}: "
                f"unknown_reasons={unknown} valid={valid}"
            )
            warnings.warn(msg, stacklevel=2)
            log.warning(msg)
            n_rejected += 1
            results.append(
                {
                    "status": "rejected",
                    "error": "unknown_or_empty_reasons",
                    "unknown_reasons": unknown,
                    "valid_reasons": valid,
                    "match": match,
                    "selection": selection,
                }
            )
            continue

        n_hard += 1
        pair_str = raw.get("evidence_pair_key_str") or evidence_pair_key_str(match, selection)
        resolved = resolve_evidence_pack_path(
            match,
            selection,
            evidence_dir,
            evidence_key=raw.get("evidence_key"),
            path_by_key=path_by_key,
            path_by_soft=path_by_soft,
        )
        if resolved is None:
            n_unresolved += 1
            results.append(
                {
                    "status": "unresolved",
                    "match": match,
                    "selection": selection,
                    "evidence_pair_key_str": pair_str,
                    "reasons": valid,
                }
            )
            continue

        rel = _rel_posix(resolved)
        pack = load_evidence(resolved) or {}
        if is_already_hard_vetoed(pack):
            n_idempotent_skip += 1
            results.append(
                {
                    "status": "idempotent_skip",
                    "match": match,
                    "selection": selection,
                    "resolved_path": rel,
                    "reasons": valid,
                }
            )
            continue

        prior_p = pack.get("p_model")
        try:
            prior_f = float(prior_p) if prior_p is not None else None
        except (TypeError, ValueError):
            prior_f = None

        mutated = mutate_pack_hard_veto(
            pack,
            reasons=valid,
            veto_date=date,
            resolved_path=rel,
        )
        undo_line = {
            "ts": _utc_now_iso(),
            "date": date,
            "match": match,
            "selection": selection,
            "evidence_pair_key_str": pair_str,
            "resolved_path": rel,
            "prior_p_model": prior_f,
            "reasons": valid,
            "dry_run": bool(dry_run),
            "action": "hard_veto",
        }

        if not dry_run:
            write_pack_atomic(resolved, mutated)
            undo_lines.append(undo_line)

        n_applied += 1
        results.append(
            {
                "status": "applied" if not dry_run else "would_apply",
                "match": match,
                "selection": selection,
                "evidence_pair_key_str": pair_str,
                "resolved_path": rel,
                "prior_p_model": prior_f,
                "reasons": valid,
            }
        )

    # soft demotes: count only
    n_demotes = sum(1 for d in demotes if isinstance(d, dict))

    applied_marker = {
        "schema_version": 1,
        "date": date,
        "applied_at": _utc_now_iso(),
        "n_vetoes": n_hard,
        "n_demotes": n_demotes,
        "n_applied": n_applied if not dry_run else 0,
        "n_would_apply": n_applied if dry_run else n_applied,
        "n_unresolved": n_unresolved,
        "n_idempotent_skip": n_idempotent_skip,
        "n_rejected": n_rejected,
        "source_veto_file": source_rel,
        "dry_run": bool(dry_run),
    }

    if not dry_run:
        outbox = path_from_config(cfg, "outbox")
        outbox.mkdir(parents=True, exist_ok=True)
        # undo jsonl (may be empty file when zero applied mutations)
        with open(paths["undo"], "a", encoding="utf-8") as f:
            for line in undo_lines:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        paths["applied"].write_text(
            json.dumps(applied_marker, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return {
        "ok": True,
        "date": date,
        "dry_run": bool(dry_run),
        "source_veto_file": source_rel,
        "applied_path": str(paths["applied"]) if not dry_run else None,
        "undo_path": str(paths["undo"]) if not dry_run else None,
        "marker": applied_marker,
        "results": results,
        "n_vetoes": n_hard,
        "n_demotes": n_demotes,
        "n_applied": n_applied if not dry_run else 0,
        "n_would_apply": n_applied if dry_run else None,
        "n_unresolved": n_unresolved,
        "n_idempotent_skip": n_idempotent_skip,
        "n_rejected": n_rejected,
    }


# ---------------------------------------------------------------------------
# assert-can-bet (SSOT: risk.json / evaluate_risk)
# ---------------------------------------------------------------------------


def load_risk_json(cfg: dict[str, Any]) -> dict[str, Any] | None:
    state_dir = path_from_config(cfg, "state_dir")
    path = state_dir / "risk.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def assert_can_bet_snapshot(
    cfg: dict[str, Any],
    *,
    refresh: bool = True,
    risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return a slim risk gate snapshot for can-bet checks.

    When ``refresh`` is True (default), recompute via the same ``refresh_state``
    path as ``status``. When False, read ``data/state/risk.json`` (or use
    provided ``risk``).
    """
    if risk is not None:
        src = "provided"
        r = risk
    elif refresh:
        from nt.recommend import refresh_state

        _bankroll, _phase, r = refresh_state(cfg)
        src = "refresh_state"
    else:
        r = load_risk_json(cfg) or {}
        src = "risk.json"

    slim = {
        "can_bet": bool(r.get("can_bet")),
        "remaining_risk_nok": r.get("remaining_risk_nok"),
        "stopped": r.get("stopped"),
        "research_only": r.get("research_only"),
        "reasons": list(r.get("reasons") or []),
        "date": r.get("date"),
        "source": src,
    }
    # capital_v2 extras when present
    for k in ("size_mode", "freeze_manual", "freeze_dd", "phase_id"):
        if k in r:
            slim[k] = r[k]
    return slim


def assert_can_bet_exit_code(snapshot: dict[str, Any]) -> int:
    """Exit 0 if can_bet true, else 1."""
    return 0 if snapshot.get("can_bet") else 1
