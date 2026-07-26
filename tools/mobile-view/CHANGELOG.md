# mobile-view changelog

Package version = `VERSION` file = `api_version` in `/api/health` and `/api/desk`.  
Wire shape = `schema_version` (still **1** unless a breaking change).

Format: [Keep a Changelog](https://keepachangelog.com/)-style.

## [1.2.0] — 2026-07-26

### Added
- **`content_hash`** on `/api/desk` — first 16 hex chars of SHA-256 over canonical JSON of the
  desk object **excluding** `generated_at` and `content_hash` (stable content identity)
- Durable **`generated_at`** = last **content** change time (not HTTP response time), persisted at
  package-local `tools/mobile-view/.cache/desk_identity.json` (survives process restart)
- In-process full-snapshot memory cache keyed on explicit per-file fingerprints
  (core state files + odds candidate path/mtime/size; no odds parse cache yet)

### Changed
- `generated_at` no longer stamped on every request when the ledger is idle — clients can skip
  unchanged payloads via string equality (including post-restart for iOS 1.1.4)

### Notes
- `schema_version` remains **1** (additive only)
- GET may write **only** `.cache/desk_identity.json` under this package; never engine SSOT
- ETag/304 deferred to a follow-up PR

## [1.1.3] — 2026-07-26


### Fixed
- Equity curve: only **terminal** P/L (never ConfirmedPlaced/Pending); baseline from bankroll
  so a refund-only match day stays at **baseline (500)** like Lumina cumulative equity

## [1.1.2] — 2026-07-26

### Fixed
- Equity curve matches **Lumina Book** again: match `date` buckets + same non-Pending filter
  (25th refund → equity 500; 26th bets accumulate). Reverted settlement-day remap that diverged from PC.

## [1.1.1] — 2026-07-26

### Fixed
- Equity / daily / drawdown series use **settlement day** (Europe/Oslo `updated_at`), not match kickoff `date` — stops wrong day buckets (e.g. activity on the 25th)
- Carry-forward empty calendar days + baseline anchor so equity trend is not a sparse flat segment

## [1.1.0] — 2026-07-26

### Added
- `api_version` / `service` / `schema_version` on `/api/health`
- `api_version` on `/api/desk` (alongside `schema_version: 1`)
- Pending `kickoff` (`YYYY-MM-DD HH:MM`) from notes, ledger peers, inbox/outbox odds dumps
- Secure Variant A fields: `secure_nok`, `working_equity_nok`, `riskable_liquid_nok`, `secure_variant`, `secure_ref_hwm_nok`
- Object-shaped `place_these.rows_preview` (iOS-tolerant)
- Charts block (equity / daily / drawdown / by_sport / overall) — full era

### Changed
- Pending sort prefers soonest kickoff when known
- Docs: product map + schema contract

## [1.0.0] — earlier

### Added
- Read-only FastAPI desk: `/api/health`, `/api/desk`, HTML `/`
- Fail-closed bind (loopback default; `-Lan` opt-in)
- Basic pending + PLACE_THESE excerpt + charts scaffold
