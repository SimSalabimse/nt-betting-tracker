# NT Desk (iOS) — personal viewer

SwiftUI app that **reads** the PC mobile-view API and **caches** the last successful `/api/desk` JSON for offline viewing.

| Online (LAN / Tailscale) | Offline |
|--------------------------|---------|
| Health → fetch desk → save raw JSON | Show last cache + stale banner |

**Not** full LuminaNT. Desk KPIs + pending + PLACE_THESE + **simple charts** (equity, daily P/L, sport ROI).

Visual identity (desk night theme, App Icon, HIG polish): design brief in [`docs/IOS_DESK_VISUAL_HIG_DESIGN.md`](../../docs/IOS_DESK_VISUAL_HIG_DESIGN.md); ops notes in this README.

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

**Reminder:** after any visual change (theme tokens, App Icon, AccentColor, launch color, DesignSystem components), rebuild the unsigned IPA and re-sideload so the home-screen glyph and ink launch flash match what is in the tree. Smoke: open all five tabs, pull-to-refresh online, then kill mobile-view / network and confirm the stale (or empty) banner still appears and numbers do not invent equity offline.

Open in Xcode once if schemes need regeneration:

```bash
open tools/ios-desk/NTDesk/NTDesk.xcodeproj
```

---

## Theme source of truth (desktop ↔ iOS)

| Role | Path |
|------|------|
| **Canonical palette / spacing** | [`desktop/theme.py`](../../desktop/theme.py) — “desk night” (warm amber on deep ink) |
| **iOS token map** | [`NTDesk/DesignSystem/DeskTheme.swift`](NTDesk/NTDesk/DesignSystem/DeskTheme.swift) (+ `DeskSpacing`, `DeskTypography`, `DeskFormatters`) |
| **Design brief** | [`docs/IOS_DESK_VISUAL_HIG_DESIGN.md`](../../docs/IOS_DESK_VISUAL_HIG_DESIGN.md) |

**Rule:** change colors, radii, or P/L semantics in `desktop/theme.py` first (or in lockstep). Mirror hex values in `DeskTheme.swift`. `DeskTheme` header comments point at the Python SoT.

### Token map (hex)

| Python (`theme.py`) | Swift (`DeskTheme`) | Hex / notes |
|---------------------|---------------------|-------------|
| `BG` | `bg` | `#0B0D12` page ink |
| `SURFACE` | `surface` | `#12161F` rail / header |
| `SURFACE_ELEV` | `surfaceElev` | `#171C27` cards |
| `SURFACE_2` | `surface2` | `#1C2330` nested / chips |
| `SURFACE_3` | `surface3` | `#262E3D` pressed / bars |
| `RAIL` | `rail` | `#1A2030` |
| `BORDER` / `BORDER_SOFT` / `BORDER_FOCUS` | `border` / `borderSoft` / `borderFocus` | `#2C3548` / `#232A38` / `#4A5568` |
| `TEXT` / `TEXT_MUTED` / `TEXT_DIM` | `text` / `textMuted` / `textDim` | `#F3F5F9` / `#8B95A8` / `#5C6678` |
| `ACCENT` | `accent` | `#E8A317` brand amber |
| `ACCENT_SOFT` | `accentSoft` | `#E8A317` @ alpha `0x28/255` ≈ 0.157 (not 0xAARRGGBB packed) |
| `ACCENT_DIM` | `accentDim` | `#B87E10` |
| `PROFIT` / `LOSS` / `PENDING` | `profit` / `loss` / `pending` | `#3DDC97` / `#FF6B7A` / `#F5C542` |
| `INFO` | `info` | `#7C9CFF` |
| `S1`…`S8` | `DeskSpacing.s1`…`s8` | 4, 8, 12, 16, 20, 24, 32, 40 |
| `RADIUS` / `RADIUS_SM` / `RADIUS_LG` | `radius` / `radiusSM` / `radiusLG` | 10 / 6 / 14 |
| `fmt_nok` / `fmt_pct` | `DeskFormatters.nok` / `pct` | NOK 2dp; pct is **ratio × 100**, 1dp |

**Color roles (normative):** brand → `accent` (equity, tab tint, default metric rails); profit/loss → P/L and gate pills; drawdown series uses **`loss` only**; mid/caution → `pending` (stale banners, mid risk gauge).

**Phone-only deltas:** `DeskSpacing.contentPad` = 16 (desktop `CONTENT_PAD` = 22); dark-only (`.preferredColorScheme(.dark)`). Spacing/radii live in `DeskSpacing.swift`, not `DeskTheme`.

Related assets (must stay in brand):

| Asset | Value |
|-------|--------|
| `AccentColor.colorset` | `#E8A317` (system `Color.accentColor`, chart accents) |
| `LaunchBackground.colorset` | `#0B0D12` (`UILaunchScreen` → `UIColorName`) |

### Token tests (opt-out)

There is **no** `NTDeskTests` XCTest target today. Hex parity is enforced by:

1. SoT comments in `DeskTheme.swift` / this README table
2. Manual greppability of hex constants against `desktop/theme.py`

If a test target is added later, prefer assertions on BG / ACCENT / PROFIT / LOSS integer hex values (see design doc §PR-2). Until then, do not invent a CI gate that does not exist.

---

## App Icon (Concept A) — regenerate

| Attribute | Detail |
|-----------|--------|
| **Concept** | **A (default):** deep ink field; vertical amber **3pt rail** on the left third; abstract monoline desk gauge or stylized **NT** monogram in amber at right-center |
| **Master** | **1024×1024**, sRGB, **opaque PNG (no alpha)** |
| **Path** | `NTDesk/NTDesk/Assets.xcassets/AppIcon.appiconset/AppIcon.png` |
| **Catalog** | Single-size iOS 17+ universal icon (`Contents.json` lists one 1024 entry; Xcode derives home/spotlight/settings sizes) |
| **Display name** | `NT Desk` (`CFBundleDisplayName`) |

### How to regenerate

1. Produce a new master at **1024×1024**, palette ink `#0B0D12` + amber `#E8A317` (optional mint `#3DDC97` micro-accent only). No fine text, no UI screenshots, no transparency.
2. Export **opaque** PNG (verify with `file AppIcon.png` → RGB, non-interlaced; or check that alpha is fully opaque).
3. Replace `AppIcon.appiconset/AppIcon.png` and **commit the binary**.
4. Confirm catalog wiring still holds:
   - `Assets.xcassets` is in the target **Resources** build phase (not Sources alone)
   - `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon`
5. Rebuild: `./tools/ios-desk/build_unsigned_ipa.sh`
6. Smoke: sideload IPA → home screen shows non-default glyph; launch flash is ink, not system white/black.

Operator may swap art (Concept B or custom) without a design-doc change; keep the opaque 1024 single-size contract. Optional helper (non-blocking if missing): `tools/ios-desk/scripts/generate_app_icon.sh` via `sips` for multi-size sets.

Full brief: design doc §5 App Icon.

---

## Accessibility checklist

NT Desk targets personal sideload quality (HIG), not App Store review. Use this checklist after UI or privacy-string changes.

### VoiceOver

- [ ] KPI `MetricCard`s announce as **one** element: `label, value` (optional subtitle)
- [ ] Pending rows combine match / stake / odds / status into a single label
- [ ] Charts expose a short summary (point counts / latest), not raw mark-by-mark noise
- [ ] Charts: drag/scrub with a finger shows day (or sport) detail callout + rule mark
- [ ] Risk gauge, status pill, freshness banners, and empty states have explicit labels
- [ ] Section titles use header traits where useful; decorative rails/icons are `accessibilityHidden`
- [ ] Empty-state primary control remains activatable (children `.contain`, not over-combined)

### Dynamic Type

- [ ] Prefer semantic / system fonts via `DeskTypography` (no fixed `Font.system(size:)` for body/KPI roles)
- [ ] Desk KPI grid collapses to **1 column** at accessibility sizes (`dynamicTypeSize.isAccessibilitySize`)
- [ ] KPI values keep `.minimumScaleFactor` + `.lineLimit(1)`; long phase text goes in subtitle
- [ ] Spot-check Accessibility Inspector at **AX3** and **AX5** if available

### Local Network permission

- [ ] `NSLocalNetworkUsageDescription` in `Info.plist` explains LAN / Tailscale **read-only** desk access and that nothing is sent to third parties (current string is operator-facing; keep that intent if you reword)
- [ ] On first LAN fetch, system Local Network prompt appears; Allow is required for private-host base URLs
- [ ] Base URL hint in Settings mentions LAN IP or Tailscale `100.x` (not MagicDNS when ATS clarity matters)

### Other HIG / privacy hygiene

| Area | Behavior |
|------|----------|
| **Reduce Motion** | No decorative animations in v1; charts are static |
| **Contrast** | Fixed dark ink theme; KPI values use profit / loss / accent on elevated surfaces |
| **Touch** | System tab bar + standard controls; empty-state primary uses large control size |
| **PrivacyInfo** | Optional `PrivacyInfo.xcprivacy` with tracking off and empty collected-data / API-reason arrays (sideload hygiene; expand if Xcode warns) |

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
      Assets.xcassets/          # AppIcon, AccentColor, LaunchBackground
      DesignSystem/            # DeskTheme, spacing, type, formatters, components
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
