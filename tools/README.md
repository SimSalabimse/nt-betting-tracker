# `tools/` — satellite products

Not the betting engine. These sit beside the PC ledger and **read** it (or talk to a reader).

| Directory | Product | Version | Docs |
|-----------|---------|---------|------|
| [`mobile-view/`](mobile-view/) | Read-only desk **HTTP API** for phone/browser | [`VERSION`](mobile-view/VERSION) | [README](mobile-view/README.md) · [CHANGELOG](mobile-view/CHANGELOG.md) |
| [`ios-desk/`](ios-desk/) | **iOS** viewer app (SwiftUI) | [`VERSION`](ios-desk/VERSION) | [README](ios-desk/README.md) · [CHANGELOG](ios-desk/CHANGELOG.md) |

**Map of everything in the monorepo:** [`docs/PRODUCTS.md`](../docs/PRODUCTS.md)  
**Wire contract:** [`docs/api/DESK_SCHEMA_V1.md`](../docs/api/DESK_SCHEMA_V1.md)  
**Copy-paste commands:** [`docs/COMMANDS.md`](../docs/COMMANDS.md)

```
PC (engine + data) ──► mobile-view :8787 ──► iOS Desk
         ▲                    │
         └── desktop (Flet) ──┘  (desktop does not need mobile-view)
```
