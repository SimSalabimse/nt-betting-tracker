#!/usr/bin/env python3
"""
Dry-run daily desk path (no Pending ledger write).

Finds newest odds file in inbox/, runs research board + light + recommend --dry-run,
then prints a short summary: PLACE slip, deep queue, reasoning chains, coverage floor.

Usage (from tracker root):
  python scripts/dry_run_daily_path.py
  python scripts/dry_run_daily_path.py --odds inbox/odds_2026-07-23.txt

Soft-fails with a clear message if no odds dump is present.
Does not commit data/state — operator decides what to keep.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import nt_bootstrap  # noqa: F401,E402


def _newest_odds(inbox: Path) -> Path | None:
    patterns = ("odds*.txt", "odds*.csv", "odds*.md", "current_odds*.txt", "current_odds*.csv", "*odds*.txt")
    cands: list[Path] = []
    for pat in patterns:
        cands.extend(inbox.glob(pat))
    # Prefer real dumps over templates
    real = [
        p
        for p in cands
        if p.is_file() and "template" not in p.name.lower() and p.stat().st_size > 32
    ]
    pool = real or [p for p in cands if p.is_file()]
    if not pool:
        return None
    pool.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return pool[0]


def _run(cmd: list[str], *, timeout: int = 180) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        return int(proc.returncode), out
    except subprocess.TimeoutExpired as e:
        return 124, f"TIMEOUT after {timeout}s: {e}"
    except Exception as e:
        return 1, f"ERROR: {e}"


def _read_text(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return f"(missing: {path})"
    t = path.read_text(encoding="utf-8", errors="replace")
    if len(t) > max_chars:
        return t[:max_chars] + f"\n… [{len(t) - max_chars} more chars]"
    return t


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _deep_queue_summary() -> str:
    p = ROOT / "data" / "state" / "deep_queue.json"
    if not p.exists():
        # fallback: light research dir
        lr = ROOT / "outbox" / "light_research"
        if lr.is_dir():
            files = sorted(lr.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
            if files:
                return f"no deep_queue.json; latest light report: {files[0].name}"
        return "deep_queue.json not found (board/light may not have written SSOT yet)"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return f"deep_queue.json unreadable: {e}"
    if isinstance(data, dict):
        items = data.get("queue") or data.get("items") or data.get("deep_queue") or []
        n = data.get("n") or data.get("size") or (len(items) if isinstance(items, list) else "?")
        pref = data.get("preferred_share") or data.get("composition", {}).get("preferred_share")
        short = data.get("short_main_share") or data.get("composition", {}).get("short_main_share")
        bits = [f"n={n}"]
        if pref is not None:
            bits.append(f"preferred_share={pref}")
        if short is not None:
            bits.append(f"short_main_share={short}")
        if isinstance(items, list) and items:
            sample = items[:3]
            labels = []
            for it in sample:
                if isinstance(it, dict):
                    labels.append(
                        f"{it.get('match') or '?'} / {it.get('selection') or '?'}"
                    )
                else:
                    labels.append(str(it)[:60])
            bits.append("top: " + "; ".join(labels))
        return " | ".join(bits)
    if isinstance(data, list):
        return f"n={len(data)} (list SSOT)"
    return f"type={type(data).__name__}"


def _coverage_floor_section() -> str:
    status = ROOT / "data" / "state" / "status.md"
    if not status.exists():
        return "(status.md missing — run refresh/board first)"
    text = status.read_text(encoding="utf-8", errors="replace")
    # Prefer explicit Coverage floor section
    m = re.search(
        r"(?is)##\s*Coverage floor\b(.*?)(?=\n##\s|\Z)",
        text,
    )
    if m:
        body = m.group(0).strip()
        if len(body) > 2500:
            body = body[:2500] + "\n…"
        return body
    # Fallback: coverage-related lines
    lines = [
        ln
        for ln in text.splitlines()
        if re.search(r"coverage|deep.?queue|temp_ev_relax|force_coverage", ln, re.I)
    ]
    if lines:
        return "\n".join(lines[:40])
    return "(no Coverage floor section found in status.md)"


def main() -> int:
    ap = argparse.ArgumentParser(description="Dry-run daily research→recommend path")
    ap.add_argument("--odds", default=None, help="Odds file (default: newest inbox/odds*)")
    ap.add_argument("--skip-board", action="store_true", help="Skip research board")
    ap.add_argument("--skip-light", action="store_true", help="Skip research light")
    ap.add_argument("--skip-recommend", action="store_true", help="Skip recommend dry-run")
    ap.add_argument(
        "--allow-low-coverage",
        action="store_true",
        help="Pass --allow-low-coverage to recommend if supported",
    )
    args = ap.parse_args()

    print("=== dry_run_daily_path ===")
    print(f"ROOT: {ROOT}")

    inbox = ROOT / "inbox"
    if args.odds:
        odds = Path(args.odds)
        if not odds.is_absolute():
            odds = (ROOT / odds).resolve()
    else:
        odds = _newest_odds(inbox)

    if odds is None or not odds.exists():
        print()
        print("SOFT-FAIL: no usable odds dump found.")
        print(f"  Looked in: {inbox}")
        print("  Expected:   inbox/odds_*.txt (or .csv) — not only odds_template.*")
        print()
        print("  Drop today's Oddsen dump into inbox/, then re-run:")
        print("    python scripts/dry_run_daily_path.py")
        print("  Or pass a path:")
        print("    python scripts/dry_run_daily_path.py --odds path/to/odds.txt")
        return 2

    if "template" in odds.name.lower():
        print()
        print(f"SOFT-FAIL: refusing template odds file: {odds.name}")
        print("  Provide a real Oddsen dump (odds_*.txt) in inbox/.")
        return 2

    print(f"Odds: {odds} ({odds.stat().st_size} bytes)")
    py = sys.executable
    run_nt = [py, str(ROOT / "run_nt.py")]

    steps_ok = True

    if not args.skip_board:
        print("\n--- research board ---")
        # board has no --dry; writes outbox + state (expected for desk path)
        code, out = _run(run_nt + ["research", "board", "--odds", str(odds)], timeout=240)
        print(out[-3000:] if len(out) > 3000 else out)
        if code != 0:
            print(f"[board exit={code}]")
            steps_ok = False

    if not args.skip_light:
        print("\n--- research light ---")
        code, out = _run(run_nt + ["research", "light", "--odds", str(odds)], timeout=240)
        print(out[-3000:] if len(out) > 3000 else out)
        if code != 0:
            print(f"[light exit={code}]")
            steps_ok = False

    rec_result = {}
    if not args.skip_recommend:
        print("\n--- recommend --dry-run ---")
        rec_cmd = run_nt + ["recommend", "--odds", str(odds), "--dry-run"]
        if args.allow_low_coverage:
            rec_cmd.append("--allow-low-coverage")
        code, out = _run(rec_cmd, timeout=240)
        print(out[-4000:] if len(out) > 4000 else out)
        if code not in (0, 3):  # 3 = blocked research / coverage — still a valid dry path signal
            print(f"[recommend exit={code}]")
            steps_ok = False
        # Try parse JSON blob from output
        try:
            start = out.find("{")
            end = out.rfind("}")
            if start >= 0 and end > start:
                rec_result = json.loads(out[start : end + 1])
        except Exception:
            rec_result = {}

    print("\n========== SUMMARY ==========")
    place = ROOT / "outbox" / "PLACE_THESE.md"
    print(f"PLACE_THESE: {place}")
    if place.exists():
        text = place.read_text(encoding="utf-8", errors="replace")
        # table + reasoning header
        for line in text.splitlines()[:25]:
            print("  " + line)
        if "## Reasoning" in text:
            print("  …")
            idx = text.index("## Reasoning")
            print(text[idx : idx + 1200])
        else:
            print("  (no ## Reasoning section yet)")
    else:
        print("  (PLACE_THESE.md missing)")

    print("\nDeep queue:")
    print("  " + _deep_queue_summary())

    chains_path = ROOT / "data" / "state" / "reasoning_chains.jsonl"
    n_chains = _count_jsonl(chains_path)
    print(f"\nReasoning chains: {n_chains} rows in {chains_path.relative_to(ROOT)}")
    if rec_result.get("n_reasoning_chains") is not None:
        print(f"  this run (recommend): {rec_result.get('n_reasoning_chains')}")

    print("\nCoverage floor (status.md excerpt):")
    for ln in _coverage_floor_section().splitlines():
        print("  " + ln)

    ch = ROOT / "data" / "state" / "coverage_health.json"
    if ch.exists():
        try:
            health = json.loads(ch.read_text(encoding="utf-8"))
            print("\nCoverage health:")
            for k in (
                "level",
                "shortlist_deep_pct",
                "deep_survivable_pct",
                "mid_unresearched_n",
                "empty_slip_risk",
            ):
                if k in health:
                    print(f"  {k}: {health[k]}")
        except Exception as e:
            print(f"\nCoverage health unreadable: {e}")

    print("\nRecommend meta:")
    for k in ("blocked", "n_picked", "n_rejects", "phase", "remaining_risk", "message"):
        if k in rec_result:
            print(f"  {k}: {rec_result[k]}")

    print("\nNote: dry-run does not log Pending. data/state may still update from board/light/refresh.")
    print("Do not commit data/state from this path unless intentional.")

    if not steps_ok:
        print("\nRESULT: completed with step failures (see above).")
        return 1
    print("\nRESULT: dry path finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
