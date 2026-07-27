"""
Optional Playwright multi-resource fetch for SPA hosts (Flashscore, Sofascore).

Soft-import: clear playwright_not_installed when package/browser missing.
"""
from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import urlparse

from nt.match_intel.fetch.bundle import MatchFetchBundle

# XHR URL substrings to capture (refine in PR-3 with live fixtures)
XHR_ALLOW_SUBSTR = (
    "global/feed",
    "df_sur",
    "df_sui",
    "summary",
    "match",
    "standings",
    "h2h",
    "form",
    "participant",
)
XHR_DENY_SUBSTR = (
    "google",
    "facebook",
    "doubleclick",
    "hotjar",
    "analytics",
    "tracking",
    "adservice",
    "googletagmanager",
)


def playwright_available() -> bool:
    try:
        import playwright  # type: ignore  # noqa: F401
        from playwright.sync_api import sync_playwright  # type: ignore  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _xhr_allowed(url: str) -> bool:
    u = (url or "").lower()
    if any(d in u for d in XHR_DENY_SUBSTR):
        return False
    return any(a in u for a in XHR_ALLOW_SUBSTR)


def _extract_meta_from_html(html: str, title: str = "") -> dict[str, Any]:
    meta: dict[str, Any] = {
        "title": title or "",
        "home_name": None,
        "away_name": None,
        "competition_hint": None,
    }
    if not meta["title"] and html:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I | re.S)
        if m:
            meta["title"] = re.sub(r"\s+", " ", m.group(1)).strip()
    title = meta["title"] or ""
    if title:
        vs = re.search(
            r"(.+?)\s+vs\.?\s+(.+?)(?:\s*[|\-–—]\s*|\s*$)",
            title,
            re.I,
        )
        if vs:
            meta["home_name"] = vs.group(1).strip()
            meta["away_name"] = vs.group(2).strip()
    return meta


def fetch_playwright(
    url: str,
    *,
    timeout_s: float = 45.0,
    wait_selector_ms: int = 12_000,
    h2h_wait_ms: int = 8_000,
    fetch_h2h_tab: bool = True,
    max_xhr_bytes: int = 1_500_000,
    max_bytes: int = 2_500_000,
    sport: str | None = None,
) -> MatchFetchBundle:
    """
    Navigate URL with Chromium, wait for content, optional H2H tab, capture XHR JSON.

    Returns playwright_not_installed when Playwright is unavailable.
    """
    t0 = time.perf_counter()
    if not url or not str(url).strip():
        return MatchFetchBundle(
            ok=False, url=url or "", method="playwright", error="empty_url", duration_ms=0
        )
    url = str(url).strip()

    if not playwright_available():
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="playwright",
            error="playwright_not_installed",
            duration_ms=0,
        )

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:  # noqa: BLE001
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="playwright",
            error="playwright_not_installed",
            duration_ms=0,
        )

    xhr_json: list[dict[str, Any]] = []
    nav_ms = 0
    h2h_ms = 0
    summary_html = ""
    h2h_html: str | None = None
    final_url = url
    title = ""
    err: str | None = None
    status_code: int | None = None

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as ex:  # noqa: BLE001
                msg = str(ex).lower()
                if "executable" in msg or "install" in msg or "browser" in msg:
                    return MatchFetchBundle(
                        ok=False,
                        url=url,
                        method="playwright",
                        error="playwright_not_installed",
                        duration_ms=int((time.perf_counter() - t0) * 1000),
                    )
                return MatchFetchBundle(
                    ok=False,
                    url=url,
                    method="playwright",
                    error="fetch_failed",
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )

            context = browser.new_context()
            page = context.new_page()
            timeout_ms = int(max(1.0, timeout_s) * 1000)

            def _on_response(response: Any) -> None:
                try:
                    req_url = response.url or ""
                    if not _xhr_allowed(req_url):
                        return
                    ct = (response.headers or {}).get("content-type", "") or ""
                    if "json" not in ct.lower():
                        return
                    body = response.body()
                    if not body or len(body) > max_xhr_bytes:
                        return
                    import json

                    data = json.loads(body.decode("utf-8", errors="replace"))
                    xhr_json.append({"url": req_url, "data": data})
                except Exception:  # noqa: BLE001
                    return

            page.on("response", _on_response)

            t_nav = time.perf_counter()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if resp is not None:
                    status_code = resp.status
                    final_url = resp.url or url
            except Exception as ex:  # noqa: BLE001
                msg = str(ex).lower()
                if "timeout" in msg:
                    err = "timeout"
                elif "block" in msg:
                    err = "blocked"
                else:
                    err = "fetch_failed"
            nav_ms = int((time.perf_counter() - t_nav) * 1000)

            if err is None:
                # Wait for participant-like content (budget wait_selector_ms)
                try:
                    page.wait_for_timeout(min(500, wait_selector_ms))
                    # Best-effort selectors; all optional
                    for sel in (
                        "[class*='participant']",
                        "[class*='home']",
                        "text=/vs|–|-/i",
                    ):
                        try:
                            page.wait_for_selector(sel, timeout=min(3000, wait_selector_ms))
                            break
                        except Exception:  # noqa: BLE001
                            continue
                    # Consume remaining wait budget lightly
                    remaining = max(0, wait_selector_ms - 3500)
                    if remaining > 0:
                        page.wait_for_timeout(min(remaining, 2000))
                except Exception:  # noqa: BLE001
                    pass

                try:
                    title = page.title() or ""
                    summary_html = page.content() or ""
                    if len(summary_html) > max_bytes:
                        summary_html = summary_html[:max_bytes]
                except Exception:  # noqa: BLE001
                    summary_html = ""

                # Challenge / empty shell heuristics
                lower = (summary_html or "").lower()
                if any(
                    m in lower
                    for m in (
                        "cf-browser-verification",
                        "just a moment",
                        "access denied",
                        "captcha",
                    )
                ):
                    err = "blocked"
                elif len(re.sub(r"<[^>]+>", " ", summary_html or "")) < 80:
                    err = "js_shell_empty"

            if err is None and fetch_h2h_tab:
                t_h2h = time.perf_counter()
                try:
                    # Click H2H tab if present
                    for label in ("H2H", "Head to head", "Head-to-head"):
                        loc = page.get_by_role("link", name=re.compile(label, re.I))
                        if loc.count() == 0:
                            loc = page.get_by_text(re.compile(f"^{label}$", re.I))
                        if loc.count() > 0:
                            loc.first.click(timeout=min(3000, h2h_wait_ms))
                            page.wait_for_timeout(min(h2h_wait_ms, 4000))
                            h2h_html = page.content() or None
                            if h2h_html and len(h2h_html) > max_bytes:
                                h2h_html = h2h_html[:max_bytes]
                            break
                except Exception:  # noqa: BLE001
                    h2h_html = None
                h2h_ms = int((time.perf_counter() - t_h2h) * 1000)

            context.close()
            browser.close()
    except Exception as ex:  # noqa: BLE001
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="playwright",
            error=_map_pw_error(ex),
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )

    duration_ms = int((time.perf_counter() - t0) * 1000)
    meta = _extract_meta_from_html(summary_html, title=title)
    if err:
        return MatchFetchBundle(
            ok=False,
            url=url,
            final_url=final_url,
            method="playwright",
            html=summary_html,
            error=err,
            duration_ms=duration_ms,
            xhrs=list(xhr_json),
            page_meta=meta,
            status_code=status_code,
            resources={
                "summary_html": summary_html,
                "h2h_html": h2h_html,
                "xhr_json": list(xhr_json),
                "markdown": None,
            },
            timings_ms={"nav": nav_ms, "h2h": h2h_ms, "total": duration_ms},
            bytes=len((summary_html or "").encode("utf-8", errors="replace")),
        )

    if not summary_html:
        return MatchFetchBundle(
            ok=False,
            url=url,
            final_url=final_url,
            method="playwright",
            error="fetch_failed",
            duration_ms=duration_ms,
            xhrs=list(xhr_json),
            timings_ms={"nav": nav_ms, "h2h": h2h_ms, "total": duration_ms},
        )

    return MatchFetchBundle(
        ok=True,
        url=url,
        final_url=final_url,
        method="playwright",
        html=summary_html,
        markdown="",
        error=None,
        duration_ms=duration_ms,
        xhrs=list(xhr_json),
        page_meta=meta,
        status_code=status_code,
        resources={
            "summary_html": summary_html,
            "h2h_html": h2h_html,
            "xhr_json": list(xhr_json),
            "markdown": None,
        },
        timings_ms={"nav": nav_ms, "h2h": h2h_ms, "total": duration_ms},
        bytes=len(summary_html.encode("utf-8", errors="replace")),
    )


def _map_pw_error(ex: BaseException) -> str:
    msg = str(ex).lower()
    if "timeout" in msg:
        return "timeout"
    if "executable" in msg or "playwright" in msg and "install" in msg:
        return "playwright_not_installed"
    return "fetch_failed"


def host_needs_playwright(url: str, playwright_hosts: list[str] | None = None) -> bool:
    hosts = playwright_hosts or [
        "flashscore.com",
        "www.flashscore.com",
        "sofascore.com",
        "www.sofascore.com",
    ]
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:  # noqa: BLE001
        return False
    host_bare = host[4:] if host.startswith("www.") else host
    for h in hosts:
        hb = h.lower().removeprefix("www.")
        if host == h.lower() or host_bare == hb or host.endswith("." + hb):
            return True
    return False
