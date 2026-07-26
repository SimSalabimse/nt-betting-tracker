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
# Defaults: SCHEME=NTDesk CONFIGURATION=Release (redesign AppRootView)
./tools/ios-desk/build_unsigned_ipa.sh

# Recovery IPA (LegacyRootView via NTDESK_USE_LEGACY_UI):
SCHEME=NTDesk-Legacy CONFIGURATION=LegacyRelease ./tools/ios-desk/build_unsigned_ipa.sh

# Or your personal script:
# /Users/simsalabim/Documents/GitHub/build_unsigned_ipa.sh \
#   "$(pwd)/tools/ios-desk/NTDesk/NTDesk.xcodeproj"
```

Output: `tools/ios-desk/build_unsigned/NTDesk.ipa` (unsigned). Env: `SCHEME`, `CONFIGURATION` (product dir = `${CONFIGURATION}-iphoneos`).

**Reminder:** after any visual change (theme tokens, App Icon, AccentColor, launch color, DesignSystem components), rebuild the unsigned IPA and re-sideload so the home-screen glyph and ink launch flash match what is in the tree. Smoke: open all four content tabs (Desk / Charts / Pending / Slip), open Settings via the gear (sheet), pull-to-refresh online, then kill mobile-view / network and confirm the stale (or empty) banner still appears and numbers do not invent equity offline.

Open in Xcode once if schemes need regeneration:

```bash
open tools/ios-desk/NTDesk/NTDesk.xcodeproj
```

---

## Schemes, Legacy UI, and git tag

| Scheme | Configuration | Root UI | Notes |
|--------|---------------|---------|--------|
| **NTDesk** (default) | Debug / Release | Redesign `AppRootView` | 4 content tabs + Settings gear/sheet; default IPA via `build_unsigned_ipa.sh` |
| **NTDesk-Legacy** | LegacyDebug / LegacyRelease | `LegacyRootView` | Compile flag `NTDESK_USE_LEGACY_UI`; five peer tabs including Settings |

Both schemes build the **same** `NTDesk` app target. Redesign `App/` + `Features/**` and renamed `Legacy/*` **always compile** in one module; the flag only selects the root in `NTDeskApp.swift`. See [`NTDesk/Legacy/README.md`](NTDesk/NTDesk/Legacy/README.md).

**Deployment target:** iOS **18.0** (app + `NTDeskTests`).

### Pre-redesign git tag

Before merging HIG redesign work, tag the tree so full rollback is one checkout:

```bash
# From repo root, on the commit that freezes pre-HIG scaffold behavior:
git tag -a ios-desk-pre-hig-redesign -m "NT Desk iOS freeze before HIG redesign"
git push origin ios-desk-pre-hig-redesign
```

If you lack tag-create permission, still document the name `ios-desk-pre-hig-redesign` and have an operator with rights create it from the agreed commit.

**Rollback options if redesign regresses:**

1. Ship a Legacy IPA: `SCHEME=NTDesk-Legacy CONFIGURATION=LegacyRelease ./tools/ios-desk/build_unsigned_ipa.sh`
2. Check out tag `ios-desk-pre-hig-redesign`.
3. Cache format is unchanged (raw desk JSON envelope).

### Unit tests

Use any available **iOS 18+** simulator (device names drift with Xcode; pick one from `xcrun simctl list devices available`):

```bash
# Build-only (no booted sim required):
xcodebuild -project tools/ios-desk/NTDesk/NTDesk.xcodeproj \
  -scheme NTDesk \
  -destination 'generic/platform=iOS Simulator' \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO \
  build-for-testing

# Run tests (substitute a real sim name from your Xcode, e.g. iPhone 17):
xcodebuild -project tools/ios-desk/NTDesk/NTDesk.xcodeproj \
  -scheme NTDesk \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO \
  test
```

`NTDeskTests` covers `PrivateHostPolicy`, connection profiles, and **server discovery** (`DiscoveryProbeLogic` host plan + `URLProtocol` health mocks: `ok==true` hit, `ok==false` miss, public IP never requested, no `/api/desk` during scan).
Minimal smoke today: `NTDeskTests` / `PrivateHostPolicy` allow/deny + normalize/boundaries, connection profiles, **AppLock default-off**. Expand in later PRs (parser, charts builders).

---
## Optional app lock (Face ID) + App Intent Sync
| Feature | Default | Notes |
|---------|---------|--------|
| **App lock** | **Off** (`app_lock_enabled` = false) | Redesign Settings → “Require Face ID / Touch ID”. UI gate only; does not place/settle. |
| **Biometrics** | System LAContext | Face ID / Touch ID / device passcode fallback. `NSFaceIDUsageDescription` in `Info.plist`. |
| **Cache file protection** | Applied when lock **on** after each successful cache write | `URLFileProtection.completeUntilFirstUserAuthentication` on the envelope file (not “encrypted because Application Support” alone). |
| **App Intent** | `Sync Desk` | Read-only `SyncService.sync()` via Shortcuts / Siri phrases. No write/place APIs. |
**Frameworks:** uses system **LocalAuthentication** + **AppIntents** (shipped with iOS 18 SDK). No third-party packages. If a future Xcode drops App Intents for the chosen deploy target, remove `Intents/SyncDeskIntent.swift` from the target and keep app lock; document the skip in this section.
**Operator notes:**
- App lock is **opt-in**. Cold launch / return from background re-prompts when enabled.

- App lock is **opt-in**. Cold launch / return from **background** re-prompts when enabled (in-flight Face ID is invalidated on lock).
- **Settings toggle is redesign-only** (`Features/Settings/SettingsView`). Legacy scheme (`NTDesk-Legacy` / `LegacySettingsView`) still honors the gate if `app_lock_enabled` was set earlier, but has no on/off control — use the redesign scheme to change the preference, or set UserDefaults key `app_lock_enabled`.
- When lock is enabled, inactive/background scenes show a solid privacy cover for app-switcher snapshots; VoiceOver cannot reach desk content under the lock gate.
- Sideload / unsigned IPA: Face ID works on device like any personal app; Simulator has limited biometrics (Features → Face ID).
- Shortcuts “Sync Desk” refreshes the configured default profile URL; it never invents equity offline. Intent is status dialog only (no desk numbers).

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

### Token tests

`NTDeskTests` exists (iOS 18+) with policy smoke tests. Hex palette parity is still primarily enforced by:

1. SoT comments in `DeskTheme.swift` / this README table
2. Manual greppability of hex constants against `desktop/theme.py`

Prefer adding token assertions (BG / ACCENT / PROFIT / LOSS integer hex) in a later PR; do not invent a CI gate that does not run on Windows runners.

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

- [ ] `NSLocalNetworkUsageDescription` in `Info.plist` explains **scanning** + confirm-only connect, LAN / Tailscale **read-only** desk access, and that nothing is sent to third parties
- [ ] On first LAN scan or fetch, system Local Network prompt appears; Allow is required for private-host discovery and base URLs
- [ ] Base URL hint in Settings mentions LAN IP or Tailscale `100.x` (not MagicDNS when ATS clarity matters); **Find PC on network** is user-initiated only

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
2. Or **Find PC on network** (Settings): user-initiated probe of the current **private /24** for `GET /api/health` with `ok == true`. Confirm before a profile is saved and `/api/desk` is fetched.
3. Allow **Local Network** when prompted.
4. Pull to refresh; auto-refresh while foregrounded.

Base URL different from cached envelope → **never show as fresh** (mismatch banner).

### Discovery vs Tailscale

| Path | Behavior |
|------|----------|
| **Home LAN (RFC1918)** | Optional **Find PC** scan of the phone’s current private subnet (cap 256 hosts, short timeouts, concurrency cap). Health-only; **confirm before connect**. |
| **Tailscale** | **No CGNAT `100.64/10` bulk scan.** Add a **manual profile** with the PC’s `100.x` IP or MagicDNS name, then Test / Sync. |
| **Cellular** | Discovery UI disabled; use saved profiles only. |

### LAN residual risk

LAN-bound mobile-view is readable by anyone on the same L2 who can reach TCP **8787**. Discovery only increases **findability** (health already exposes metadata such as `project_root`). Prefer **Tailscale ACLs** for remote access; do not expose mobile-view on hostile/guest Wi‑Fi without understanding that risk.

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
    NTDesk.xcodeproj            # schemes: NTDesk, NTDesk-Legacy
    NTDesk/
      NTDeskApp.swift           # #if NTDESK_USE_LEGACY_UI → LegacyRootView else AppRootView
      App/                      # AppRootView, DeskTab, DeskScreenChrome, openSettings
      Features/                 # Desk, Charts, Pending, Slip, Settings (default scheme)
      Assets.xcassets/          # AppIcon, AccentColor, LaunchBackground
      DesignSystem/             # DeskTheme, spacing, type, formatters, components
      Models/…
      Services/…
      Legacy/                   # renamed freeze (Legacy* types; always compiled)
    NTDeskTests/                # XCTest (PrivateHostPolicy, profiles, discovery, …)
```

## CI note

iOS targets need **macOS**. Windows runners skip this tree.

## Engine law

- Phone never mutates desk state.
- Never invent equity offline.
- Cache stores **raw** desk JSON inside an envelope (not Codable re-encode of the desk object).
