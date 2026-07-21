from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "LuminaNT-Settle/1.1 (+multi-sport research tool)"
DEFAULT_TIMEOUT = 5.0


def http_get_json(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> Any | None:
    """GET JSON; returns None on any failure (never raises to callers)."""
    hdrs = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
    }
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return None
            return json.loads(raw)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        ValueError,
        OSError,
    ):
        return None


def http_get_text(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json,*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def qs(params: dict[str, Any]) -> str:
    return urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
