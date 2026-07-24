#!/usr/bin/env bash
# NT mobile-view launcher (macOS / Linux). Same bind rules as start.ps1.
# Default: 127.0.0.1. Opt-in: --lan [--bind-host IP]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

LAN=0
BIND_HOST=""
PORT=8787
PROJECT_ROOT="${NT_PROJECT_ROOT:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lan|-Lan) LAN=1; shift ;;
    --bind-host|-BindHost) BIND_HOST="${2:-}"; shift 2 ;;
    --port|-Port) PORT="${2:-8787}"; shift 2 ;;
    --project-root) PROJECT_ROOT="${2:-}"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -n "$PROJECT_ROOT" ]]; then
  export NT_PROJECT_ROOT="$PROJECT_ROOT"
fi

# Normative bind (must match server.resolve_bind_host)
if [[ "$LAN" -eq 1 ]]; then
  export MOBILE_VIEW_LAN=1
  BIND_HOST="${BIND_HOST:-0.0.0.0}"
  echo "WARNING: LAN bind enabled ($BIND_HOST). View-only desk is reachable on bound interfaces." >&2
else
  unset MOBILE_VIEW_LAN || true
  if [[ -n "$BIND_HOST" && "$BIND_HOST" != "127.0.0.1" && "$BIND_HOST" != "localhost" && "$BIND_HOST" != "::1" ]]; then
    echo "ERROR: --bind-host requires --lan" >&2
    exit 1
  fi
  BIND_HOST="127.0.0.1"
fi

export MOBILE_VIEW_HOST="$BIND_HOST"
export MOBILE_VIEW_PORT="$PORT"

# CLI --host and MOBILE_VIEW_HOST must agree; launcher is the production path.
exec python3 -m uvicorn server:app --host "$BIND_HOST" --port "$PORT" --log-level info
