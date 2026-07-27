"""
URL discovery for Match Intelligence (PR-2).

Priority (stop at first high-confidence URL):
  D0  operator alias  → data/state/match_aliases.json
  D1  explicit CLI --url  (caller skips this module)
  D2  Flashscore search → parse result list → confidence gate
  D3  soft fail → url_not_found

Network fetch of search pages only when allow_network; tests inject
search HTML/markdown offline. Never live-parses match fields (PR-3).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus, urljoin, urlparse

from nt.fetchers.names import split_match
from nt.match_intel.matching import load_aliases, match_confidence, resolve_match
from nt.match_intel.schema import mic_match_key
from nt.odds_common import normalize_match_key

# Design §2.3: accept exact|alias|fuzzy with score ≥ min_match_score
DEFAULT_MIN_MATCH_SCORE = 0.85
DEFAULT_FLASHSCORE_HOST = "https://www.flashscore.com"
DEFAULT_ALIAS_PATH = "data/state/match_aliases.json"

# Match event links (new Flashscore full-page paths + legacy /match/id/)
_MATCH_HREF_RE = re.compile(
    r"""(?P<href>(?:https?://(?:www\.)?flashscore\.[a-z.]+)?"""
    r"""/match/(?:football/)?[^\s"'<>#?]+)""",
    re.I,
)
_MD_LINK_RE = re.compile(
    r"""\[(?P<label>[^\]]+)\]\((?P<href>(?:https?://[^)\s]+|/match/[^)\s]+))\)""",
    re.I,
)
_VS_SPLIT_RE = re.compile(
    r"""\s+(?:vs\.?|v|[-–—])\s+""",
    re.I,
)
# Strip query/fragment and trailing slash for stable URLs
_WS_RE = re.compile(r"\s+")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _discovery_cfg(mi: dict[str, Any] | None) -> dict[str, Any]:
    mi = mi or {}
    disc = mi.get("discovery") if isinstance(mi.get("discovery"), dict) else {}
    return dict(disc or {})


def min_match_score(mi: dict[str, Any] | None = None) -> float:
    disc = _discovery_cfg(mi)
    mi = mi or {}
    raw = disc.get("min_match_score", mi.get("min_match_score", DEFAULT_MIN_MATCH_SCORE))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return DEFAULT_MIN_MATCH_SCORE


def flashscore_host(mi: dict[str, Any] | None = None) -> str:
    disc = _discovery_cfg(mi)
    mi = mi or {}
    host = str(
        disc.get("flashscore_host")
        or mi.get("flashscore_host")
        or DEFAULT_FLASHSCORE_HOST
    ).strip()
    if not host.startswith("http"):
        host = "https://" + host.lstrip("/")
    return host.rstrip("/")


def alias_path_from_cfg(mi: dict[str, Any] | None = None) -> Path:
    mi = mi or {}
    disc = _discovery_cfg(mi)
    raw = disc.get("alias_path") or mi.get("alias_path") or DEFAULT_ALIAS_PATH
    return Path(str(raw))


def write_aliases_enabled(mi: dict[str, Any] | None = None) -> bool:
    mi = mi or {}
    disc = _discovery_cfg(mi)
    if "write_aliases" in disc:
        return bool(disc.get("write_aliases"))
    return bool(mi.get("write_aliases"))


@dataclass
class DiscoveryCandidate:
    """One row from Flashscore (or similar) search results."""

    url: str
    home_name: str | None = None
    away_name: str | None = None
    competition_hint: str | None = None
    start_time_hint: str | None = None
    title: str = ""

    def label(self) -> str:
        if self.home_name and self.away_name:
            return f"{self.home_name} vs {self.away_name}"
        return self.title or self.url


@dataclass
class DiscoveryResult:
    """Outcome of alias / search URL resolution for one match."""

    ok: bool = False
    url: str | None = None
    confidence: str = "none"  # exact | alias | fuzzy | none
    score: float = 0.0
    source: str = "none"  # alias | search | none
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    error: str | None = None
    search_url: str | None = None
    query: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "url": self.url,
            "confidence": self.confidence,
            "score": self.score,
            "source": self.source,
            "error": self.error,
            "search_url": self.search_url,
            "query": self.query,
            "candidates": [
                {
                    "url": c.url,
                    "home_name": c.home_name,
                    "away_name": c.away_name,
                    "competition_hint": c.competition_hint,
                    "start_time_hint": c.start_time_hint,
                    "title": c.title,
                }
                for c in self.candidates
            ],
        }


# ---------------------------------------------------------------------------
# Aliases load / save / lookup
# ---------------------------------------------------------------------------


def load_alias_store(path: Path | str | None) -> dict[str, Any]:
    """
    Load match_aliases.json as a dict with an ``aliases`` list.

    Accepts ``{}``, ``{"aliases": []}``, or a bare list (normalized to dict).
    """
    if not path:
        return {"aliases": [], "updated_at": None}
    p = Path(path)
    if not p.is_file():
        return {"aliases": [], "updated_at": None}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"aliases": [], "updated_at": None}
    if isinstance(data, list):
        return {"aliases": [x for x in data if isinstance(x, dict)], "updated_at": None}
    if not isinstance(data, dict):
        return {"aliases": [], "updated_at": None}
    aliases = data.get("aliases")
    if not isinstance(aliases, list):
        aliases = []
    return {
        "aliases": [x for x in aliases if isinstance(x, dict)],
        "updated_at": data.get("updated_at"),
    }


def save_alias_store(path: Path | str, store: dict[str, Any]) -> Path:
    """Atomic-ish write of alias store (tmp + replace)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "aliases": list(store.get("aliases") or []),
        "updated_at": store.get("updated_at") or _utc_now_iso(),
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)
    return p


def lookup_alias_url(
    match: str,
    aliases: list[dict[str, Any]] | None,
    *,
    sport: str | None = None,
) -> dict[str, Any] | None:
    """
    Return first alias row with a usable URL for this odds match.

    Row keys: odds_match / match, url / flashscore_url, sport (optional).
    """
    key = normalize_match_key(match)
    if not key:
        return None
    for row in aliases or []:
        if not isinstance(row, dict):
            continue
        if sport and row.get("sport") and str(row["sport"]).lower() != str(sport).lower():
            continue
        odds_alias = str(row.get("odds_match") or row.get("match") or "").strip()
        if not odds_alias or normalize_match_key(odds_alias) != key:
            continue
        url = str(
            row.get("url")
            or row.get("flashscore_url")
            or row.get("match_url")
            or ""
        ).strip()
        if url and url.startswith("http"):
            return row
    return None


def upsert_alias(
    path: Path | str,
    *,
    match: str,
    url: str,
    sport: str | None = None,
    confidence: str | None = None,
    source: str = "discovery",
) -> dict[str, Any]:
    """
    Insert or update a high-confidence alias row. Returns the written row.
    """
    store = load_alias_store(path)
    aliases = list(store.get("aliases") or [])
    key = normalize_match_key(match)
    row: dict[str, Any] = {
        "odds_match": match,
        "match_key": mic_match_key(match),
        "url": url,
        "flashscore_url": url,
        "sport": (sport or "football").strip().lower(),
        "confidence": confidence or "fuzzy",
        "source": source,
        "updated_at": _utc_now_iso(),
    }
    replaced = False
    for i, existing in enumerate(aliases):
        odds_alias = str(existing.get("odds_match") or existing.get("match") or "")
        if odds_alias and normalize_match_key(odds_alias) == key:
            merged = dict(existing)
            merged.update(row)
            aliases[i] = merged
            row = merged
            replaced = True
            break
    if not replaced:
        aliases.append(row)
    store["aliases"] = aliases
    store["updated_at"] = _utc_now_iso()
    save_alias_store(path, store)
    return row


# ---------------------------------------------------------------------------
# Flashscore search URL + result parse
# ---------------------------------------------------------------------------


def build_search_query(match: str) -> str:
    """Build site-search query from odds match string: \"Home Away\"."""
    home, away = split_match(match)
    if home and away:
        return f"{home} {away}".strip()
    return (match or "").strip()


def build_flashscore_search_url(
    match: str,
    *,
    host: str | None = None,
    mi_cfg: dict[str, Any] | None = None,
) -> str:
    """
    Stable search GET for Flashscore.

    Pattern: ``{host}/search/?q={quote(home+away)}``
    (not a fragile CDN path; actual result HTML is captured into fixtures).
    """
    base = (host or flashscore_host(mi_cfg)).rstrip("/")
    q = build_search_query(match)
    return f"{base}/search/?q={quote_plus(q)}"


def _normalize_match_url(href: str, *, base: str = DEFAULT_FLASHSCORE_HOST) -> str | None:
    href = (href or "").strip()
    if not href:
        return None
    # Ignore pure search / static assets
    low = href.lower()
    if any(x in low for x in ("/search", "javascript:", "mailto:", "#", ".css", ".js", ".png", ".jpg")):
        if "/match/" not in low:
            return None
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("/"):
        href = urljoin(base.rstrip("/") + "/", href.lstrip("/"))
    if not href.startswith("http"):
        return None
    # Must look like a match event page
    path = urlparse(href).path or ""
    if "/match/" not in path:
        return None
    # Drop query/fragment
    parsed = urlparse(href)
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if clean.endswith("/") and clean.count("/") > 3:
        clean = clean.rstrip("/")
    return clean


def _split_teams_from_label(label: str) -> tuple[str | None, str | None]:
    label = _WS_RE.sub(" ", (label or "").strip())
    if not label:
        return None, None
    # Drop trailing competition pipe segments: "A vs B | League"
    if "|" in label:
        label = label.split("|", 1)[0].strip()
    parts = _VS_SPLIT_RE.split(label, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return None, None


def _extract_surrounding_text(html: str, href: str, *, radius: int = 180) -> str:
    """Best-effort local context around an href for team names."""
    if not html or not href:
        return ""
    # Prefer relative path for search in HTML
    path = urlparse(href).path if href.startswith("http") else href
    idx = html.find(path) if path else -1
    if idx < 0 and href:
        idx = html.find(href)
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(html), idx + len(path) + radius)
    chunk = html[start:end]
    # Strip tags lightly
    text = re.sub(r"<[^>]+>", " ", chunk)
    text = _WS_RE.sub(" ", text).strip()
    return text


def parse_flashscore_search_results(
    content: str,
    *,
    base_host: str = DEFAULT_FLASHSCORE_HOST,
) -> list[DiscoveryCandidate]:
    """
    Parse Flashscore search HTML or markdown into candidate match URLs.

    Accepts mixed HTML+markdown. Dedupes by normalized URL (first wins).
    """
    if not content or not str(content).strip():
        return []
    text = str(content)
    base = base_host.rstrip("/")
    found: list[DiscoveryCandidate] = []
    seen: set[str] = set()

    def _add(
        url: str,
        *,
        home: str | None = None,
        away: str | None = None,
        title: str = "",
        competition: str | None = None,
    ) -> None:
        nu = _normalize_match_url(url, base=base)
        if not nu or nu in seen:
            return
        seen.add(nu)
        if not home and not away and title:
            home, away = _split_teams_from_label(title)
        found.append(
            DiscoveryCandidate(
                url=nu,
                home_name=home,
                away_name=away,
                competition_hint=competition,
                title=title or (f"{home} vs {away}" if home and away else ""),
            )
        )

    # Markdown links first (Firecrawl often returns markdown)
    for m in _MD_LINK_RE.finditer(text):
        href = m.group("href")
        label = _WS_RE.sub(" ", m.group("label")).strip()
        if "/match/" not in href.lower() and not href.lower().startswith("http"):
            # relative may still be match
            if "/match/" not in href:
                continue
        home, away = _split_teams_from_label(label)
        _add(href, home=home, away=away, title=label)

    # HTML / bare hrefs
    for m in _MATCH_HREF_RE.finditer(text):
        href = m.group("href")
        local = _extract_surrounding_text(text, href)
        home, away = _split_teams_from_label(local)
        title = ""
        if home and away:
            title = f"{home} vs {away}"
        elif local:
            # Take a short window as weak title
            title = local[:120]
        _add(href, home=home, away=away, title=title)

    # data-event-url / href="/match/..." attribute forms already covered by _MATCH_HREF_RE

    return found


def rank_candidates(
    match: str,
    candidates: list[DiscoveryCandidate],
    *,
    aliases: list[dict[str, Any]] | None = None,
    sport: str | None = None,
    min_score: float = DEFAULT_MIN_MATCH_SCORE,
) -> DiscoveryResult:
    """
    Score candidates with matching.py; accept best with confidence gate.

    Accept when confidence ∈ {exact, alias, fuzzy} AND score ≥ min_score.
    """
    if not candidates:
        return DiscoveryResult(ok=False, error="url_not_found", source="search")

    labels = [c.label() for c in candidates]
    best_resolve = resolve_match(match, labels, aliases=aliases, sport=sport)

    # Map back to candidate + recompute full confidence with aliases
    best: DiscoveryResult = DiscoveryResult(
        ok=False,
        source="search",
        candidates=list(candidates),
        error="url_not_found",
    )
    order = {"exact": 3, "alias": 2, "fuzzy": 1, "none": 0}
    min_s = float(min_score)

    for cand in candidates:
        conf, score = match_confidence(
            match, cand.label(), aliases=aliases, sport=sport
        )
        if order.get(conf, 0) < 1:
            continue
        if score < min_s and conf == "fuzzy":
            # exact/alias always accept even if score slightly under (alias is 0.95)
            continue
        if conf in ("exact", "alias") or (conf == "fuzzy" and score >= min_s):
            if order.get(conf, 0) > order.get(best.confidence, 0) or (
                conf == best.confidence and score > best.score
            ):
                best = DiscoveryResult(
                    ok=True,
                    url=cand.url,
                    confidence=conf,
                    score=float(score),
                    source="search",
                    candidates=list(candidates),
                    error=None,
                )

    # If resolve_match found something but loop skipped due to min_score, honor exact/alias
    if not best.ok and best_resolve.get("matched") and best_resolve.get("candidate"):
        conf = str(best_resolve.get("confidence") or "none")
        score = float(best_resolve.get("score") or 0.0)
        if conf in ("exact", "alias") or (conf == "fuzzy" and score >= min_s):
            for cand in candidates:
                if cand.label() == best_resolve["candidate"]:
                    best = DiscoveryResult(
                        ok=True,
                        url=cand.url,
                        confidence=conf,
                        score=score,
                        source="search",
                        candidates=list(candidates),
                        error=None,
                    )
                    break

    return best


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def discover_match_url(
    match: str,
    *,
    sport: str = "football",
    mi_cfg: dict[str, Any] | None = None,
    allow_network: bool = False,
    search_html: str | None = None,
    search_markdown: str | None = None,
    fetch_search: Callable[[str], Any] | None = None,
    writeback: bool | None = None,
) -> DiscoveryResult:
    """
    Resolve a match page URL via aliases then Flashscore search.

    Parameters
    ----------
    search_html / search_markdown
        Offline fixtures (tests). When set, no network is used for search.
    fetch_search
        Optional callable(url) → object with .ok/.html/.markdown (or a str body).
        When allow_network and no fixture body, default uses fetch router.
    writeback
        Override config write_aliases; on success + high confidence, persist alias.
    """
    mi = dict(mi_cfg or {})
    sport_n = (sport or "football").strip().lower()
    a_path = alias_path_from_cfg(mi)
    store = load_alias_store(a_path)
    aliases = list(store.get("aliases") or [])
    # Also accept matching.load_aliases shape
    if not aliases:
        aliases = load_aliases(a_path)

    # D0 — alias
    hit = lookup_alias_url(match, aliases, sport=sport_n)
    if hit:
        url = str(hit.get("url") or hit.get("flashscore_url") or "").strip()
        return DiscoveryResult(
            ok=True,
            url=url,
            confidence="alias",
            score=0.95,
            source="alias",
            candidates=[
                DiscoveryCandidate(
                    url=url,
                    title=str(hit.get("odds_match") or match),
                )
            ],
            query=build_search_query(match),
        )

    min_score = min_match_score(mi)
    host = flashscore_host(mi)
    search_url = build_flashscore_search_url(match, host=host, mi_cfg=mi)
    query = build_search_query(match)

    body = ""
    if search_html:
        body = search_html
    if search_markdown:
        body = (body + "\n" + search_markdown) if body else search_markdown

    if not body and allow_network:
        body = _fetch_search_body(
            search_url,
            mi_cfg=mi,
            fetch_search=fetch_search,
            match_key=mic_match_key(match),
        )
    elif not body and not allow_network:
        return DiscoveryResult(
            ok=False,
            error="url_not_found",
            source="none",
            search_url=search_url,
            query=query,
        )

    if not body or not str(body).strip():
        return DiscoveryResult(
            ok=False,
            error="url_not_found",
            source="search",
            search_url=search_url,
            query=query,
        )

    candidates = parse_flashscore_search_results(body, base_host=host)
    ranked = rank_candidates(
        match,
        candidates,
        aliases=aliases,
        sport=sport_n,
        min_score=min_score,
    )
    ranked.search_url = search_url
    ranked.query = query
    ranked.candidates = candidates

    if ranked.ok and ranked.url:
        do_write = write_aliases_enabled(mi) if writeback is None else bool(writeback)
        # Only write high-confidence (exact|alias|fuzzy accepted already)
        if do_write and ranked.confidence in ("exact", "alias", "fuzzy"):
            try:
                upsert_alias(
                    a_path,
                    match=match,
                    url=ranked.url,
                    sport=sport_n,
                    confidence=ranked.confidence,
                    source="discovery_search",
                )
            except OSError:
                pass
        return ranked

    ranked.ok = False
    ranked.error = ranked.error or "url_not_found"
    return ranked


def _fetch_search_body(
    search_url: str,
    *,
    mi_cfg: dict[str, Any],
    fetch_search: Callable[[str], Any] | None,
    match_key: str,
) -> str:
    """
    Fetch search page via injectable callable or fetch router (Firecrawl prefer).

    CI safety: without Firecrawl or Playwright configured/available, do **not**
    fall through to bare HTTP (Flashscore search is SPA; would risk live sockets
    and empty shells in offline tests).
    """
    if fetch_search is not None:
        try:
            res = fetch_search(search_url)
        except Exception:  # noqa: BLE001
            return ""
        return _body_from_fetch_result(res)

    try:
        from nt.match_intel.fetch.firecrawl_fetch import (
            firecrawl_cli_available,
            firecrawl_configured,
            firecrawl_sdk_available,
        )
        from nt.match_intel.fetch.playwright_fetch import playwright_available
    except Exception:  # noqa: BLE001
        return ""

    has_fc = bool(
        firecrawl_configured() or firecrawl_sdk_available() or firecrawl_cli_available()
    )
    has_pw = bool(playwright_available())
    if not has_fc and not has_pw:
        return ""

    try:
        from nt.match_intel.fetch.router import fetch_match_bundle
    except Exception:  # noqa: BLE001
        return ""

    try:
        bundle = fetch_match_bundle(
            search_url,
            mi_cfg=mi_cfg,
            match_key=f"search_{match_key}",
            source="flashscore_search",
            sport="football",
            use_cache=True,
            force=False,
        )
    except Exception:  # noqa: BLE001
        return ""
    return _body_from_fetch_result(bundle)


def _body_from_fetch_result(res: Any) -> str:
    if res is None:
        return ""
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        if not res.get("ok", True) and not (res.get("html") or res.get("markdown")):
            return ""
        return str(res.get("html") or "") + "\n" + str(res.get("markdown") or "")
    # MatchFetchBundle-like
    ok = getattr(res, "ok", True)
    html = getattr(res, "html", None) or getattr(res, "summary_html", None) or ""
    md = getattr(res, "markdown", None) or ""
    if ok is False and not html and not md:
        return ""
    return str(html or "") + "\n" + str(md or "")
