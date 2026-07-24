# NT Desk (iOS) — personal viewer

SwiftUI app that **reads** the PC mobile-view API and **caches** the last successful `/api/desk` JSON for offline viewing.

| Online (LAN / Tailscale) | Offline |
|--------------------------|---------|
| Health → fetch desk → save raw JSON | Show last cache + stale banner |

**Not** full LuminaNT. Desk KPIs + pending + PLACE_THESE + **simple charts** (equity, daily P/L, sport ROI).

---

## Gate-0 / signing (recorded)

| Choice | Detail |
|--------|--------|
| **Method** | **Unsigned IPA** built with the operator’s own build script |
| **Install** | Sideload (e.g. SideStore / TrollStore / your preferred tool) |
| **Not used** | App Store, TestFlight (optional later) |
| **Cadence** | Whatever your sideload tool requires — document your re-sign/reinstall habit here if needed |

This Mac has Xcode; day-to-day desk ops may still be on Windows. Build IPAs here, run `mobile-view` on the PC (or this Mac for dev).

### Build unsigned IPA

From repo root (or adapt path to your script):

```bash
# Using the in-repo wrapper (mirrors Documents/GitHub/build_unsigned_ipa.sh pattern)
./tools/ios-desk/build_unsigned_ipa.sh

# Or your personal script:
# /Users/simsalabim/Documents/GitHub/build_unsigned_ipa.sh \
#   "$(pwd)/tools/ios-desk/NTDesk/NTDesk.xcodeproj"
```

Output: `tools/ios-desk/build_unsigned/NTDesk.ipa` (unsigned).

Open in Xcode once if schemes need regeneration:

```bash
open tools/ios-desk/NTDesk/NTDesk.xcodeproj
```

---

## Settings

1. Base URL, e.g. `http://192.168.1.42:8787` or `http://100.x.y.z:8787` (Tailscale IP preferred over MagicDNS for ATS clarity).
2. Allow **Local Network** when prompted.
3. Pull to refresh; auto-refresh while foregrounded.

Base URL different from cached envelope → **never show as fresh** (mismatch banner).

---

## PC side

```powershell
# Windows desk machine
.\tools\mobile-view\start.ps1 -Lan
```

```bash
# Or Mac
./tools/mobile-view/start.sh --lan
```

---

## Project layout

```
tools/ios-desk/
  README.md
  build_unsigned_ipa.sh
  fixtures/desk_sample_v1.json
  NTDesk/
    NTDesk.xcodeproj
    NTDesk/
      NTDeskApp.swift
      Models/…
      Services/…
      Views/…
```

## CI note

iOS targets need **macOS**. Windows runners skip this tree.

## Engine law

- Phone never mutates desk state.
- Never invent equity offline.
- Cache stores **raw** desk JSON inside an envelope (not Codable re-encode of the desk object).

---

## Accessibility

NT Desk targets personal sideload quality (HIG), not App Store review.

| Area | Behavior |
|------|----------|
| **VoiceOver** | KPI `MetricCard`s and pending rows are combined elements (`label, value`). Charts announce a short summary (point counts / latest). Risk gauge, status pill, freshness banners, and empty states have explicit labels. Section titles use header traits where useful. |
| **Dynamic Type** | Semantic / system fonts via `DeskTypography`. Desk KPI grid collapses to **1 column** at accessibility sizes (`dynamicTypeSize.isAccessibilitySize`). |
| **Reduce Motion** | No decorative animations in v1; charts are static. |
| **Contrast** | Fixed dark ink theme; KPI value colors use profit / loss / accent tokens on elevated surfaces. |
| **Touch** | System tab bar + standard controls; empty-state primary button uses large control size. |

Local Network permission string (`NSLocalNetworkUsageDescription`) explains LAN / Tailscale read-only desk access and that nothing is sent to third parties. Optional `PrivacyInfo.xcprivacy` ships with tracking off and empty collected-data / API-reason arrays (hygiene for sideload; expand if Xcode warns).
