"""MatchFetchBundle — multi-resource fetch result for MIC live path."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class MatchFetchBundle:
    """
    Result of fetching a match page (possibly multi-resource).

    Simple path fields (PR-1): url, html, markdown, method, ok, error, duration_ms, xhrs.
    Extended multi-resource fields ready for Playwright H2H/XHR (PR-1 hooks / PR-3 parse).
    """

    ok: bool = False
    url: str = ""
    final_url: str = ""
    method: str = ""  # firecrawl | playwright | http | cache | fixture
    html: str = ""
    markdown: str = ""
    error: str | None = None
    duration_ms: int = 0
    xhrs: list[dict[str, Any]] = field(default_factory=list)
    # Multi-resource (Playwright)
    resources: dict[str, Any] = field(default_factory=dict)
    page_meta: dict[str, Any] = field(default_factory=dict)
    status_code: int | None = None
    fetched_at: str = ""
    bytes: int = 0
    timings_ms: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.fetched_at:
            self.fetched_at = _utc_now_iso()
        if not self.final_url and self.url:
            self.final_url = self.url
        # Keep resources in sync with top-level html/markdown when empty
        if self.html and not self.resources.get("summary_html"):
            self.resources = dict(self.resources or {})
            self.resources.setdefault("summary_html", self.html)
        if self.markdown and not self.resources.get("markdown"):
            self.resources = dict(self.resources or {})
            self.resources.setdefault("markdown", self.markdown)
        if self.xhrs and not self.resources.get("xhr_json"):
            self.resources = dict(self.resources or {})
            self.resources.setdefault("xhr_json", list(self.xhrs))
        if not self.bytes and self.html:
            self.bytes = len(self.html.encode("utf-8", errors="replace"))

    @property
    def summary_html(self) -> str:
        return str(self.resources.get("summary_html") or self.html or "")

    def identity_text(self) -> str:
        """Best-effort page teams/title string for match_confidence."""
        meta = self.page_meta or {}
        home = str(meta.get("home_name") or "").strip()
        away = str(meta.get("away_name") or "").strip()
        if home and away:
            return f"{home} vs {away}"
        title = str(meta.get("title") or "").strip()
        if title:
            return title
        # Fall back to bare HTML title tag
        html = self.summary_html
        if html:
            import re

            m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
            if m:
                return m.group(1).strip()
        return ""


def bundle_to_dict(bundle: MatchFetchBundle) -> dict[str, Any]:
    return asdict(bundle)


def bundle_from_dict(data: dict[str, Any] | None) -> MatchFetchBundle | None:
    if not data or not isinstance(data, dict):
        return None
    known = {f.name for f in MatchFetchBundle.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    kwargs = {k: v for k, v in data.items() if k in known}
    try:
        return MatchFetchBundle(**kwargs)
    except TypeError:
        return None
