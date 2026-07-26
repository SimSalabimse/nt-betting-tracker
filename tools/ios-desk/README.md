# ios-desk — NT Desk (iOS)

| | |
|--|--|
| **What** | SwiftUI **viewer** for the PC desk (LAN / Tailscale) |
| **What it is not** | Not the engine. Not place/settle. Not full LuminaNT |
| **Version** | **`VERSION` = 1.1.0** → Xcode `MARKETING_VERSION` / Settings “Version” |
| **Build** | `CURRENT_PROJECT_VERSION` / `CFBundleVersion` (build **2** for 1.1.0) |
| **Needs API** | Prefer **mobile-view `api_version` ≥ 1.1.0** for kickoff + Secure A |
| **Changelog** | [`CHANGELOG.md`](CHANGELOG.md) |
| **Product map** | [`docs/PRODUCTS.md`](../../docs/PRODUCTS.md) |
| **Schema** | [`docs/api/DESK_SCHEMA_V1.md`](../../docs/api/DESK_SCHEMA_V1.md) |

```
iPhone  ──GET /api/desk──►  PC mobile-view  ──read files──►  data/
        ◄── JSON cache ──
```

## Gate-0 install

| Choice | Detail |
|--------|--------|
| **Method** | Unsigned IPA |
| **Build** | Mac + Xcode |
| **Install** | Sideload (SideStore / TrollStore / your tool) |

```bash
# From monorepo root
./tools/ios-desk/build_unsigned_ipa.sh
# → tools/ios-desk/build_unsigned/NTDesk.ipa

# Legacy UI recovery
SCHEME=NTDesk-Legacy CONFIGURATION=LegacyRelease ./tools/ios-desk/build_unsigned_ipa.sh
```

Copy IPA to `Documents/Dimensional Storage/` (or your sideload drop) as you prefer.

**Settings → base URL** examples: `http://192.168.x.x:8787` or Tailscale `http://100.x.y.z:8787`.

## Version bump checklist (app release)

1. Edit [`VERSION`](VERSION) (e.g. `1.2.0`)
2. Match Xcode: `MARKETING_VERSION` + `CURRENT_PROJECT_VERSION` in `NTDesk.xcodeproj` and `Info.plist`
3. Entry in [`CHANGELOG.md`](CHANGELOG.md)
4. Build IPA, sideload, smoke tabs
5. Optional git tag: `ios-desk-v1.2.0` (see [`docs/PRODUCTS.md`](../../docs/PRODUCTS.md))

## Layout

| Path | Role |
|------|------|
| `NTDesk/` | Xcode project + sources |
| `build_unsigned_ipa.sh` | Unsigned Release IPA |
| `docs/` | iOS-specific notes (e.g. FUTURE_IDEAS) |
| `fixtures/` | Sample JSON if present |

Design history: [`docs/IOS_DESK_APP_DESIGN.md`](../../docs/IOS_DESK_APP_DESIGN.md), [`docs/IOS_DESK_VISUAL_HIG_DESIGN.md`](../../docs/IOS_DESK_VISUAL_HIG_DESIGN.md).

## Schemes

| Scheme | Root UI |
|--------|---------|
| **NTDesk** (default) | Redesign `AppRootView` |
| **NTDesk-Legacy** | `LegacyRootView` (`NTDESK_USE_LEGACY_UI`) |

Deployment target: **iOS 18.0**.
