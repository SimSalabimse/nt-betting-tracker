# LuminaNT / Desktop GUI Integration (v5)

The desktop app (`desktop/`, Flet) and any companion **LuminaNT / NT Lumina / BetLumina** build must remain a **view + invoker** over the same files and engines. Engines in `nt/` stay law.

## Contracts that must not break

| Contract | Location |
|----------|----------|
| Equity formula | `nt/bankroll.py` ← `data/bets.csv` + baseline |
| Phase / risk JSON | `data/state/phase.json`, `risk.json`, `bankroll.json` |
| Status markdown | `data/state/status.md` |
| Recommend / settle | `nt.recommend.run_recommend`, `nt.settle.run_settle` |
| Bets header | `nt.bets_io.BET_HEADER` |
| Config load | `config.yaml` via `nt.config.load_config` |
| Project root | `NT_PROJECT_ROOT` or repo root |

## Safe additive UI surfaces

| Feature | Suggested mode | Backend |
|---------|----------------|---------|
| Analyze report | Book / Lab | `nt.analyze.run_analyze` or CLI `analyze` |
| Bankroll projection chart | Lab | `nt.project.simulate_paths` |
| Edges browser | Lab | `nt.edges.query_edges` |
| Research scaffold button | Desk / Workflow | `nt.research.scaffold_evidence` |
| Combo policy badge | Desk / Risk | `nt.combos.combo_policy_summary` |
| Agent chat (optional) | Lab | `nt.agent.ask` + show audit path |
| Loss-streak A-only banner | Desk | `analyze` streak_gate or portfolio rejects |

## Hard rules for GUI authors

1. **Do not reimplement** stake sizing, phase unlock, or daily cap in TypeScript/React without calling Python engines (or reading generated state files).
2. **Never** let agent UI call non-dry-run recommend without a confirm dialog.
3. **Never** rewrite historical `bets.csv` rows from the GUI except via settle/engine APIs.
4. Prefer reading `data/state/*.json` for dashboards; call engines for mutations.
5. Keep Windows Flet constraints in `desktop/AGENTS.md` if using this repo’s Flet UI.
6. **Desk “Analyze odds” must call `research board` first**, not bare `recommend`. Show `outbox/RESEARCH_BOARD.md`. Recommend is step 2 after evidence.
7. If `recommend` returns `blocked: true` / exit code 3, surface the message and link to board research — do not treat as empty-slip success.
8. **Lab:** optional panels for `outbox/SIM_LATEST.md` and `outbox/CALIBRATION.md` / `calibrate report` JSON. Sim never auto-places.
9. Calibration path: `data/state/calibration.jsonl` (append-only).

## Tauri / React companion

If LuminaNT is a separate Tauri shell:

1. Point `NT_PROJECT_ROOT` (or config) at this repo root.
2. Shell out to `python run_nt.py …` or embed a small Python sidecar that imports `nt.*`.
3. Watch `outbox/PLACE_THESE.md` and `data/state/status.md` for live panels.
4. Surface new commands as optional menu items; keep v3 command names for scripts.

## Example: Desk “Process health” chip

```
Equity · Phase · Remaining risk · Can bet
+ Grade-A-only if loss streak ≥ 3
+ Combos: OFF (phase 1A)
```

Data sources: `refresh_state()` once per poll interval (respect existing auto-sync patterns).

## Next iterations (recommended)

1. Lab tab: embed markdown from `nt analyze` / `nt project`.
2. Evidence editor with checklist checkboxes → write `evidence/*.json`.
3. Agent panel with tool-call timeline from `agent_audit.jsonl`.
4. Combo builder UI that calls `assess_combo` and still requires human place.
5. Do **not** auto-scrape NT Oddsen from the GUI without legal/ToS review.
