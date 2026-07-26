# Legacy UI freeze

Pre–HIG-redesign UI snapshot, kept **always compiled** in the `NTDesk` target with **renamed types** so it does not collide with scaffold / redesign screens.

## Why rename?

Swift does not allow two `struct DeskView` (etc.) in one module. `#if` at the app root does **not** exclude type definitions. The chosen strategy:

| Scaffold / redesign (default) | Legacy (always compiled) |
|-------------------------------|--------------------------|
| `AppRootView` | `LegacyRootView` |
| `DeskView` | `LegacyDeskView` |
| `ChartsView` | `LegacyChartsView` |
| `PendingListView` | `LegacyPendingListView` |
| `SlipView` | `LegacySlipView` |
| `SettingsView` | `LegacySettingsView` |
| `DeskTab` (4 content tabs) | `LegacyDeskTab` (5 tabs incl. Settings) |
| private helpers | `Legacy*` prefix as needed |

## What is frozen vs shared

| Surface | Frozen? | Notes |
|---------|---------|--------|
| `Legacy/*.swift` view types | **Yes** (freeze-on-copy) | Only security/build fixes + renames |
| `Models/`, `Services/` | Shared live | Must stay Legacy-compatible (facade contract) |
| `DesignSystem/*` tokens/components | **Shared live, not frozen** | Theme/spacing changes restyle Legacy too |
| `DeskTab` | Redesign only | Four content tabs; Settings is gear/sheet |
| `LegacyDeskTab` | Legacy only | Five tabs including Settings peer |

**Implication:** a redesign IA or token change can affect Legacy compile/runtime without editing `Legacy/*`. Full visual/behavior tree rollback remains the **git tag** path (`ios-desk-pre-hig-redesign`).

## Compile flag

| Scheme | Root UI | Flag |
|--------|---------|------|
| **NTDesk** (default) | Redesign `AppRootView` | *(none)* |
| **NTDesk-Legacy** | `LegacyRootView` | `NTDESK_USE_LEGACY_UI` |

`NTDeskApp.swift` switches only the root:

```swift
#if NTDESK_USE_LEGACY_UI
LegacyRootView()
#else
AppRootView()
#endif
```

## Freeze policy

- **Legacy is freeze-on-copy:** only security/build fixes and renames required for compile.
- New features go to the redesign tree (`App/`, `Features/`), not here.
- Services API must stay Legacy-compatible (see design doc §1 Shared Services contract).

## Recovery layers

1. **Git tag** `ios-desk-pre-hig-redesign` — full tree rollback (see `tools/ios-desk/README.md`).
2. **This folder** — side-by-side source comparison of view types.
3. **NTDesk-Legacy scheme** — ship a Legacy IPA if redesign fails smoke:

```bash
SCHEME=NTDesk-Legacy CONFIGURATION=LegacyRelease ./tools/ios-desk/build_unsigned_ipa.sh
```

## Do not

- Introduce redesign-only features here.
- Change Legacy behavior except compile/security fixes.
- Assume DesignSystem hex/spacing is pinned for Legacy — it is not; tokens are shared.
