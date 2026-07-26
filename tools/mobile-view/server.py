"""
Read-only mobile desk API (GET/HEAD only).

Production launcher: start.ps1 / start.sh — they pass uvicorn --host.
CLI `--host` and MOBILE_VIEW_HOST must agree; launcher is the production path.
"""

from __future__ import annotations

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

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import HTMLResponse, JSONResponse
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "fastapi is required for mobile-view. Install: pip install -r tools/mobile-view/requirements.txt"
    ) from e


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
            # Additive fingerprint for discovery (optional; clients key off ok / view_only).
            "service": "nt-mobile-view",
        }

    @app.get("/api/desk")
    def desk() -> JSONResponse:
        snap = build_desk_snapshot(root)
        return JSONResponse(content=snap)

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
