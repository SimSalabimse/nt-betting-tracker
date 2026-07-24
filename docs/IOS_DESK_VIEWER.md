# iOS NT Desk Viewer + LAN mobile-view

| Field | Value |
|-------|--------|
| **Status** | PC track shipped in-repo; iOS scaffold under `tools/ios-desk/` |
| **Signing** | **Unsigned IPA + operator build script** (sideload) — see `tools/ios-desk/README.md` |
| **API** | `tools/mobile-view/` — GET-only `:8787` |
| **Charts** | Additive `charts` on `/api/desk` (equity, daily P/L, drawdown, sport, overall) |

Full design: `docs/IOS_DESK_APP_DESIGN.md`.

## Daily ops

### PC (Windows)

```powershell
pip install -r tools/mobile-view/requirements.txt
.\tools\mobile-view\start.ps1 -Lan
# Prefer: .\tools\mobile-view\start.ps1 -Lan -BindHost <LAN-or-Tailscale-IP>
```

### PC (macOS)

```bash
pip install -r tools/mobile-view/requirements.txt
./tools/mobile-view/start.sh --lan
```

### Phone

| Path | URL |
|------|-----|
| Safari (same Wi‑Fi / Tailscale) | `http://<pc-ip>:8787/` |
| Native app Settings | base URL `http://<pc-ip>:8787` |

Offline: last cached `/api/desk` JSON with stale banner (native app).

## Residual risks

- LAN bind is view-only but **readable** by anyone on that L2/tailnet.
- Prefer Tailscale ACLs; avoid guest Wi‑Fi reachability.
- Do not combine public Cloudflare origin with `-Lan` casually.

## Firewall

Windows: allow inbound TCP **8787** on **Private** profile when using `-Lan` (manual).
