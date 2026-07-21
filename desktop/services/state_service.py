from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
import nt_bootstrap  # noqa: F401

from datetime import datetime

from nt.analytics import (
    DATE_RANGE_PRESETS,
    date_range_bounds,
    deep_dive,
    filter_rows,
    fnum,
    group_stats_with_ids,
    with_derived,
)
from nt.bets_io import load_bets, validate_bets
from nt.calibrate import load_calibration
from nt.config import load_config, path_from_config
from nt.decisions import (
    backfill_decisions_from_notes,
    load_decisions,
    load_evidence_links,
)
from nt.learning import load_learning, load_learning_history, run_learning
from nt.recommend import refresh_state, run_recommend
from nt.settle import run_settle


def is_valid_project_root(path: Path) -> bool:
    return (path / "config.yaml").is_file() and (path / "data" / "bets.csv").is_file()


def default_project_root() -> Path:
    env = os.environ.get("NT_PROJECT_ROOT")
    if env and is_valid_project_root(Path(env)):
        return Path(env).resolve()
    if is_valid_project_root(_REPO):
        return _REPO
    cwd = Path.cwd()
    if is_valid_project_root(cwd):
        return cwd.resolve()
    return _REPO


@dataclass
class AppState:
    root: Path
    cfg: dict[str, Any] = field(default_factory=dict)
    bankroll: dict[str, Any] = field(default_factory=dict)
    phase: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    rows: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dive: dict[str, Any] = field(default_factory=dict)
    learning: dict[str, Any] = field(default_factory=dict)
    learning_history: list = field(default_factory=list)
    decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence_links: dict[str, dict[str, Any]] = field(default_factory=dict)
    calibration: list[dict[str, Any]] = field(default_factory=list)
    range_key: str = "all"
    range_label: str = "All time"
    range_from: str | None = None
    range_to: str | None = None
    last_error: str | None = None
    updated_at: str = ""
    # Forensic drill state (chart/table → tickets); not persisted
    forensic_bet_ids: list[str] | None = None
    forensic_label: str = ""

    @property
    def equity_curve(self) -> list:
        return self.dive.get("equity_curve") or []

    @property
    def daily(self) -> list:
        return self.dive.get("daily") or []

    @property
    def bands(self) -> dict:
        return self.dive.get("bands") or {}

    @property
    def by_sport(self) -> dict:
        return self.dive.get("by_sport") or {}

    @property
    def by_phase(self) -> dict:
        return self.dive.get("by_phase") or {}

    @property
    def by_grade(self) -> dict:
        return self.dive.get("by_grade") or {}

    @property
    def overall(self) -> dict:
        return self.dive.get("overall") or {}

    @property
    def streak(self) -> dict:
        return (self.dive.get("streaks") or {}).get("current") or {}

    @property
    def max_dd(self) -> float:
        return float(self.dive.get("max_drawdown") or 0)

    @property
    def recent(self) -> list:
        return self.dive.get("recent") or []

    def pending_rows(self) -> list[dict[str, str]]:
        return [r for r in self.rows if r.get("result") == "Pending"]


class StateService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_project_root()).resolve()
        self.state = AppState(root=self.root)
        self.range_key = "all"

    def set_root(self, root: Path) -> None:
        root = root.resolve()
        if not is_valid_project_root(root):
            raise ValueError(f"Not a valid NT project root: {root}")
        self.root = root
        self.state.root = root

    def _activate_root(self) -> None:
        import nt.paths as paths

        paths.ROOT = self.root
        os.chdir(self.root)
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))

    def set_range(self, key: str) -> AppState:
        """Change analytics window and recompute dive only (fast)."""
        self.range_key = key
        return self._recompute_dive()

    def _recompute_dive(self) -> AppState:
        st = self.state
        if not st.cfg or not st.rows:
            return st
        era = (st.cfg.get("bankroll") or {}).get("era_start")
        d_from, d_to, label = date_range_bounds(self.range_key, era_start=era)
        dive = deep_dive(
            st.rows,
            float(st.bankroll.get("baseline_nok") or st.cfg["bankroll"]["baseline_nok"]),
            cfg=st.cfg,
            phase=st.phase,
            date_from=d_from if self.range_key != "all" else None,
            date_to=d_to if self.range_key != "all" else None,
            range_key=self.range_key,
            range_label=label,
        )
        # For "all", deep_dive already sets dates from data; still store label
        if self.range_key == "all":
            dive["range_key"] = "all"
            dive["range_label"] = "All time"
        st.dive = dive
        st.range_key = self.range_key
        st.range_label = label
        st.range_from = dive.get("date_from")
        st.range_to = dive.get("date_to")
        return st

    def reload(self, write_state: bool = True) -> AppState:
        self._activate_root()
        try:
            cfg = load_config(self.root / "config.yaml")
            if write_state:
                bankroll, phase, risk = refresh_state(cfg)
            else:
                from nt.bankroll import compute_bankroll
                from nt.phase import evaluate_phase, load_phase_state
                from nt.risk import evaluate_risk

                bankroll = compute_bankroll(cfg)
                prev = load_phase_state(cfg)
                current_id = prev["phase_id"] if prev else None
                bets_path = path_from_config(cfg, "bets")
                rows_tmp = load_bets(bets_path)
                phase = evaluate_phase(
                    cfg,
                    bankroll["equity_nok"],
                    bankroll["settled_count"],
                    rows=rows_tmp,
                    current_phase=current_id,
                )
                risk = evaluate_risk(cfg, bankroll["equity_nok"], phase, rows_tmp)

            bets_path = path_from_config(cfg, "bets")
            rows = load_bets(bets_path)
            errors = validate_bets(rows)

            # Single learning path: refresh_state already runs learning when write_state=True.
            # Soft reload recompute once so Lab stays fresh after CLI settle.
            learning: dict[str, Any] = {}
            learning_err: str | None = None
            try:
                if (cfg.get("learning") or {}).get("enabled", True):
                    if write_state:
                        learning = load_learning(cfg)
                        if not learning:
                            learning = run_learning(cfg, rows)
                    else:
                        learning = run_learning(cfg, rows)
                else:
                    learning = load_learning(cfg)
            except Exception as ex:  # noqa: BLE001
                learning_err = str(ex)
                learning = load_learning(cfg)

            # Ensure side-car exists for recommend rows (notes recovery); cheap no-op if filled
            try:
                backfill_decisions_from_notes(cfg, rows, only_missing=True)
            except Exception:
                pass

            decisions: dict[str, dict[str, Any]] = {}
            try:
                decisions = load_decisions(cfg)
            except Exception:
                decisions = {}

            evidence_links: dict[str, dict[str, Any]] = {}
            try:
                evidence_links = load_evidence_links(cfg)
            except Exception:
                evidence_links = {}

            calibration: list[dict[str, Any]] = []
            try:
                calibration = load_calibration(cfg)
            except Exception:
                calibration = []

            learning_history: list = []
            try:
                learning_history = load_learning_history(cfg, limit=80)
            except Exception:
                learning_history = []

            # Preserve forensic drill across soft reloads
            prev_ids = self.state.forensic_bet_ids
            prev_label = self.state.forensic_label

            self.state = AppState(
                root=self.root,
                cfg=cfg,
                bankroll=bankroll,
                phase=phase,
                risk=risk,
                rows=rows,
                errors=errors,
                learning=learning or {},
                learning_history=learning_history or [],
                decisions=decisions or {},
                evidence_links=evidence_links or {},
                calibration=calibration or [],
                last_error=learning_err,
                updated_at=bankroll.get("updated_at") or "",
                range_key=self.range_key,
                forensic_bet_ids=prev_ids,
                forensic_label=prev_label,
            )
            self._recompute_dive()
        except Exception as e:  # noqa: BLE001
            self.state.last_error = str(e)
            raise
        return self.state

    def inbox_odds_files(self) -> list[Path]:
        return [
            f
            for f in self.inbox_files()
            if f.suffix.lower() in (".txt", ".csv") and "result" not in f.name.lower()
        ]

    def inbox_results_files(self) -> list[Path]:
        return [
            f
            for f in self.inbox_files()
            if f.suffix.lower() in (".yaml", ".yml", ".txt", ".json")
            and ("result" in f.name.lower() or f.suffix.lower() in (".yaml", ".yml"))
        ]

    def latest_rejects_text(self) -> str:
        out = self.root / "outbox"
        if not out.is_dir():
            return ""
        cands = sorted(out.glob("REJECTS*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            return ""
        try:
            return cands[0].read_text(encoding="utf-8")
        except OSError:
            return ""

    def latest_receipt_text(self) -> str:
        path = self.root / "outbox" / "SETTLEMENT_RECEIPT.md"
        if not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def run_recommend_odds(self, odds_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
        """Invoke engine recommend; reloads state after."""
        self._activate_root()
        cfg = load_config(self.root / "config.yaml")
        result = run_recommend(cfg, odds_path, log_pending=not dry_run)
        self.reload(write_state=True)
        return result

    def run_settle_results(self, results_path: Path) -> dict[str, Any]:
        """Invoke engine settle; reloads state after."""
        self._activate_root()
        cfg = load_config(self.root / "config.yaml")
        result = run_settle(cfg, results_path)
        self.reload(write_state=True)
        return result

    def filtered_rows(self, **kwargs: Any) -> list[dict[str, str]]:
        # Forensic bet_ids are exact grain — do not also clamp to range window
        if kwargs.get("bet_ids"):
            return filter_rows(self.state.rows, **kwargs)
        # Default bets explorer to active range unless caller overrides
        if "date_from" not in kwargs and self.state.range_from and self.range_key != "all":
            kwargs["date_from"] = self.state.range_from
        if "date_to" not in kwargs and self.state.range_to and self.range_key != "all":
            kwargs["date_to"] = self.state.range_to
        return filter_rows(self.state.rows, **kwargs)

    def set_forensic(self, bet_ids: list[str] | None, label: str = "") -> None:
        """Set chart→tickets forensic drill (grain law: exact bet_ids)."""
        self.state.forensic_bet_ids = list(bet_ids) if bet_ids else None
        self.state.forensic_label = label or ""

    def clear_forensic(self) -> None:
        self.state.forensic_bet_ids = None
        self.state.forensic_label = ""

    def period_settled_rows(self) -> list[dict[str, str]]:
        """Settled rows in the active analytics window (same scope as Book stats)."""
        return self.filtered_rows(result=["Win", "Loss", "Refunded", "Void", "Push"])

    def bet_ids_for_group(self, dim: str, value: str) -> list[str]:
        """
        Resolve forensic bet_ids for a breakdown bucket using group_stats_with_ids.
        dim: sport | odds_band | phase | research_grade | market | weekday |
             stake_bucket | source | grade
        """
        if not value or value in ("(empty)",) or str(value).startswith("Other"):
            return []
        period = self.period_settled_rows()
        dim = (dim or "").strip()
        if dim == "grade":
            dim = "research_grade"

        key_fn = None
        key = dim
        if dim == "market":
            derived = with_derived(period)
            g = group_stats_with_ids(derived, "market_inferred")
            st = g.get(value) or {}
            return list(st.get("bet_ids") or [])
        if dim == "source":
            # archive vs live uses source_group on derived rows
            derived = with_derived(period)
            g = group_stats_with_ids(derived, "source_group")
            st = g.get(value) or g.get(value.lower()) or {}
            if not st:
                # fallback raw source field
                g = group_stats_with_ids(period, "source")
                st = g.get(value) or {}
            return list(st.get("bet_ids") or [])
        if dim == "weekday":

            def _wd(r: dict[str, str]) -> str:
                d = r.get("date") or ""
                try:
                    return datetime.strptime(d, "%Y-%m-%d").strftime("%a")
                except ValueError:
                    return "?"

            key_fn = _wd
            key = "weekday"
        elif dim == "stake_bucket":

            def _sb(r: dict[str, str]) -> str:
                s = fnum(r.get("stake_nok")) or 0.0
                if s < 12:
                    return "10–11"
                if s < 15:
                    return "12–14"
                if s < 20:
                    return "15–19"
                return "20+"

            key_fn = _sb
            key = "stake_bucket"
        elif dim not in (
            "sport",
            "odds_band",
            "phase",
            "research_grade",
            "result",
        ):
            # unknown dim — try as raw field
            key = dim

        g = group_stats_with_ids(period, key, key_fn=key_fn)
        st = g.get(value) or {}
        return list(st.get("bet_ids") or [])

    def drill_forensic(self, dim: str, value: str, label: str | None = None) -> list[str]:
        """Compute bet_ids for group, store forensic state, return ids."""
        ids = self.bet_ids_for_group(dim, value)
        pretty = label or f"{dim}: {value}"
        self.set_forensic(ids if ids else None, pretty if ids else "")
        return ids

    def inbox_files(self) -> list[Path]:
        p = self.root / "inbox"
        if not p.is_dir():
            return []
        return sorted([f for f in p.iterdir() if f.is_file()], key=lambda x: x.name)

    def outbox_files(self) -> list[Path]:
        p = self.root / "outbox"
        if not p.is_dir():
            return []
        return sorted(
            [f for f in p.iterdir() if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

    def place_slip_text(self) -> str:
        path = self.root / "outbox" / "PLACE_THESE.md"
        if not path.exists():
            return "_No place slip yet (outbox/PLACE_THESE.md)._"
        return path.read_text(encoding="utf-8")


__all__ = [
    "StateService",
    "AppState",
    "default_project_root",
    "is_valid_project_root",
    "DATE_RANGE_PRESETS",
]
