# Command cheatsheet

Copy-paste commands for the NT desk. Run from the **repo root** unless noted.

| Topic | Jump |
|-------|------|
| Setup | [Install](#install) |
| Mobile desk (phone / Safari) | [Mobile-view server](#mobile-view-server) |
| iPhone app | [iOS unsigned IPA](#ios-unsigned-ipa) |
| Daily betting CLI | [Engine / desk CLI](#engine--desk-cli) |
| Checks | [Smoke tests](#smoke-tests) |

Deep docs: [VISION](VISION.md) · [mobile-view](../tools/mobile-view/README.md) · [ios-desk](../tools/ios-desk/README.md) · [IOS_DESK_VIEWER](IOS_DESK_VIEWER.md)

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
curl -s http://127.0.0.1:8787/api/desk | python3 -m json.tool | head -40
```

**Security:** default is loopback. `-Lan` / `--lan` is view-only but readable on that network — prefer Tailscale or a pinned `-BindHost`.

---

## iOS unsigned IPA

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
