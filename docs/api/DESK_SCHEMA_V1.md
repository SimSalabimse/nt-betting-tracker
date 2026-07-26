# Desk API schema v1 (`/api/desk`)

**Owner product:** `tools/mobile-view`  
**Consumers:** iOS Desk (`tools/ios-desk`), browser HTML at `GET /`  
**Mutations:** none — view-only

## Versions

| Field | Location | Current |
|-------|----------|---------|
| `schema_version` | desk JSON | **1** (breaking changes only) |
| `api_version` | desk JSON + `/api/health` | See `tools/mobile-view/VERSION` (e.g. **1.2.0**) |

**Compatibility rule:** keep `schema_version == 1` while only **adding** optional keys. iOS must tolerate missing keys (decode defaults / optionals).

---

## Endpoints

| Method | Path | Body |
|--------|------|------|
| `GET` | `/api/health` | Reachability + versions |
| `GET` | `/api/desk` | Full desk snapshot (this schema); strong `ETag` / conditional `304` (api ≥ 1.2.0) |
| `GET` | `/` | HTML desk (same snapshot) |
| `POST`/`PUT`/… | any | **405** |

### Conditional GET headers (`/api/desk`, api ≥ 1.2.0)

| Item | Value |
|------|--------|
| `ETag` (response) | Strong: `"<first 16 hex of SHA-256(body_bytes)>"` where `body_bytes` is the exact JSON response body |
| `Cache-Control` | `private, no-cache` on 200 and 304 |
| `If-None-Match` (request) | Previous `ETag`; weak `W/"…"` accepted for comparison |
| `304` | Empty body; same `ETag` + `Cache-Control` when validator matches |

Body serialization for ETag: `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")` — served as those bytes (no second serialize).

### `/api/health` (minimum)

```json
{
  "ok": true,
  "view_only": true,
  "service": "nt-mobile-view",
  "api_version": "1.2.0",
  "schema_version": 1,
  "project_root": "/path/to/nt-betting-tracker"
}
```

### `/api/desk` — top-level keys (v1 + additive)

| Key | Type | Notes |
|-----|------|--------|
| `schema_version` | int | Always `1` for this document |
| `api_version` | string | Package version of mobile-view |
| `generated_at` | string | ISO UTC — **last content change** for this desk body (may be older than wall clock when inputs are unchanged). Clients may treat equality of this field (or of `content_hash`) as “payload unchanged.” **Not** “time of HTTP response.” HTML “Generated …” may look stale while idle — acceptable. |
| `content_hash` | string | Additive (api ≥ 1.2.0). First 16 hex chars of SHA-256 over **canonical JSON** of the desk object **excluding** `generated_at` and `content_hash` (`sort_keys=True`, compact separators, `ensure_ascii=False`). Canonical identity for debugging and client skip. |
| `view_only` | bool | Always true |
| `stale` / `warnings` | bool / list | Server-side hints |
| `equity_nok`, `liquid_nok`, `pending_at_risk_nok`, … | number | Bankroll KPIs |
| `phase_id`, `phase_label` | string | Phase |
| `can_bet`, `size_mode`, `stopped`, `freeze` | bool/string | Risk gate |
| `remaining_risk_nok`, `daily_risk_cap_nok`, `today_realized_pl_nok` | number | Daily risk |
| `secure_nok`, `working_equity_nok`, `riskable_liquid_nok` | number | Secure Variant A (optional) |
| `secure_variant`, `secure_ref_hwm_nok` | string/number | Secure A metadata |
| `risk_reasons` | string[] | Human reasons |
| `pending_bets` | object[] | Open book |
| `place_these` | object | PLACE_THESE excerpt + `rows_preview` |
| `status_excerpt` | string | STATUS.md clip |
| `charts` | object | Equity / daily / drawdown / by_sport / overall |

### `pending_bets[]` (additive kickoff)

| Key | Type | Notes |
|-----|------|--------|
| `bet_id`, `date`, `match`, `selection` | string | |
| `decimal_odds`, `stake_nok` | number | |
| `result`, `sport`, `updated_at` | string | |
| **`kickoff`** | string \| null | `YYYY-MM-DD HH:MM` Europe/Oslo wall when known |

Resolution order on the server: notes `kickoff=` → ledger peers → inbox/outbox odds dumps (`Kick-off:`).

### `charts` (additive)

| Key | Notes |
|-----|--------|
| `equity_curve`, `daily`, `drawdown` | Time series |
| `by_sport`, `overall`, `max_drawdown` | Aggregates |
| `range_label`, `range_key` | Labels |

Full era series preferred; clients may filter (1w / 1m / all).

---

## Smoke checks

```bash
curl -s http://127.0.0.1:8787/api/health
# expect ok, service, api_version, schema_version

curl -s http://127.0.0.1:8787/api/desk | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('api_version'), d.get('schema_version')); print([(b.get('match'), b.get('kickoff')) for b in d.get('pending_bets') or []])"
```
