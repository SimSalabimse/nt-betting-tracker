# Optional AI Agent (Assist-Only)

## Role

## Odds-file protocol (Grok / CLI agents)

Whenever the user drops or updates an odds file, follow **root `AGENTS.md`**: board → real research → evidence packs → `research ready` → `recommend` (live by default; `--dry-run` only if user asks) → present slip (exclude Pending from new-place advice). Do not mechanical-force unless asked.

---

The agent is a **research and analysis co-pilot**. It must never:

- Bypass phase / risk / evidence engines
- Write to `data/bets.csv` without explicit human-driven `recommend` / `settle`
- Place bets on Norsk Tipping
- Invent settled results

It **may**:

- Summarize ledger patterns, edges, and learning mults
- Critique evidence packs and suggest failure modes
- Propose research checklists and p_model sanity checks
- Run **dry-run** recommend and read-only status tools
- Draft strategy notes for you to accept or reject

## Configuration

```yaml
# config.yaml (all optional — defaults safe)
agent:
  enabled: false
  provider: auto          # auto | xai | openai | none
  model: ""               # provider default if empty
  # API keys: prefer environment variables, not committed secrets
  # XAI_API_KEY / OPENAI_API_KEY
  max_tool_rounds: 6
  audit_log: data/state/agent_audit.jsonl
  allow_cli_dry_run: true
  allow_write_evidence_scaffold: true   # may create draft evidence files only if you pass --write
  temperature: 0.2
```

Environment:

| Variable | Use |
|----------|-----|
| `XAI_API_KEY` | xAI / Grok API |
| `OPENAI_API_KEY` | OpenAI-compatible API |
| `NT_AGENT_PROVIDER` | Override provider |
| `NT_AGENT_MODEL` | Override model |

## CLI

```bash
# Local tools only (no API) — still useful
python run_nt.py agent tools
python run_nt.py agent status-brief
python run_nt.py agent critique-evidence evidence/example.json

# LLM chat with tool calling (requires key + agent.enabled)
python run_nt.py agent ask "Summarize my last 30 settled bets by sport ROI"
python run_nt.py agent ask "Is this high-odds candidate evidence strong enough?" --context evidence/foo.json
```

## Safe tools (function calling)

| Tool | Access |
|------|--------|
| `get_status` | Read bankroll/phase/risk |
| `get_ledger_summary` | Analytics deep-dive slice |
| `query_bets` | Filtered ledger rows (capped) |
| `query_edges` | Recent edges.jsonl |
| `get_learning` | learning.json mults / lessons |
| `grade_evidence_file` | Run grader on a path |
| `dry_run_recommend` | `recommend --dry-run` equivalent |
| `list_evidence` | List evidence/*.json |
| `ev_calc` | Haircut EV helper |
| `project_bankroll` | Simulation summary (read-only math) |

## Auditability

Every agent turn appends to `data/state/agent_audit.jsonl`:

```json
{"ts":"…","role":"user","content":"…"}
{"ts":"…","role":"tool","name":"get_status","result_digest":"…"}
{"ts":"…","role":"assistant","content":"…"}
```

You can disable the agent entirely with `agent.enabled: false` (default). Offline `agent tools` / `critique-evidence` still work without API keys.

## LuminaNT integration

Desktop should treat agent as optional Lab/Desk panel:

1. Call the same CLI or import `nt.agent` tools.
2. Show audit log path.
3. Never auto-invoke settle or non-dry-run recommend from agent UI without confirmation.

## Prompt contract (for external Grok Build / Chat)

When using Grok outside this repo, attach:

- `data/state/status.md`
- Relevant evidence JSON
- `outbox/PLACE_THESE.md` if placing
- Instruction: **follow NT engines; empty slip OK; do not invent stakes outside phase**
