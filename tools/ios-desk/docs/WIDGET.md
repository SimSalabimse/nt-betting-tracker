# Home Screen widget — deferred

| Field | Value |
|-------|--------|
| **Status** | **Deferred** (docs only — no WidgetKit target in tree) |
| **PR** | PR-10 (`execute-plan/42148c0e-pr-10-home-screen-widget`) |
| **Product** | Optional glance of desk KPIs on iOS Home Screen |
| **Depends on** | App Group shared container + signed entitlements + viable sideload path |
| **Today** | App cache lives in the main app’s Application Support only |

This note records **why** a WidgetKit extension is not shipping now, the **future design sketch** when the operator is ready, and **acceptance criteria** for that future work. It is not a build plan and does **not** add an Xcode widget target.

---

## Why deferred

NT Desk is distributed as an **unsigned IPA** via `tools/ios-desk/build_unsigned_ipa.sh` and sideload (SideStore / TrollStore / operator tool of choice). That path is Gate-0 for the whole app. Home Screen widgets collide with it in three practical ways:

### 1. App Group entitlement

A widget extension is a **separate process**. It cannot read the main app’s sandbox (`Application Support/NTDesk/…`) unless both targets share data through an **App Group** container (`group.<team-or-bundle>.…`).

That requires:

- App Group capability on **both** the app target and the widget extension
- Matching `com.apple.security.application-groups` entitlements in the signed product
- A stable group identifier chosen once and kept forever (or a migration story)

Unsigned / ad-hoc / sideload re-sign flows often **strip or mismatch** entitlements. A widget that silently fails to open the group container is worse than no widget: operators would assume live KPIs while the tile is empty or stuck.

### 2. Signing identity

WidgetKit extensions must be embedded in the host app and signed consistently with it. Personal team / free provisioning, multi-identity re-sign, and “strip codesign then re-sign for sideload” workflows make multi-target products fragile:

| Concern | Pain for unsigned IPA |
|---------|------------------------|
| Two product types (app + appex) | Both must embed and sign correctly |
| Entitlements plist(s) | Re-sign tools must preserve App Group |
| Bundle ID suite | `…NTDesk` + `…NTDesk.Widget` (example) must stay aligned |
| Provisioning | App Groups need a team that actually has the capability |

The main app already builds with `CODE_SIGNING_ALLOWED=NO` for simulator smoke and produces an **unsigned** IPA for sideload. Adding an appex multiplies failure modes without improving bankroll truth.

### 3. Operator cost vs value

| Ship widget now | Cost |
|-----------------|------|
| Xcode widget extension target | Project / scheme / `build_unsigned_ipa.sh` churn |
| Shared cache path rewrite | Move or dual-write `CacheStore` into App Group |
| Sideload verification matrix | Every re-sign must prove widget still reads KPIs |
| Stale-tile UX | Timeline reload policy, empty/missing cache copy |

**Value** is a glance of equity / remaining / can-bet — already one tap into the app. Design already lists widgets as non-goal / later (`docs/IOS_DESK_VISUAL_HIG_DESIGN.md` non-goals: “widgets (may follow later)”).

**Verdict:** Defer until the operator has a **stable signing identity** (or a sideload path proven to preserve App Groups) and explicitly wants the extension.

---

## Current cache (what a widget would need)

Today’s SSOT on device:

| Piece | Location / shape |
|-------|------------------|
| **Writer** | `NTDesk/Services/CacheStore.swift` (main app only) |
| **Path** | `Application Support/NTDesk/desk_cache_envelope.json` |
| **Envelope** | `CacheEnvelope` — `envelope_version`, `cached_at`, `source_base_url`, `desk` (raw JSON object graph) |
| **Write policy** | Atomic tmp → replace; only after successful validated fetch |
| **Law** | Phone never mutates desk state; never invents equity offline |

A widget **must not** invent fields missing from the envelope. No network from the widget is required for v1 (and is discouraged for private LAN URLs).

---

## Future design sketch (when operator is ready)

### Goals

1. Small / medium Home Screen widget showing **KPIs only** from the last good cache.
2. Same numbers the Desk tab would show for those fields when offline/stale.
3. Clear **stale / empty** presentation — never fabricate bankroll math.

### Non-goals

- Write APIs, place/settle, App Intents that mutate desk
- Charts, pending lists, PLACE_THESE tables inside the widget
- Background network fetch as the primary data path (optional later only if App Group + policy allow)
- App Store packaging requirements as a process gate (still personal sideload)

### Architecture

```
┌──────────────── NTDesk (app) ─────────────────┐
│  SyncService → CacheStore.save(...)           │
│       │                                       │
│       ▼                                       │
│  App Group container                          │
│  group.… / desk_cache_envelope.json           │
│       │                                       │
└───────┼───────────────────────────────────────┘
        │ read-only
        ▼
┌── NTDeskWidget (WidgetKit extension) ─────────┐
│  TimelineProvider loads envelope              │
│  Parse KPI keys from desk raw JSON            │
│  Render small/medium views (desk night tokens)│
│  No writes · no invent · no place/settle      │
└───────────────────────────────────────────────┘
```

### Shared storage

1. Enable App Group on **app** + **widget** targets (same group id).
2. Point `CacheStore` at the **group container** (or dual-write during migration, then group-only).
3. Widget opens the same filename (`desk_cache_envelope.json`) and decodes the same envelope shape (`envelope_version` ≥ 1).
4. Optional: when app lock / file protection is on, document that the widget may be blank until first unlock after boot (align with `URLFileProtection` policy if present).

### KPI surface (v1 proposal)

Read from `desk` object only (schema v1 field names):

| Widget line | Desk JSON keys (examples) |
|-------------|---------------------------|
| Equity | `equity_nok` |
| Liquid | `liquid_nok` |
| Open / remaining | `pending_at_risk_nok`, `remaining_risk_nok` |
| Phase | `phase_id` / `phase_label` |
| Can bet | `can_bet` (+ optional `size_mode` / freeze flags if space) |
| Freshness | envelope `cached_at` → relative “Updated …” |

Formatting: reuse or share `DeskFormatters`-style NOK / relative time; palette from desk night (`#0B0D12` / `#E8A317` / profit-loss tokens) where WidgetKit materials allow.

### Timeline policy

- **Reload:** on app write to cache (WidgetKit `WidgetCenter.shared.reloadTimelines`) + periodic cheap reload (e.g. 15–60 min) that only re-reads disk.
- **Empty:** no envelope → “Open NT Desk to sync” (not zeros).
- **Partial:** missing KPI keys → show “—” for that cell; do not default to `0` equity.

### Engine / product law (unchanged)

| Do | Don’t |
|----|--------|
| Read shared envelope only | Call mobile-view write APIs |
| Show last cached KPIs | Invent equity when cache missing |
| Label stale via `cached_at` | Imply live LAN state without proof |
| Keep widget read-only | Dual-write conflicting envelope formats |

---

## Acceptance criteria (operator-ready checklist)

Implement the extension only when **all** of the following can be checked:

### Prerequisites

- [ ] Stable signing / sideload path that **preserves App Group** entitlements on both app and appex after IPA install
- [ ] Chosen App Group id documented in README + this file
- [ ] Operator accepts multi-target rebuild + re-sideload cost

### Implementation

- [ ] Widget extension target embedded in `NTDesk` product; `build_unsigned_ipa.sh` (or successor) still produces one installable IPA including the appex
- [ ] `CacheStore` persists envelope to App Group container; main app still works offline with same envelope
- [ ] Widget **reads only**; no file writes from the extension
- [ ] KPI-only UI (small + medium at minimum); desk night colors where feasible
- [ ] Empty / missing cache does **not** show invented `0` equity
- [ ] Stale presentation uses envelope `cached_at` (relative time preferred)
- [ ] App foreground sync that saves cache triggers widget timeline reload
- [ ] No change to `/api/desk` schema required; raw `desk` subtree remains SSOT

### Verification

- [ ] Simulator or device: sync online → Home Screen widget shows equity / remaining / phase consistent with Desk tab
- [ ] Kill network / stop mobile-view → widget still shows last cache (stale), not zeros
- [ ] Clear app data / fresh install → widget empty state until first successful sync
- [ ] Sideload path: re-sign + install IPA → widget still reads App Group file (not blank-only)
- [ ] Unit or fixture test: decode sample envelope (`fixtures/desk_sample_v1.json` wrapped as envelope) → KPI extractors match expected NOK values

### Explicit non-acceptance

- Shipping a widget target that only works on a fully provisioned Apple Developer team build and fails silently on the operator’s unsigned sideload path
- Network-from-widget as the only data source (bypassing cache law)
- Any write / place / settle surface on the widget

---

## Related

| Doc / path | Role |
|------------|------|
| [`../README.md`](../README.md) | Gate-0 unsigned IPA, layout, engine law |
| [`CacheStore.swift`](../NTDesk/NTDesk/Services/CacheStore.swift) | On-disk envelope today (app sandbox) |
| [`CacheEnvelope.swift`](../NTDesk/NTDesk/Models/CacheEnvelope.swift) | Envelope schema |
| [`docs/IOS_DESK_VISUAL_HIG_DESIGN.md`](../../../docs/IOS_DESK_VISUAL_HIG_DESIGN.md) | Non-goal: widgets may follow later |
| [`docs/IOS_DESK_APP_DESIGN.md`](../../../docs/IOS_DESK_APP_DESIGN.md) | Cache envelope + read-only product law |

---

## Decision log

| Date | Decision |
|------|----------|
| 2026-07-26 | **PR-10 = docs-only deferral.** No WidgetKit extension, no App Group entitlement, no `CacheStore` path change. Revisit when signing/sideload preserves App Groups. |
