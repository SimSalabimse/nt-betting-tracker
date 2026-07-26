# NT products map

This monorepo holds **four products**. They share a machine and a ledger; they do **not** share write paths from the phone.

```
┌─────────────────────────────────────────────────────────────────┐
│  nt-betting-tracker (monorepo)                                  │
│                                                                 │
│  ┌──────────────────┐   writes    ┌──────────────────────────┐  │
│  │  ENGINE          │────────────▶│  data/  inbox/  outbox/  │  │
│  │  nt/ + run_nt.py │             │  (source of truth on PC) │  │
│  └────────┬─────────┘             └────────────▲─────────────┘  │
│           │ runs engines                       │ reads only     │
│  ┌────────▼─────────┐             ┌────────────┴─────────────┐  │
│  │  DESKTOP         │             │  MOBILE-VIEW API         │  │
│  │  desktop/ (Flet) │             │  tools/mobile-view/      │  │
│  └──────────────────┘             │  GET :8787 /api/desk     │  │
│                                   └────────────┬─────────────┘  │
│                                                │ HTTP JSON      │
│                                   ┌────────────▼─────────────┐  │
│                                   │  iOS DESK APP            │  │
│                                   │  tools/ios-desk/         │  │
│                                   │  GET-only + local cache  │  │
│                                   └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

| Product | Path | Runs on | Mutates bankroll? | Version file |
|---------|------|---------|-------------------|--------------|
| **Engine** | `nt/`, `run_nt.py`, `config.yaml` | Windows PC (or any ops machine) | **Yes** (CLI / desktop) | Engine releases via git tags on the monorepo |
| **Desktop** | `desktop/` | Windows PC | **Yes** (calls engine) | Same as engine |
| **Mobile-view API** | `tools/mobile-view/` | **Same PC as data** | **No** (GET-only; may write only package-local `.cache/desk_identity.json`) | [`tools/mobile-view/VERSION`](../tools/mobile-view/VERSION) → `api_version` |
| **iOS Desk** | `tools/ios-desk/` | iPhone (sideload) | **No** | [`tools/ios-desk/VERSION`](../tools/ios-desk/VERSION) → app marketing version |

**Law:** PC is source of truth. Phone never place/settle. See root [`AGENTS.md`](../AGENTS.md).

**Mobile-view write exception:** mobile-view may write **only** `tools/mobile-view/.cache/desk_identity.json` (content identity for stable `generated_at`); it never mutates engine files under `data/`, `inbox/`, or `outbox/`.

---

## Two version numbers (do not confuse them)

| Name | Where | Meaning | Bump when |
|------|--------|---------|-----------|
| **`schema_version`** | Every `/api/desk` body | Wire **shape** contract (currently **1**). Additive keys only. | Breaking remove/rename of required fields |
| **`api_version`** | `/api/health`, `/api/desk` (`api_version`) | **mobile-view package** release (`MAJOR.MINOR.PATCH`) | Any API feature/fix you care about on Windows |
| **App version** | iOS Settings “Version”, IPA | **iOS product** release | Features/UI the phone ships |

iOS should prefer features by **presence of keys** (tolerant decode). Optionally show `api_version` from health for support.

Contract detail: [`docs/api/DESK_SCHEMA_V1.md`](api/DESK_SCHEMA_V1.md).

---

## Who updates what (Windows vs Mac)

| You changed… | Update on… | How (safe) |
|--------------|------------|------------|
| Engine / desktop / `data` math | **Windows PC** | Normal engine workflow; **do not** need iOS rebuild |
| Kickoff, secure fields, charts payload, `/api/*` | **Windows PC** `tools/mobile-view/` only | Path-only checkout — [COMMANDS → Update API only](COMMANDS.md#update-mobile-view-api-only-windows) |
| Swift UI, charts chrome, pending UX | **Mac** → IPA | `./tools/ios-desk/build_unsigned_ipa.sh` → sideload |
| Both phone + API for a new field | **Both**: bump `api_version`, deploy mobile-view, then ship IPA that reads the field | |

**Avoid** full `git pull` of experimental stacks on the live Windows ops tree. Prefer `main` (or a `release/mobile-view-*` tag) and **path checkout** of `tools/mobile-view/`.

---

## Release tags (git)

Use annotated tags so Windows and Mac can pin:

| Tag pattern | Points at | Example |
|-------------|-----------|---------|
| `mobile-view-vX.Y.Z` | Commit that ships that API package | `mobile-view-v1.1.0` |
| `ios-desk-vX.Y.Z` | Commit that ships that IPA tree | `ios-desk-v1.1.0` |

Create after the VERSION files match:

```bash
# From monorepo root, on the commit you want to freeze:
git tag -a mobile-view-v1.1.0 -m "mobile-view api_version 1.1.0 (kickoff, secure_*, charts)"
git tag -a ios-desk-v1.1.0 -m "NT Desk iOS 1.1.0"
git push origin mobile-view-v1.1.0 ios-desk-v1.1.0
```

Windows path-only from a tag:

```powershell
git fetch --tags origin
git checkout mobile-view-v1.1.0 -- tools/mobile-view/
```

---

## Quick links

| Product | README | Changelog | Run |
|---------|--------|-----------|-----|
| Mobile-view | [tools/mobile-view/README.md](../tools/mobile-view/README.md) | [CHANGELOG](../tools/mobile-view/CHANGELOG.md) | `.\tools\mobile-view\start.ps1 -Lan` |
| iOS Desk | [tools/ios-desk/README.md](../tools/ios-desk/README.md) | [CHANGELOG](../tools/ios-desk/CHANGELOG.md) | Build IPA script |
| Commands | [COMMANDS.md](COMMANDS.md) | — | Copy-paste |
| Schema | [api/DESK_SCHEMA_V1.md](api/DESK_SCHEMA_V1.md) | — | Contract |
