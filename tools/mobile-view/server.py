"""
Read-only mobile desk API (GET/HEAD only).

Production launcher: start.ps1 / start.sh — they pass uvicorn --host.
CLI `--host` and MOBILE_VIEW_HOST must agree; launcher is the production path.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# Allow running as `python server.py` from this directory
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from paths_util import resolve_project_root  # noqa: E402
from readers import build_desk_snapshot  # noqa: E402
from version_info import API_VERSION, SCHEMA_VERSION, SERVICE_NAME  # noqa: E402

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import HTMLResponse
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "fastapi is required for mobile-view. Install: pip install -r tools/mobile-view/requirements.txt"
    ) from e

_CACHE_CONTROL = "private, no-cache"


def resolve_bind_host(
    requested: str | None = None,
    *,
    lan: bool | None = None,
) -> str:
    """
    Pure bind resolver. Unit-tested.

    Without lan: only loopback. With lan: honor requested (default 0.0.0.0 from launcher).
    MOBILE_VIEW_HOST alone must not open non-loopback unless MOBILE_VIEW_LAN is set.
    """
    req = (
        requested
        if requested is not None
        else (os.environ.get("MOBILE_VIEW_HOST") or "127.0.0.1")
    ).strip()
    if lan is None:
        lan = os.environ.get("MOBILE_VIEW_LAN", "").strip().lower() in ("1", "true", "yes")
    loopback = {"127.0.0.1", "localhost", "::1"}
    if not req:
        req = "127.0.0.1"
    if req in loopback:
        return "127.0.0.1" if req == "localhost" else req
    if not lan:
        return "127.0.0.1"  # fail closed
    return req  # e.g. 0.0.0.0, 192.168.x.x, 100.x.y.z


def _desk_body_bytes(final_dict: dict[str, Any]) -> bytes:
    """Serialize desk once — strong ETag is SHA-256 of these exact bytes."""
    return json.dumps(
        final_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _strong_etag(body_bytes: bytes) -> str:
    """Strong ETag: quoted first 16 hex chars of SHA-256(body_bytes)."""
    return '"' + hashlib.sha256(body_bytes).hexdigest()[:16] + '"'


def _if_none_match_hits(header: str | None, etag: str) -> bool:
    """
    True if If-None-Match matches etag (or is ``*``).

    RFC 9110 §13.1.2: ``*`` matches any current representation for GET/HEAD.
    Strips weak W/ prefix for comparison leniency; compares opaque tags with quotes.
    """
    if not header:
        return False
    target = etag.strip()
    for part in header.split(","):
        tag = part.strip()
        if not tag:
            continue
        if tag == "*":
            return True
        if tag[:2].upper() == "W/":
            tag = tag[2:].lstrip()
        if tag == target:
            return True
    return False


def create_app(project_root: Path | None = None) -> FastAPI:
    root = resolve_project_root(project_root) if project_root else resolve_project_root()
    app = FastAPI(title="NT Mobile Desk", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def write_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            return Response(status_code=405, content="Method Not Allowed — view-only")
        return await call_next(request)

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "view_only": True,
            "project_root": str(root),
            # Identity + versions (see docs/PRODUCTS.md, docs/api/DESK_SCHEMA_V1.md).
            "service": SERVICE_NAME,
            "api_version": API_VERSION,
            "schema_version": SCHEMA_VERSION,
        }

    @app.get("/api/desk")
    def desk(request: Request) -> Response:
        # Build final dict (content_hash + stable generated_at from readers), serialize once.
        snap = build_desk_snapshot(root)
        body_bytes = _desk_body_bytes(snap)
        etag = _strong_etag(body_bytes)
        headers = {"ETag": etag, "Cache-Control": _CACHE_CONTROL}
        if _if_none_match_hits(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, content=b"", headers=headers)
        # Serve body_bytes only — do not re-serialize via JSONResponse (key order / ETag).
        return Response(content=body_bytes, media_type="application/json", headers=headers)

    @app.get("/")
    def index() -> HTMLResponse:
        from html_page import render_html

        snap = build_desk_snapshot(root)
        return HTMLResponse(render_html(snap))

    return app


# Module-level app for uvicorn `server:app`
_project = os.environ.get("NT_PROJECT_ROOT") or None
app = create_app(Path(_project) if _project else None)


def main() -> None:
    """
    python server.py path — uses resolve_bind_host.
    Operators normally use start.ps1 / start.sh which pass uvicorn --host directly.
    """
    import uvicorn

    lan = os.environ.get("MOBILE_VIEW_LAN", "").strip().lower() in ("1", "true", "yes")
    host = resolve_bind_host(os.environ.get("MOBILE_VIEW_HOST"), lan=lan)
    port = int(os.environ.get("MOBILE_VIEW_PORT") or "8787")
    if lan:
        print(
            "WARNING: LAN bind enabled — desk is view-only but reachable on bound interfaces.",
            file=sys.stderr,
        )
    print(f"Binding {host}:{port} (project={resolve_project_root()})", file=sys.stderr)
    # CLI --host and MOBILE_VIEW_HOST must agree; launcher is the production path.
    uvicorn.run("server:app", host=host, port=port, reload=False, app_dir=str(_HERE))


if __name__ == "__main__":
    main()
