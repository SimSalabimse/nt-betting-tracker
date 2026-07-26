# mobile-view — read-only desk API

| | |
|--|--|
| **What** | HTTP service that **reads** PC ledger files and serves a desk snapshot |
| **What it is not** | Not the betting engine. Not the Flet desktop. No place/settle |
| **Version** | **`api_version` = contents of [`VERSION`](VERSION)** (now **1.2.0**) |
| **Wire shape** | **`schema_version` = 1** — [`docs/api/DESK_SCHEMA_V1.md`](../../docs/api/DESK_SCHEMA_V1.md) |
| **Changelog** | [`CHANGELOG.md`](CHANGELOG.md) |
| **Product map** | [`docs/PRODUCTS.md`](../../docs/PRODUCTS.md) |

```
Windows PC data/  ──read──►  mobile-view :8787  ──JSON──►  iOS Desk / browser
```

**Reads-only exception:** mobile-view may write **only** `.cache/desk_identity.json` under this
package (durable `content_hash` → `generated_at` map so content identity survives restarts).
It **never** mutates engine files under `data/`, `inbox/`, or `outbox/`. The `.cache/` directory
is gitignored. Run with a **single uvicorn worker** (`reload=False`); identity/cache are process-local.

## Endpoints

| Endpoint | Role |
|----------|------|
| `GET /api/health` | `ok`, `service`, **`api_version`**, **`schema_version`**, `project_root` |
| `GET /api/desk` | Full snapshot (`schema_version` + `api_version` + stable `generated_at` + `content_hash` + KPIs + …) |
| `GET /` | Dark HTML desk |
| writes | **405** (except the package-local identity cache above) |

## Install / run

```bash
pip install -r tools/mobile-view/requirements.txt
```

### Windows (production path)

```powershell
.\tools\mobile-view\start.ps1              # loopback only
.\tools\mobile-view\start.ps1 -Lan         # phone on LAN / Tailscale
.\tools\mobile-view\start.ps1 -Lan -BindHost 192.168.1.42
```

### macOS / Linux

```bash
./tools/mobile-view/start.sh --lan --bind-host 192.168.1.42
```

**Security:** default is loopback. Prefer Tailscale or a single `-BindHost` over `0.0.0.0`.

## Update **only** this API on Windows (no full pull)

After `api_version` / tag is on GitHub:

```powershell
cd path\to\nt-betting-tracker
git fetch --tags origin

# Option A — from a release tag (preferred)
git checkout mobile-view-v1.2.0 -- tools/mobile-view/

# Option B — from main (paths only)
git checkout origin/main -- tools/mobile-view/

# Restart the server (stop old process first)
.\tools\mobile-view\start.ps1 -Lan
```

Verify:

```powershell
curl -s http://127.0.0.1:8787/api/health
# expect "api_version":"1.2.0"  "schema_version":1  "service":"nt-mobile-view"
```

Full cheat sheet: [`docs/COMMANDS.md`](../../docs/COMMANDS.md#update-mobile-view-api-only-windows).

## Files in this folder

| File | Role |
|------|------|
| `VERSION` | Package semver → `api_version` |
| `version_info.py` | Loads VERSION + constants |
| `server.py` | FastAPI routes + bind |
| `readers.py` | Disk → desk JSON (no `nt.*` imports) |
| `html_page.py` | Browser desk |
| `start.ps1` / `start.sh` | Launchers |
| `CHANGELOG.md` | Human history |

## iOS consumer

[`tools/ios-desk/`](../ios-desk/) — rebuild IPA separately when the app changes; only restart mobile-view when the API changes.
