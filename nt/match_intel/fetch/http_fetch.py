"""Static HTML fetch via httpx (if installed) or urllib."""
from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import urlparse

from nt.match_intel.fetch.bundle import MatchFetchBundle

USER_AGENT = (
    "Mozilla/5.0 (compatible; NT-MatchIntel/1.0; +local research tool)"
)
MAX_BYTES_DEFAULT = 2_500_000


def httpx_available() -> bool:
    try:
        import httpx  # type: ignore  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _extract_page_meta(html: str) -> dict[str, Any]:
    meta: dict[str, Any] = {"title": "", "home_name": None, "away_name": None}
    if not html:
        return meta
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        meta["title"] = title
        # Common pattern: "Home vs Away | Competition"
        vs = re.search(
            r"(.+?)\s+vs\.?\s+(.+?)(?:\s*[|\-–—]\s*|\s*$)",
            title,
            re.I,
        )
        if vs:
            meta["home_name"] = vs.group(1).strip()
            meta["away_name"] = vs.group(2).strip()
    # data-* fixtures / simple attributes (offline-friendly)
    dh = re.search(r'data-home(?:-name)?=["\']([^"\']+)["\']', html, re.I)
    da = re.search(r'data-away(?:-name)?=["\']([^"\']+)["\']', html, re.I)
    if dh:
        meta["home_name"] = dh.group(1).strip()
    if da:
        meta["away_name"] = da.group(1).strip()
    return meta


def _looks_like_js_shell(html: str) -> bool:
    if not html or len(html) < 200:
        return True
    lower = html.lower()
    # Very thin SPA shells without participant text
    textish = re.sub(r"<script[\s\S]*?</script>", " ", lower, flags=re.I)
    textish = re.sub(r"<style[\s\S]*?</style>", " ", textish, flags=re.I)
    textish = re.sub(r"<[^>]+>", " ", textish)
    textish = re.sub(r"\s+", " ", textish).strip()
    if len(textish) < 80:
        return True
    return False


def fetch_http(
    url: str,
    *,
    timeout_s: float = 45.0,
    max_bytes: int = MAX_BYTES_DEFAULT,
    headers: dict[str, str] | None = None,
) -> MatchFetchBundle:
    """
    GET URL as text/html. Never raises.

    Prefer httpx when installed; else stdlib urllib.
    """
    t0 = time.perf_counter()
    if not url or not str(url).strip():
        return MatchFetchBundle(
            ok=False,
            url=url or "",
            method="http",
            error="empty_url",
            duration_ms=0,
        )
    url = str(url).strip()
    hdrs = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        hdrs.update(headers)

    html = ""
    status: int | None = None
    final_url = url
    err: str | None = None

    try:
        if httpx_available():
            import httpx  # type: ignore

            with httpx.Client(
                timeout=timeout_s,
                follow_redirects=True,
                headers=hdrs,
            ) as client:
                resp = client.get(url)
                status = int(resp.status_code)
                final_url = str(resp.url)
                raw = resp.content or b""
                if len(raw) > max_bytes:
                    raw = raw[:max_bytes]
                html = raw.decode(resp.encoding or "utf-8", errors="replace")
                if status >= 400:
                    err = f"http_{status}"
        else:
            import urllib.error
            import urllib.request

            req = urllib.request.Request(url, headers=hdrs)
            try:
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    status = int(getattr(resp, "status", None) or resp.getcode() or 200)
                    final_url = resp.geturl() or url
                    raw = resp.read(max_bytes + 1)
                    if len(raw) > max_bytes:
                        raw = raw[:max_bytes]
                    html = raw.decode("utf-8", errors="replace")
            except urllib.error.HTTPError as he:
                status = int(he.code)
                err = f"http_{status}"
                try:
                    raw = he.read(max_bytes)
                    html = raw.decode("utf-8", errors="replace") if raw else ""
                except Exception:  # noqa: BLE001
                    html = ""
    except TimeoutError:
        err = "timeout"
    except Exception as ex:  # noqa: BLE001
        msg = str(ex).lower()
        if "timed out" in msg or "timeout" in msg:
            err = "timeout"
        else:
            err = "fetch_failed"

    duration_ms = int((time.perf_counter() - t0) * 1000)
    if err in ("timeout",) or (err and err.startswith("http_") and not html):
        return MatchFetchBundle(
            ok=False,
            url=url,
            final_url=final_url,
            method="http",
            html=html,
            error=err,
            duration_ms=duration_ms,
            status_code=status,
            page_meta=_extract_page_meta(html),
            timings_ms={"total": duration_ms},
        )

    if not html:
        return MatchFetchBundle(
            ok=False,
            url=url,
            final_url=final_url,
            method="http",
            error=err or "fetch_failed",
            duration_ms=duration_ms,
            status_code=status,
            timings_ms={"total": duration_ms},
        )

    meta = _extract_page_meta(html)
    # Hosts that need JS: flag shell (router may escalate)
    host = (urlparse(final_url or url).netloc or "").lower()
    if _looks_like_js_shell(html):
        return MatchFetchBundle(
            ok=False,
            url=url,
            final_url=final_url,
            method="http",
            html=html,
            error="js_shell_empty",
            duration_ms=duration_ms,
            status_code=status,
            page_meta=meta,
            resources={"summary_html": html},
            timings_ms={"total": duration_ms},
            bytes=len(html.encode("utf-8", errors="replace")),
        )

    if err and err.startswith("http_"):
        return MatchFetchBundle(
            ok=False,
            url=url,
            final_url=final_url,
            method="http",
            html=html,
            error=err,
            duration_ms=duration_ms,
            status_code=status,
            page_meta=meta,
            resources={"summary_html": html},
            timings_ms={"total": duration_ms},
        )

    return MatchFetchBundle(
        ok=True,
        url=url,
        final_url=final_url,
        method="http",
        html=html,
        markdown="",
        error=None,
        duration_ms=duration_ms,
        status_code=status,
        page_meta=meta,
        resources={"summary_html": html, "h2h_html": None, "xhr_json": [], "markdown": None},
        timings_ms={"total": duration_ms},
        bytes=len(html.encode("utf-8", errors="replace")),
    )
