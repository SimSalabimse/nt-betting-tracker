# Mobile desk view (read-only)

Personal phone / browser surface for the NT desk snapshot.

| Endpoint | Role |
|----------|------|
| `GET /api/health` | Reachability |
| `GET /api/desk` | Schema v1 JSON (+ optional `charts`) |
| `GET /` | Dark HTML desk (KPIs, simple charts, pending, PLACE_THESE) |

**No write routes.** POST/PUT/PATCH/DELETE → **405**.

## Install

```bash
pip install -r tools/mobile-view/requirements.txt
```

## Bind modes

| Mode | Host | How |
|------|------|-----|
| **LocalOnly** (default) | `127.0.0.1` | `./start.sh` or `.\start.ps1` |
| **Lan** | `0.0.0.0` or pinned IP | `--lan` / `-Lan` |
| **BindHost** | single IP | `--lan --bind-host 192.168.1.42` |

Fail-closed: `MOBILE_VIEW_HOST` alone **never** opens non-loopback without `MOBILE_VIEW_LAN=1` / `-Lan`.

### Windows

```powershell
.\tools\mobile-view\start.ps1              # loopback
.\tools\mobile-view\start.ps1 -Lan         # LAN / Tailscale
.\tools\mobile-view\start.ps1 -Lan -BindHost 192.168.1.42
```

### macOS / Linux

```bash
chmod +x tools/mobile-view/start.sh
./tools/mobile-view/start.sh
./tools/mobile-view/start.sh --lan
./tools/mobile-view/start.sh --lan --bind-host 192.168.1.42
```

### Security preference

1. **Tailscale** + `-Lan` (or `-BindHost 100.x.y.z`)  
2. **`-Lan -BindHost <LAN IPv4>`**  
3. **`-Lan` → `0.0.0.0`** (last resort)

Do **not** combine public Cloudflare tunnel with `-Lan` unless you intentionally want a wider origin.

Windows Firewall: allow inbound TCP **8787** on **Private** profile when using LAN (manual; not auto-opened).

## Charts

`/api/desk` includes additive `charts` (equity curve, daily P/L, drawdown, by-sport, overall ROI/WR). Same ledger as Book; no engine mutation.

## iOS app

See `tools/ios-desk/README.md` (SwiftUI + local JSON cache + unsigned IPA sideload).
