# Command cheatsheet

Copy-paste commands for the NT desk. Run from the **repo root** unless noted.

| Topic | Jump |
|-------|------|
| Setup | [Install](#install) |
| **What’s what** | [Products map](PRODUCTS.md) · [tools/](../tools/README.md) |
| Mobile desk API | [Mobile-view server](#mobile-view-server) |
| **API-only Windows update** | [Update mobile-view only](#update-mobile-view-api-only-windows) |
| iPhone app | [iOS unsigned IPA](#ios-unsigned-ipa) |
| Daily betting CLI | [Engine / desk CLI](#engine--desk-cli) |
| Checks | [Smoke tests](#smoke-tests) |

Deep docs: [PRODUCTS](PRODUCTS.md) · [desk schema v1](api/DESK_SCHEMA_V1.md) · [mobile-view](../tools/mobile-view/README.md) · [ios-desk](../tools/ios-desk/README.md)

---

## Install

```bash
# Core Python (engine)
pip install -r requirements.txt

# Mobile desk API (FastAPI)
pip install -r tools/mobile-view/requirements.txt

# Optional Flet desktop
pip install -r requirements-desktop.txt
```

---

## Mobile-view server

**Product:** `tools/mobile-view` · **Package version:** see `tools/mobile-view/VERSION` (`api_version`) · **Wire:** `schema_version` **1**

Read-only desk for browser or the iOS app. **GET only** — no place/settle from the phone.

### macOS / Linux

```bash
# Loopback only (PC browser / CF tunnel origin)
./tools/mobile-view/start.sh

# Home Wi‑Fi / Tailscale (phone can connect)
./tools/mobile-view/start.sh --lan

# Prefer single interface
./tools/mobile-view/start.sh --lan --bind-host 192.168.1.42
./tools/mobile-view/start.sh --lan --bind-host 100.x.y.z   # Tailscale IP

# Custom port
./tools/mobile-view/start.sh --lan --port 8787
```

### Windows (PowerShell)

```powershell
.\tools\mobile-view\start.ps1
.\tools\mobile-view\start.ps1 -Lan
.\tools\mobile-view\start.ps1 -Lan -BindHost 192.168.1.42
.\tools\mobile-view\start.ps1 -Lan -Port 8787
```

### URLs

| Client | URL |
|--------|-----|
| Same machine | `http://127.0.0.1:8787/` |
| Phone (LAN) | `http://<PC-LAN-IP>:8787/` |
| Phone (Tailscale) | `http://<PC-100.x-IP>:8787/` |
| Health | `…/api/health` |
| Desk JSON | `…/api/desk` |

```bash
curl -s http://127.0.0.1:8787/api/health | python3 -m json.tool
# expect: ok, service=nt-mobile-view, api_version, schema_version=1

curl -s http://127.0.0.1:8787/api/desk | python3 -m json.tool | head -40
```

**Security:** default is loopback. `-Lan` / `--lan` is view-only but readable on that network — prefer Tailscale or a pinned `-BindHost`.

---

## Update mobile-view API only (Windows)

Use this when the **phone needs a new field** (kickoff, secure, charts) but you **must not** merge the whole monorepo stack onto the live ops PC.

```powershell
cd C:\path\to\nt-betting-tracker   # your Windows clone

# 1) Fetch metadata only (no merge)
git fetch --tags origin

# 2) Replace ONLY the API product folder (path checkout — no full pull)
# Prefer a release tag when it exists:
git checkout mobile-view-v1.1.0 -- tools/mobile-view/

# Or from main (still path-only):
# git checkout origin/main -- tools/mobile-view/

# 3) Optional: better future notes (kickoff prefix) — engine file, still path-only
# git checkout mobile-view-v1.1.0 -- nt/recommend.py

# 4) Restart mobile-view (stop the old uvicorn/window first)
.\tools\mobile-view\start.ps1 -Lan

# 5) Confirm package version
curl -s http://127.0.0.1:8787/api/health
# "api_version":"1.1.0"
```

| Do | Don’t |
|----|--------|
| Path-checkout `tools/mobile-view/` | Blind `git pull` of experimental branches |
| Restart API after file replace | Expect iOS to invent kickoff without API |
| Tag releases `mobile-view-vX.Y.Z` | Mix engine rewrites with API-only deploys |

Details: [PRODUCTS.md](PRODUCTS.md) · [mobile-view README](../tools/mobile-view/README.md).

---

## iOS unsigned IPA

**Product:** `tools/ios-desk` · **App version:** `tools/ios-desk/VERSION` (e.g. **1.1.0**)

Build on a Mac with Xcode; sideload with your usual tool.

```bash
# Open project
open tools/ios-desk/NTDesk/NTDesk.xcodeproj

# Unsigned IPA (no code signing)
./tools/ios-desk/build_unsigned_ipa.sh
# → tools/ios-desk/build_unsigned/NTDesk.ipa
```

**App Settings → base URL** (examples):

```text
http://192.168.1.42:8787
http://100.x.y.z:8787
```

**Simulator build (dev):**

```bash
xcodebuild \
  -project tools/ios-desk/NTDesk/NTDesk.xcodeproj \
  -scheme NTDesk \
  -destination 'generic/platform=iOS Simulator' \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO \
  build
```

Charts: drag with a finger to scrub day (or sport) details.

**Version tags (optional):** `ios-desk-v1.1.0` — see [PRODUCTS.md](PRODUCTS.md).

---

## Engine / desk CLI

```bash
# Dry-run daily path (no ledger write)
python scripts/dry_run_daily_path.py

# Board + light research + recommend (dry-run)
python run_nt.py research board --odds inbox/odds_YYYY-MM-DD.txt
python run_nt.py research light --odds inbox/odds_YYYY-MM-DD.txt
python run_nt.py recommend --odds inbox/odds_YYYY-MM-DD.txt --dry-run

# Settle (after results file in inbox/)
python run_nt.py settle --results inbox/results.txt

# Optional Flet desktop
python run_desktop.py
```

Grok / skill launchers (Windows examples):

```powershell
.\scripts\skill_list.ps1
.\scripts\skill_invoke.ps1 daily-run
.\scripts\skill_smoke.ps1
```

---

## Smoke tests

```bash
# Mobile-view unit tests
python -m pytest tests/test_mobile_view.py -q

# Broader suite (may take a while)
python -m pytest tests/ -q --tb=no
```

---

## Quick day: phone viewer

1. On the **PC** (or Mac hosting the ledger):

```bash
pip install -r tools/mobile-view/requirements.txt
./tools/mobile-view/start.sh --lan
# Windows: .\tools\mobile-view\start.ps1 -Lan
```

2. Note the PC LAN or Tailscale IP.

3. **Safari:** open `http://<ip>:8787/`  
   **or iOS app:** Settings → that base URL → pull to refresh.

4. Rebuild IPA only after app code/icon changes:

```bash
./tools/ios-desk/build_unsigned_ipa.sh
```
