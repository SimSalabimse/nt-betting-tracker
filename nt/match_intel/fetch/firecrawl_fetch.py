"""
Real Firecrawl fetch: SDK (FIRECRAWL_API_KEY) or CLI subprocess.

Never hardcodes API keys. Offline tests mock this module.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from typing import Any

from nt.match_intel.fetch.bundle import MatchFetchBundle


def firecrawl_sdk_available() -> bool:
    try:
        import firecrawl  # type: ignore  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def firecrawl_cli_available() -> bool:
    return bool(shutil.which("firecrawl"))


def firecrawl_api_key() -> str | None:
    """Return API key from env if set (never hardcode)."""
    for name in ("FIRECRAWL_API_KEY", "FIRECRAWL_KEY", "FC_API_KEY"):
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    return None


def firecrawl_configured() -> bool:
    """True when SDK or CLI can realistically run (key optional for some CLI auth)."""
    if firecrawl_api_key() and firecrawl_sdk_available():
        return True
    if firecrawl_cli_available():
        return True
    if firecrawl_api_key() and firecrawl_sdk_available() is False:
        # key present but package missing — still "configured" intent; will error clearly
        return bool(firecrawl_api_key())
    return False


def _extract_title_meta(html: str, markdown: str) -> dict[str, Any]:
    meta: dict[str, Any] = {"title": "", "home_name": None, "away_name": None}
    src = html or ""
    m = re.search(r"<title[^>]*>([^<]+)</title>", src, re.I | re.S)
    title = ""
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
    if not title and markdown:
        # first non-empty markdown line as weak title
        for line in markdown.splitlines():
            line = line.strip().lstrip("#").strip()
            if line:
                title = line[:200]
                break
    meta["title"] = title
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


def _scrape_via_sdk(url: str, *, timeout_s: float, api_key: str) -> MatchFetchBundle:
    t0 = time.perf_counter()
    try:
        client = None
        # firecrawl-py modern
        try:
            from firecrawl import FirecrawlApp  # type: ignore

            client = FirecrawlApp(api_key=api_key)
        except Exception:  # noqa: BLE001
            client = None
        if client is None:
            try:
                from firecrawl import Firecrawl  # type: ignore

                client = Firecrawl(api_key=api_key)
            except Exception:  # noqa: BLE001
                client = None
        if client is None:
            return MatchFetchBundle(
                ok=False,
                url=url,
                method="firecrawl",
                error="firecrawl_not_installed",
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )

        result: Any = None
        # Try common method names across package versions
        for meth_name in ("scrape_url", "scrape"):
            meth = getattr(client, meth_name, None)
            if not callable(meth):
                continue
            try:
                # Prefer formats that include markdown + html when supported
                try:
                    result = meth(url, formats=["markdown", "html"])
                except TypeError:
                    try:
                        result = meth(url, params={"formats": ["markdown", "html"]})
                    except TypeError:
                        result = meth(url)
                break
            except Exception as ex:  # noqa: BLE001
                return MatchFetchBundle(
                    ok=False,
                    url=url,
                    method="firecrawl",
                    error=_classify_ex(ex),
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )

        if result is None:
            return MatchFetchBundle(
                ok=False,
                url=url,
                method="firecrawl",
                error="firecrawl_not_installed",
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )

        markdown, html = _parse_sdk_result(result)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if not markdown and not html:
            return MatchFetchBundle(
                ok=False,
                url=url,
                method="firecrawl",
                error="fetch_failed",
                duration_ms=duration_ms,
            )
        meta = _extract_title_meta(html, markdown)
        return MatchFetchBundle(
            ok=True,
            url=url,
            final_url=url,
            method="firecrawl",
            html=html,
            markdown=markdown,
            error=None,
            duration_ms=duration_ms,
            page_meta=meta,
            resources={
                "summary_html": html,
                "h2h_html": None,
                "xhr_json": [],
                "markdown": markdown or None,
            },
            timings_ms={"total": duration_ms},
            bytes=len((html or markdown).encode("utf-8", errors="replace")),
        )
    except Exception as ex:  # noqa: BLE001
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="firecrawl",
            error=_classify_ex(ex),
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )


def _parse_sdk_result(result: Any) -> tuple[str, str]:
    markdown = ""
    html = ""
    if result is None:
        return markdown, html
    if isinstance(result, dict):
        data = result.get("data") if isinstance(result.get("data"), dict) else result
        markdown = str(data.get("markdown") or result.get("markdown") or "")
        html = str(data.get("html") or result.get("html") or "")
        return markdown, html
    # object with attributes
    markdown = str(getattr(result, "markdown", None) or "")
    html = str(getattr(result, "html", None) or "")
    data = getattr(result, "data", None)
    if data is not None and (not markdown or not html):
        if isinstance(data, dict):
            markdown = markdown or str(data.get("markdown") or "")
            html = html or str(data.get("html") or "")
        else:
            markdown = markdown or str(getattr(data, "markdown", None) or "")
            html = html or str(getattr(data, "html", None) or "")
    return markdown, html


def _classify_ex(ex: BaseException) -> str:
    msg = str(ex).lower()
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    if "401" in msg or "403" in msg or "unauthorized" in msg or "api key" in msg:
        return "firecrawl_not_configured"
    if "block" in msg or "cloudflare" in msg:
        return "blocked"
    return "fetch_failed"


def _scrape_via_cli(url: str, *, timeout_s: float) -> MatchFetchBundle:
    """
    Subprocess: `firecrawl scrape URL`.

    Tries JSON output when supported; falls back to stdout as markdown/html.
    """
    t0 = time.perf_counter()
    if not firecrawl_cli_available():
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="firecrawl",
            error="firecrawl_not_installed",
            duration_ms=0,
        )
    env = os.environ.copy()
    # Pass through key if present for CLI auth
    key = firecrawl_api_key()
    if key and "FIRECRAWL_API_KEY" not in env:
        env["FIRECRAWL_API_KEY"] = key

    candidates = [
        ["firecrawl", "scrape", url, "--format", "markdown", "--format", "html"],
        ["firecrawl", "scrape", url, "--json"],
        ["firecrawl", "scrape", url],
    ]
    last_err = "fetch_failed"
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(5.0, float(timeout_s)),
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return MatchFetchBundle(
                ok=False,
                url=url,
                method="firecrawl",
                error="timeout",
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        except FileNotFoundError:
            return MatchFetchBundle(
                ok=False,
                url=url,
                method="firecrawl",
                error="firecrawl_not_installed",
                duration_ms=int((time.perf_counter() - t0) * 1000),
            )
        except Exception as ex:  # noqa: BLE001
            last_err = _classify_ex(ex)
            continue

        out = (proc.stdout or "").strip()
        err_txt = (proc.stderr or "").strip()
        if proc.returncode != 0 and not out:
            last_err = "fetch_failed"
            if "api" in err_txt.lower() and "key" in err_txt.lower():
                last_err = "firecrawl_not_configured"
            continue

        markdown = ""
        html = ""
        if out.startswith("{") or out.startswith("["):
            try:
                payload = json.loads(out)
                if isinstance(payload, dict):
                    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
                    markdown = str(data.get("markdown") or payload.get("markdown") or "")
                    html = str(data.get("html") or payload.get("html") or "")
            except json.JSONDecodeError:
                markdown = out
        else:
            # Heuristic: treat as markdown unless looks like HTML
            if "<html" in out.lower() or "<!doctype" in out.lower():
                html = out
            else:
                markdown = out

        if not markdown and not html:
            last_err = "fetch_failed"
            continue

        duration_ms = int((time.perf_counter() - t0) * 1000)
        meta = _extract_title_meta(html, markdown)
        return MatchFetchBundle(
            ok=True,
            url=url,
            final_url=url,
            method="firecrawl",
            html=html,
            markdown=markdown,
            error=None,
            duration_ms=duration_ms,
            page_meta=meta,
            resources={
                "summary_html": html,
                "h2h_html": None,
                "xhr_json": [],
                "markdown": markdown or None,
            },
            timings_ms={"total": duration_ms},
            bytes=len((html or markdown).encode("utf-8", errors="replace")),
        )

    return MatchFetchBundle(
        ok=False,
        url=url,
        method="firecrawl",
        error=last_err,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )


def fetch_firecrawl(
    url: str,
    *,
    timeout_s: float = 45.0,
    prefer_cli: bool = False,
) -> MatchFetchBundle:
    """
    Scrape URL via Firecrawl SDK or CLI.

    Order:
      1. If prefer_cli or no SDK: try CLI
      2. Else if API key + SDK: SDK
      3. Else CLI
      4. Clear errors: firecrawl_not_installed / firecrawl_not_configured
    """
    if not url or not str(url).strip():
        return MatchFetchBundle(
            ok=False, url=url or "", method="firecrawl", error="empty_url", duration_ms=0
        )
    url = str(url).strip()
    key = firecrawl_api_key()
    sdk_ok = firecrawl_sdk_available()
    cli_ok = firecrawl_cli_available()

    if not key and not cli_ok:
        # No credentials and no CLI — honest not-configured
        if not sdk_ok:
            return MatchFetchBundle(
                ok=False,
                url=url,
                method="firecrawl",
                error="firecrawl_not_installed",
                duration_ms=0,
            )
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="firecrawl",
            error="firecrawl_not_configured",
            duration_ms=0,
        )

    if prefer_cli and cli_ok:
        bundle = _scrape_via_cli(url, timeout_s=timeout_s)
        if bundle.ok:
            return bundle
        # fall through to SDK if key present
        if key and sdk_ok:
            return _scrape_via_sdk(url, timeout_s=timeout_s, api_key=key)
        return bundle

    if key and sdk_ok:
        bundle = _scrape_via_sdk(url, timeout_s=timeout_s, api_key=key)
        if bundle.ok:
            return bundle
        if cli_ok:
            cli_bundle = _scrape_via_cli(url, timeout_s=timeout_s)
            if cli_bundle.ok:
                return cli_bundle
        return bundle

    if cli_ok:
        return _scrape_via_cli(url, timeout_s=timeout_s)

    if key and not sdk_ok:
        return MatchFetchBundle(
            ok=False,
            url=url,
            method="firecrawl",
            error="firecrawl_not_installed",
            duration_ms=0,
        )

    return MatchFetchBundle(
        ok=False,
        url=url,
        method="firecrawl",
        error="firecrawl_not_configured",
        duration_ms=0,
    )


# Backward-friendly alias matching old sources.firecrawl.shapes
def fetch_markdown(url: str, *, timeout_s: float = 45.0) -> dict[str, Any]:
    """Return {ok, markdown, html, error, method} for shim compatibility."""
    b = fetch_firecrawl(url, timeout_s=timeout_s)
    return {
        "ok": b.ok,
        "markdown": b.markdown or "",
        "html": b.html or "",
        "error": b.error,
        "method": b.method or "firecrawl",
        "duration_ms": b.duration_ms,
        "page_meta": b.page_meta,
    }
