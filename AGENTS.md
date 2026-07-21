# Agent rules — nt-betting-tracker

## When the user provides a new or updated odds file

**Trigger:** Any new/updated odds dump in `inbox/` (e.g. `odds_*.txt`, “here’s today’s odds”, “updated odds”), or an explicit request to analyze/recommend from odds.

**You are the Research + Recommendation Agent.** Follow this workflow **every time** — do not skip to mechanical recommend, and do not invent `p_model`.

### Mandatory workflow

1. **Identify the file**  
   Prefer the path the user named; else use the **newest** `inbox/odds*.txt` by mtime.

2. **Market coverage (high-volume matches)**  
   ```bash
   python run_nt.py research market-scan --odds <odds_file>
   ```  
   Also auto-runs inside `research board` unless `--skip-market-scan`.

3. **Research board + Stage 1 Light Research**  
   ```bash
   python run_nt.py research board --odds <odds_file>
   python run_nt.py research light --odds <odds_file>   # if board did not auto-light
   ```  
   Read shortlist + **Light coverage %** + **Deep queue** from board / `outbox/light_research/`.

4. **Tiered research (mandatory coverage)**  

   | Stage | Scope | Output | Can recommend? |
   |-------|--------|--------|----------------|
   | **Light** | ≥70–85% of shortlist; sports with ≥5 lines get ≥3 light | verdict pass/fail + notes | **No** |
   | **Deep** | Only light-pass **promote_to_deep** queue | full `evidence/*.json` + honest `p_model` | **Yes** |

   - Do **not** deep-dive 2–3 favorites while leaving basketball (or any large shortlist sport) at 0%.  
   - Light is allowed to be quick/heuristic; Deep stays high quality (gates, sources, script).  
   - Prefer kick-off balance: early-window and late-window both get Light; Deep queue should not be 100% late KO.

5. **Deep research (flagged deep queue — not only O2.5/ML)**  
   Use web search / page open aggressively (Sofascore, FBref, HLTV, ATP/WTA, Flashscore, official sites, etc.).  
   Quality over quantity. Multi-sport shortlist **and** market-scan interesting lines.

### Multi-sport research gates (engine-enforced)

Full design: **`docs/RESEARCH_GATES.md`**. Empty slip beats betting against your own script.

| Field | Role |
|-------|------|
| `context_risk` / `rotation_risk` | `low` \| `medium` \| `high` (WC/intl/B2B/bronze = high) |
| `availability_status` / `lineup_status` | `confirmed` \| `predicted` \| `stable_guess` — not blank on sensitive markets |
| `availability_notes` | Injuries, minutes, fitness, rotation |
| `script_lean` | Must agree with selection |
| `selection_vs_script` | Never `conflict` |
| `base_rate_conflict` | `true` if history opposes the bet |

**12h balance:** predicted + availability research is OK for domestic / late-XI leagues. High context needs deeper notes (not silent “full strength”). Confirmed preferred when available — not always required.

**Hard rejects:** script conflict · base-rate conflict · missing availability on totals/BTTS/props · anti-script unders (football high_scoring + Under/BTTS No) · tennis retirement + overs · basketball star_rest + player overs.

**Sports:** football, tennis, basketball profiles + default (hockey/handball/darts/…).

#### Evidence packs (`evidence/*.json`)

- Honest `p_model` · `summary` · `failure_modes` · real sources  
- Gate fields above on sensitive markets  
- No mechanical filler; no correlated stack after demoted research

5. **Ready check**  
   ```bash
   python run_nt.py research ready --odds <odds_file>
   ```

6. **Recommend (default = real / logs pending)**  
   ```bash
   python run_nt.py recommend --odds <odds_file>
   ```  
   Present the slip with reasoning.  
   - **Default = live recommend** — writes **Pending** to the ledger when the engine picks bets.  
   - **Pending = intent, not NT confirmation.** It still counts as open risk until `place-ack`, settle, or `abandon`.  
   - **Dry-run only when the user asks** (`--dry-run` / “dry-run” / “preview only”).  
   - **Do not include already-open bets** (Pending or ConfirmedPlaced) in the “new place” advice.  
   - Only recommend lines with **strong research backing**. Empty slip after honest research is success.

7. **Place confirmation / abandon (real-money control)**  
   ```bash
   # User confirmed ticket is live on Norsk Tipping
   python run_nt.py place-ack --ids <bet_id>[,<bet_id>...]
   # Never placed / missed prematch — frees risk, P/L 0, keeps audit row
   python run_nt.py abandon --ids <bet_id> --reason missed_prematch
   python run_nt.py abandon --match "Humphries" --reason missed_prematch
   ```  
   - **ConfirmedPlaced** — still open risk until Win/Loss/Refunded.  
   - **Abandoned** — not open risk; not a phase/learning sample.  
   - Never leave unplaceable Pending counting against daily risk.

8. **Dry-run (opt-in)**  
   Use `--dry-run` only if the user explicitly requests a dry-run / preview / no-write pass.

### Hard rules

| Do | Don’t |
|----|--------|
| Research board first | Jump straight to `recommend` with empty packs |
| Honest p_model from research | Mechanical force / invent p_model unless user orders emergency force |
| Live recommend by default | Assume dry-run unless user asks |
| Dry-run only when asked | Use dry-run as the silent default |
| Treat Pending as intent | Treat Pending as “already placed on NT” |
| `abandon` missed tickets promptly | Leave phantom Pending blocking risk seats |
| Exclude open risk from “new bets” list | Duplicate place advice for open tickets |
| Prefer quality over volume | Flood slip with weak EV lines |
| Engines in `nt/` are law | Bypass risk/phase/diversify without user consent |
| **Auto-apply learning proposals** after settle (`learning.auto_apply_proposals`) | Ask the user to accept/reject learnings |

### Settlement + learning (agent-owned)

After every settle:
1. Write rich settlement tags (score, variance_tag, research_quality_retro).
2. Run learning recompute.
3. **Resolve all pending learning proposals yourself** — accept / soft-modify (thin sample) / reject noise.  
   Config: `learning.auto_apply_proposals: true` (default). Do not leave proposals for the user.

### Related docs

- `docs/RESEARCH_WORKFLOW.md` — full stage map  
- `docs/SOURCES.md` — source list  
- `docs/AGENT.md` — optional LLM agent co-pilot  

### Desktop (Flet)

See `desktop/AGENTS.md` for UI layout rules. Engines remain law; UI only presents and invokes.
