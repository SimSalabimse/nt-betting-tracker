# Legacy UI freeze

Pre–HIG-redesign UI snapshot, kept **always compiled** in the `NTDesk` target with **renamed types** so it does not collide with scaffold / redesign screens.

## Why rename?

Swift does not allow two `struct DeskView` (etc.) in one module. `#if` at the app root does **not** exclude type definitions. The chosen strategy:

| Scaffold (default) | Legacy (always compiled) |
|--------------------|--------------------------|
| `RootView` | `LegacyRootView` |
| `DeskView` | `LegacyDeskView` |
| `ChartsView` | `LegacyChartsView` |
| `PendingListView` | `LegacyPendingListView` |
| `SlipView` | `LegacySlipView` |
| `SettingsView` | `LegacySettingsView` |
| private helpers | `Legacy*` prefix as needed |

Shared: `Models/`, `Services/`, `DesignSystem/`, and the `DeskTab` enum (defined in scaffold `Views/RootView.swift`).

## Compile flag

| Scheme | Root UI | Flag |
|--------|---------|------|
| **NTDesk** (default) | Scaffold `RootView` | *(none)* |
| **NTDesk-Legacy** | `LegacyRootView` | `NTDESK_USE_LEGACY_UI` |

`NTDeskApp.swift` switches only the root:

```swift
#if NTDESK_USE_LEGACY_UI
LegacyRootView()
#else
RootView()
#endif
```

## Freeze policy

- **Legacy is freeze-on-copy:** only security/build fixes and renames required for compile.
- New features go to the redesign tree (PR-1b+), not here.
- Services API must stay Legacy-compatible (see design doc §1 Shared Services contract).

## Recovery layers

1. **Git tag** `ios-desk-pre-hig-redesign` — full tree rollback (see `tools/ios-desk/README.md`).
2. **This folder** — side-by-side source comparison.
3. **NTDesk-Legacy scheme** — ship a Legacy IPA if redesign fails smoke.

## Do not

- Introduce `AppRootView` / `Features/` here (PR-1b).
- Change Legacy behavior except compile/security fixes.
- Delete scaffold `Views/*` until redesign fully replaces them.
