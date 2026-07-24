"""Sport Research Cards — YAML SSOT under evidence/sport_cards/."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nt.evidence_hierarchy.normalize import normalize_sport_for_research
from nt.evidence_hierarchy.types import RequiredGroup, SignalSlot
from nt.paths import ROOT

# Prefer PyYAML if present; else minimal JSON fallback + hand-parsed YAML subset
try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def sport_cards_dir(cfg: dict[str, Any] | None = None) -> Path:
    if cfg:
        sel = (cfg.get("selection") or {}).get("evidence") or {}
        rel = sel.get("sport_cards_dir") or "evidence/sport_cards"
        p = Path(str(rel))
        if p.is_absolute():
            return p
        try:
            from nt.config import path_from_config

            base = path_from_config(cfg, "sport_cards")
            if base:
                return Path(base)
        except Exception:
            pass
        return (ROOT / rel).resolve()
    return (ROOT / "evidence" / "sport_cards").resolve()


def sport_card_path(sport: str, cfg: dict[str, Any] | None = None) -> Path:
    key = normalize_sport_for_research(sport)
    return sport_cards_dir(cfg) / f"{key}.yaml"


@dataclass
class SportCard:
    sport: str
    display_name: str
    onboarded: bool
    individual_sport: bool
    primary: list[dict[str, Any]]
    secondary: list[dict[str, Any]]
    tertiary: list[dict[str, Any]]
    grade_floors: dict[str, Any]
    hard_rejects: list[dict[str, Any]]
    edges: dict[str, Any]
    domain_allowlist: list[str] = field(default_factory=list)
    required_groups: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    version: int = 1
    schema_version: int = 1
    # alias_id → stable factor id (e.g. avg_checkout → checkout_scoring)
    signal_id_aliases: dict[str, str] = field(default_factory=dict)

    @property
    def card_id(self) -> str:
        return f"{self.sport}_v{self.version}"

    def all_factors(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for tier, items in (
            (1, self.primary),
            (2, self.secondary),
            (3, self.tertiary),
        ):
            for it in items:
                d = dict(it)
                d.setdefault("tier", tier)
                out.append(d)
        return out

    def stable_factor_ids(self) -> set[str]:
        return {str(f.get("id") or "") for f in self.all_factors() if f.get("id")}

    def resolve_signal_id(self, signal_id: str) -> str:
        """Map pack signal id (possibly legacy alias) → stable card factor id."""
        sid = str(signal_id or "").strip()
        if not sid:
            return sid
        aliases = self.signal_id_aliases or {}
        # alias → stable
        if sid in aliases:
            return str(aliases[sid])
        # already stable
        return sid

    def lookup_signal(
        self, signals: dict[str, Any] | None, slot_id: str
    ) -> dict[str, Any] | None:
        """Find signal payload for a stable slot id, honouring aliases."""
        if not isinstance(signals, dict):
            return None
        # direct stable id
        sig = signals.get(slot_id)
        if isinstance(sig, dict):
            return sig
        # reverse: pack uses alias that maps to this slot
        for alias, stable in (self.signal_id_aliases or {}).items():
            if stable == slot_id:
                alt = signals.get(alias)
                if isinstance(alt, dict):
                    return alt
        return None

    def map_pack_signals(self, signals: dict[str, Any] | None) -> dict[str, str]:
        """
        Map each filled pack signal id → card slot id (or '' if unrecognized).
        Used by tests / migration inventory.
        """
        out: dict[str, str] = {}
        if not isinstance(signals, dict):
            return out
        stable = self.stable_factor_ids()
        for sid in signals:
            resolved = self.resolve_signal_id(sid)
            out[str(sid)] = resolved if resolved in stable else ""
        return out

    def slots(self) -> list[SignalSlot]:
        slots: list[SignalSlot] = []
        for f in self.all_factors():
            markets = _as_frozen(f.get("markets") or ["*"])
            req = _as_frozen(f.get("require_when") or [])
            srcs = tuple(str(s) for s in (f.get("sources") or [])[:8])
            slots.append(
                SignalSlot(
                    id=str(f.get("id") or f.get("name") or "slot"),
                    tier=int(f.get("tier") or 2),
                    weight=float(f.get("weight") or 1.0),
                    markets=markets,
                    require_when=req,
                    public_sources=srcs,
                    min_takeaway_chars=int(f.get("min_takeaway_chars") or 24),
                    allows_negative_strength=bool(
                        f.get("allows_negative") or f.get("id") == "h2h_matchup"
                    ),
                    individual_h2h=bool(
                        f.get("individual_h2h")
                        or f.get("id") in ("h2h_matchup", "surface_h2h")
                    ),
                )
            )
        return slots

    def groups(self) -> list[RequiredGroup]:
        out: list[RequiredGroup] = []
        for g in self.required_groups:
            out.append(
                RequiredGroup(
                    id=str(g.get("id") or "group"),
                    slot_ids=tuple(str(x) for x in (g.get("slot_ids") or [])),
                    min_filled=int(g.get("min_filled") or 1),
                    apply_when=_as_frozen(g.get("apply_when") or ["*"]),
                )
            )
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sport": self.sport,
            "display_name": self.display_name,
            "version": self.version,
            "onboarded": self.onboarded,
            "individual_sport": self.individual_sport,
            "primary": self.primary,
            "secondary": self.secondary,
            "tertiary": self.tertiary,
            "grade_floors": self.grade_floors,
            "hard_rejects": self.hard_rejects,
            "edges": self.edges,
            "domain_allowlist": self.domain_allowlist,
            "required_groups": self.required_groups,
            "notes": self.notes,
            "signal_id_aliases": dict(self.signal_id_aliases or {}),
        }


def _as_frozen(val: Any) -> frozenset[str]:
    if val is None:
        return frozenset()
    if isinstance(val, str):
        if val.strip() in ("", "∅", "none", "null"):
            return frozenset()
        return frozenset({val.strip()})
    return frozenset(str(x).strip() for x in val if str(x).strip() and str(x) not in ("∅",))


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError(f"sport card must be mapping: {path}")
        return data
    # Minimal JSON-if-yaml-missing: try json
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    raise RuntimeError(
        f"PyYAML required to load sport cards ({path.name}). pip install pyyaml"
    )


def _card_from_dict(data: dict[str, Any], *, sport_key: str) -> SportCard:
    aliases_raw = data.get("signal_id_aliases") or {}
    aliases = (
        {str(k): str(v) for k, v in aliases_raw.items()}
        if isinstance(aliases_raw, dict)
        else {}
    )
    return SportCard(
        sport=str(data.get("sport") or sport_key),
        display_name=str(data.get("display_name") or sport_key.title()),
        onboarded=bool(data.get("onboarded", True)),
        individual_sport=bool(data.get("individual_sport", False)),
        primary=list(data.get("primary") or []),
        secondary=list(data.get("secondary") or []),
        tertiary=list(data.get("tertiary") or []),
        grade_floors=dict(data.get("grade_floors") or {}),
        hard_rejects=list(data.get("hard_rejects") or []),
        edges=dict(data.get("edges") or {}),
        domain_allowlist=[str(x) for x in (data.get("domain_allowlist") or [])],
        required_groups=list(data.get("required_groups") or []),
        notes=str(data.get("notes") or ""),
        version=int(data.get("version") or 1),
        schema_version=int(data.get("schema_version") or 1),
        signal_id_aliases=aliases,
    )


def load_sport_card(
    sport: str,
    cfg: dict[str, Any] | None = None,
    *,
    require_exists: bool = False,
) -> SportCard | None:
    key = normalize_sport_for_research(sport)
    path = sport_card_path(key, cfg)
    if not path.is_file():
        if require_exists:
            raise FileNotFoundError(path)
        return None
    data = _load_yaml(path)
    return _card_from_dict(data, sport_key=key)


def list_onboarded_sports(cfg: dict[str, Any] | None = None) -> list[str]:
    d = sport_cards_dir(cfg)
    if not d.is_dir():
        return []
    out: list[str] = []
    for p in sorted(d.glob("*.yaml")):
        if p.stem.startswith("_"):
            continue
        try:
            card = load_sport_card(p.stem, cfg)
            if card and card.onboarded:
                out.append(card.sport)
        except Exception:
            continue
    return out


def save_sport_card(card: SportCard, cfg: dict[str, Any] | None = None) -> Path:
    path = sport_card_path(card.sport, cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = card.to_dict()
    if yaml is not None:
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    else:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def default_quarantine_card(sport: str) -> SportCard:
    """Template card for unknown sports — not onboarded until filled."""
    key = normalize_sport_for_research(sport, default=sport or "unknown")
    return SportCard(
        sport=key,
        display_name=key.replace("_", " ").title(),
        onboarded=False,
        individual_sport=True,  # conservative: require H2H until proven team sport
        primary=[
            {
                "id": "h2h_matchup",
                "name": "H2H / matchup",
                "weight": 1.4,
                "markets": ["*"],
                "require_when": ["*", "underdog_hc"],
                "sources": ["Flashscore", "official"],
                "individual_h2h": True,
                "allows_negative": True,
            },
            {
                "id": "recent_form",
                "name": "Recent form",
                "weight": 1.3,
                "markets": ["*"],
                "require_when": ["*"],
                "sources": ["Flashscore", "Sofascore"],
            },
            {
                "id": "ranking_seed",
                "name": "Ranking / strength",
                "weight": 1.1,
                "markets": ["ml", "handicap"],
                "require_when": ["ml"],
                "sources": ["official rankings"],
            },
        ],
        secondary=[
            {
                "id": "venue_conditions",
                "name": "Venue / conditions",
                "weight": 0.7,
                "markets": ["*"],
                "require_when": [],
                "sources": ["Flashscore"],
            },
            {
                "id": "motivation_context",
                "name": "Motivation / tournament stage",
                "weight": 0.8,
                "markets": ["*"],
                "require_when": ["high_context"],
                "sources": ["official", "news"],
            },
        ],
        tertiary=[
            {
                "id": "line_movement",
                "name": "Line movement (soft)",
                "weight": 0.3,
                "markets": ["*"],
                "require_when": [],
                "sources": ["OddsPortal"],
            }
        ],
        grade_floors={
            "A": {"min_E": 0.72, "min_quality_sources": 6, "require_uncertainty": True},
            "B": {"min_E": 0.55, "min_quality_sources": 4, "require_r": 1.0},
            "C": {"min_E": 0.30, "min_quality_sources": 3},
            "F_quality_floor": 3,
        },
        hard_rejects=[
            {"id": "HR_NEG_H2H_UD", "when": "underdog_hc and negative_h2h"},
            {"id": "HR_NO_MATCHUP_UD", "when": "underdog_hc mid_band and not h2h_checked"},
            {"id": "HR_EMPTY_TAKEAWAYS", "when": "quality_sources < 3"},
            {"id": "HR_SPORT_UNKNOWN", "when": "not onboarded"},
        ],
        edges={
            "realistic": "Unknown until onboarded — quarantine; no mid-band places",
            "efficient_markets": "Assume efficient until proven otherwise",
            "inefficient_markets": "None claimed until card completed",
        },
        domain_allowlist=["flashscore.com", "sofascore.com"],
        notes=(
            "AUTO-GENERATED quarantine card. Fill primary sources and set onboarded: true "
            "only after hierarchy review. Prefer no bet until onboarded."
        ),
        version=1,
        schema_version=1,
        signal_id_aliases={"ranking_strength": "ranking_seed"},
    )


def ensure_sport_card(
    sport: str,
    cfg: dict[str, Any] | None = None,
    *,
    auto_create: bool = True,
) -> tuple[SportCard | None, bool]:
    """
    Load card; if missing and auto_create, write quarantine template.
    Returns (card, created).
    """
    key = normalize_sport_for_research(sport)
    existing = load_sport_card(key, cfg)
    if existing is not None:
        return existing, False
    if not auto_create:
        return None, False
    card = default_quarantine_card(key)
    save_sport_card(card, cfg)
    return card, True
