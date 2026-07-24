---
name: daily-run
description: >
  Full NT betting-desk daily run under Forced Evidence Hierarchy: settle →
  odds dump → market-scan → board+light → deep queue + coverage floor →
  FEH packs (side-first, anti-soft underdog, sport cards) → recommend only
  quality lines → Reasoning Chains (band · +/− · FEH gate) → PLACE_THESE.md
  → place-ack (10 NOK test cap when active). Use when the user runs
  /daily-run, says "daily run", "run the day", "today's desk", "full
  research day", or drops a new inbox/odds file for a complete session.
  Accepts optional kick-off window and odds filename.
metadata:
  short-description: "Full day + FEH non-bypassable (quality > volume, 10 NOK test)"
---

# /daily-run — Full desk day (FEH + research quality first)

Real-money capital desk. **Engines in `nt/` are law.** Load project rules first; never invent `p_model` or soften min_EV by hand.

**Forced Evidence Hierarchy (FEH) is NON-BYPASSABLE.** Side first, then price. Soft mid-odds underdogs with weak matchup evidence must **not** pass. Prefer **empty slip** over weak Grade B. Preferred / mid band is **research-rank only** — not soft-dog attractiveness.

> **Repo mirror:** this file is the committed copy of `~/.grok/skills/daily-run/SKILL.md`. Keep both in sync on FEH docs PRs. Desk pointer: [`DESK_SKILLS.md`](./DESK_SKILLS.md). Design: [`FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md`](./FORCED_EVIDENCE_HIERARCHY_FULL_CLEANUP_AND_10NOK_TEST_2026-07-24.md).

## 0) Bootstrap (mandatory)

1. `Read` the repo root **`AGENTS.md`** — especially **Forced Evidence Hierarchy** + engine deep queue (preferred band = research-rank only).
2. Skim **`docs/DESK_SKILLS.md`** if needed.
3. Confirm CWD is the **nt-betting-tracker** worktree root (`run_nt.py` present).
4. Force **real tools** — shell CLI, web search/open for deep research, file read/write. Do not simulate board/light/recommend output.
5. Identify odds file:
   - Path the user named, **or**
   - Path they asked to write (e.g. `inbox/odds_2026-07-24.txt` for a kick-off window), **or**
   - **Newest** `inbox/odds*.txt` by mtime.

### Optional: kick-off window + dump

If the user specifies a timeframe (Europe/Oslo) and filename, collect/write the Oddsen dump to that path **first**, then continue the path below. Same standards apply.

Example shape:

```text
/daily-run Collect the current Oddsen board from Norsk Tipping for kick-offs between
14:00 and 23:00 Europe/Oslo.
Write the dump to inbox/odds_YYYY-MM-DD.txt,
then run the full path under FEH research standards.
```

## Research standards (automatic — do not skip)

### A) Forced Evidence Hierarchy (NON-BYPASSABLE)

- **Place law** on every candidate: checklist complete → `decide_side` (side first) → anti-soft underdog → natural market elevation when required → SAEF / sport card → research_gates → EV.
- Coverage, explore, deep-queue promo, and `temp_ev_relax` **cannot** place a pack FEH hard-rejects (e.g. `FEH_ANTI_SOFT_UNDERDOG`).
- **Side first, price second** — do not lead with “underdog @ 1.85 looks good.”
- Soft underdog HC ~**1.70–2.20** (outer to 2.60): needs **structured** positive H2H + form not-fav + why-side + rank OK. Mixed / negative / unknown H2H → **reject**. Free-text claim alone is not enough.
- Prefer **empty slip** over weak soft Grade B dogs.

### B) Sport Research Cards + SAEF

- Every sport **must** have or auto-create `evidence/sport_cards/<sport>.yaml` before deep/recommend.
- Card = primary / secondary / tertiary factors · sources · weights · Grade A/B/C/Reject floors · hard rejects.
- **Individual sports** (tennis, snooker, darts, table tennis, …): **H2H high-weight / near-mandatory**.
- Soft underdog HC without matchup edge → **reject** (not mid-band Grade B by price alone).
- New sport → quarantine card (`onboarded: false`) → **no mid-band place** until reviewed.

### C) Preferred / mid band = research-rank only (not place quality)

| Odds role | Meaning |
|-----------|---------|
| Deep-queue **preferred** ≥55% | Research diversity so mid-price lines get honest packs |
| Band **1.85–2.60** promo boost | **Queue identity** — not automatic Grade B |
| Soft UD **1.70–2.20** | **Anti-soft gate** territory — not attractive by default |

Sliding confidence / odds_confidence still raise the bar as prices shorten; FEH remains primary.

### D) Quality over volume

- Empty slip after honest research = **success**.
- Do **not** force bets to fill preferred band or coverage targets.
- Coverage floor expands *what to research* only — never bypasses FEH / card / band gates.
- `temp_ev_relax` must respect FEH + SAEF floors.

### E) 10 NOK test stake cap (when active)

- First **10 placed** (place-ack) bets tagged `FEH_TEST_CAP:feh_v1` → max **10 NOK** per seat.
- Absolute-last clip after rebalance + EXPLORE_REGIME clamp — **does not** change capital_v2 / unit / phase math.
- See `data/state/status.md` → **Forced Evidence Hierarchy** for `test_cap: n/10`.

### F) Reasoning Chain (every pick + near-miss)

Must show:

1. **Which band** the selection sits in (research-rank vs place bar)  
2. **Strongest positive** signal  
3. **Strongest negative** signal  
4. **Why it passed or failed** (FEH codes, side, anti-soft, sport card, HR, EV)

## 1) Results first (if any open risk)

```powershell
python run_nt.py status
python run_nt.py settle --draft
# After user/agent confirms outcomes:
# python run_nt.py settle --results inbox/results.yaml
# or: python run_nt.py settle --items-json inbox/_settle_items.json
python run_nt.py control-signals list --json
python run_nt.py refresh
```

- Fill **PostSettlementPacket** fields on process_error / poor retro.
- Classify **predictability + variance_class + learning_weight** every settle (`/learning-rootcause` if batch).
- Learning proposals auto-apply when configured — do not ask user to accept.

## 2) Market coverage + board + light

```powershell
python run_nt.py research market-scan --odds <odds_file>
python run_nt.py research board --odds <odds_file>
# if board did not auto-light:
python run_nt.py research light --odds <odds_file>
python run_nt.py research light --odds <odds_file> --merge-deep   # after packs exist
```

Read and report:

| Artifact | Path |
|----------|------|
| Board report | `outbox/research_board*.md` (or board printout) |
| Light batch | `outbox/light_research/` |
| Deep queue SSOT | `data/state/deep_queue.json` |
| Coverage Health | `data/state/coverage_health.json` |
| Sport cards | `evidence/sport_cards/` |
| Status / FEH / floors | `data/state/status.md` · `data/state/risk.json` |

Check: Light coverage % · engine deep queue size · composition (≥55% research-preferred / ≤25% short-main) · Coverage Health · FEH / test_cap · ControlSignals.  
**Queue promotion is not a place pass** — FEH still applies at recommend.

## 3) Deep queue research (side-first + cards)

1. Work **engine deep_queue** first (research-rank mid band 1.85–2.60, alts, HC, longer ML — anti-chalk **for research**, not place).  
2. Scaffold (loads sport card, correct sources, `signals` + `h2h` + checklist stubs):

```powershell
python run_nt.py research board --odds <odds_file> --write-scaffolds
# or single line:
python run_nt.py research scaffold --match "…" --selection "…" --sport darts --write
```

3. Deep-research each queue line **side-first** using card primary factors (web: sport-correct sources — HLTV for CS, CueTracker for snooker, Darts Orakel for darts, FBref for football, etc.). Compare favourite HC / natural totals before locking a soft dog.  
4. Write full evidence packs:

```powershell
python run_nt.py research write-pack --match "…" --selection "…" --p-model 0.XX `
  --sport darts --odds-ref 1.95 --summary "…" --failure-modes "…" `
  --availability-status predicted --context-risk low `
  --script-lean competitive --selection-vs-script agree
python run_nt.py research critique evidence/<file>.json --odds 1.95
```

**Pack minimum for placeable mid-band:**

- Quality takeaways ≥24 chars (enough quality sources for card floor)  
- Required `signals{}` filled for that sport × market  
- `h2h.checked` + normalized edge for underdog HC / individual sports  
- FEH checklist complete · honest `p_model` · no script conflict  

**Hard rejects:** FEH codes (checklist / side / anti-soft / natural) · script/base-rate conflict · missing availability on sensitive markets · **negative/mixed/missing H2H on underdog HC** · empty takeaways · wrong-sport sources · quarantined sport.  
**Never invent `p_model`** to fill seats or clear EV.

## 4) Ready + recommend (live default)

```powershell
python run_nt.py research ready --odds <odds_file>
python run_nt.py recommend --odds <odds_file>
# only if Coverage Health critical AND user/ops explicitly override:
# python run_nt.py recommend --odds <odds_file> --allow-low-coverage
# dry-run ONLY if user asks:
# python run_nt.py recommend --odds <odds_file> --dry-run
```

- Only lines that clear **FEH + sport card + EV**.  
- Present slip with **Reasoning Chains** (band · +/− · FEH gate).  
- Empty slip after honest deep research = **success**.  
- When test cap active, expect ≤ **10 NOK** stakes and `FEH_TEST_CAP:…` in notes.  
- Do not re-advise already Pending/ConfirmedPlaced tickets.

## 5) Place session (operator default)

User places on Norsk Tipping. Then:

```powershell
python run_nt.py place-ack --ids <bet_id>[,<bet_id>...]
# missed / never placed:
python run_nt.py abandon --ids <bet_id> --reason missed_prematch
python run_nt.py status
```

## Exhaustive CLI map (daily desk)

| Stage | Command |
|-------|---------|
| Status | `python run_nt.py status` · `refresh` · `validate` |
| Capital | `python run_nt.py capital status` · `capital segments` |
| Settle | `settle --draft` · `settle --results …` · `settle --items-json …` |
| Learning | `learn` · `learn --proposals` · `control-signals list` |
| Research | `research market-scan` · `board` · `light` · `ready` · `scaffold` · `write-pack` · `critique` · `p-model` · `sources` · `checklist` |
| Decision | `recommend` · `place-ack` · `abandon` |
| Sims (suggest only) | `simulate --sport tennis\|football\|basketball …` |
| Analyze | `analyze` · `calibrate report` · `project` · `edges` |
| FEH oracle (dev) | `python scripts/verify_feh_smith_price.py` · `python scripts/feh_cleanup_inventory.py` |

## Deliverables (list paths in final reply)

1. Odds file used: `inbox/…`
2. Light report: `outbox/light_research/…`
3. Deep queue: `data/state/deep_queue.json`
4. Sport cards touched: `evidence/sport_cards/…`
5. Evidence packs written: `evidence/*.json`
6. Coverage Health: `data/state/coverage_health.json`
7. Slip: **`outbox/PLACE_THESE.md`**
8. Status: `data/state/status.md` (FEH + coverage floor) · `data/state/risk.json`
9. Reasoning Chains (band · +/− · FEH on picks + near-misses)
10. place-ack / abandon bet_ids if a place session ran

## Hard rules (do not break)

- Load AGENTS.md first every session.
- Live recommend by default; dry-run only on request.
- Deep-research engine queue (anti-chalk research); do not only short ML/O2.5.
- **FEH NON-BYPASSABLE** — side first, then price; anti-soft underdog on soft UD HC.
- Preferred / mid band = **research-rank only** — not soft-dog attractiveness or automatic Grade B.
- Soft underdog HC without structured matchup → **reject**.
- Prefer empty slip over weak Grade B.
- Coverage Health **critical** → soft-gate recommend unless explicit `--allow-low-coverage`.
- Coverage floor / temp_ev_relax / explore **must not** force FEH fails onto the slip.
- Engines own bankroll/phase/risk; UI never invents stakes.
- **Do not change** capital_v2, phase ladder, secure bucket, unit sizing, or staking math (10 NOK is post-size clip only).
- After place session: place-ack new Pending unless user says missed → abandon.
