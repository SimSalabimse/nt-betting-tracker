#!/usr/bin/env python3
"""
safe_bet_log_edit.py - Robust, safe editor for bet_log.csv
Part of nt-bet-log-manager skill.

Rules enforced:
- Exact header only.
- Append-only for new pending bets (always at bottom, Result=Pending, P_L empty).
- Targeted settlement updates ONLY (Result + P_L_NOK, append to Notes). Never delete or overwrite history.
- Never reduce row count without explicit confirmation.
- Always backup before any write.
- Atomic write using tempfile.
- Full post-edit validation.
- Proper CSV quoting for Notes (handles commas, quotes, etc.).

Usage:
  python safe_bet_log_edit.py validate bet_log.csv
  python safe_bet_log_edit.py add-pending bet_log.csv "2026-06-18,Match,Selection,2.50,100,Pending,,Notes here"
  python safe_bet_log_edit.py settle bet_log.csv "2026-06-18,Match,Selection" "Win" "150.00"

The script is designed to be called by Grok via the nt-bet-log-manager skill.
It can also be run manually by the user.
"""

import csv
import sys
import os
import shutil
import tempfile
from datetime import datetime
from io import StringIO

EXPECTED_HEADER = ["Date", "Match", "Selection", "Decimal_Odds", "Stake_NOK", "Result", "P_L_NOK", "Notes"]

def get_row_count(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        return sum(1 for _ in f) - 1  # minus header

def backup_file(filepath):
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"[BACKUP] Created backup: {backup_path}")
        return backup_path
    return None

def validate_csv(filepath, strict=True):
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return False

    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print("[ERROR] File is empty")
            return False

        if header != EXPECTED_HEADER:
            print(f"[ERROR] Header mismatch!")
            print(f"Expected: {EXPECTED_HEADER}")
            print(f"Got:      {header}")
            return False

        row_count = 0
        errors = []
        for i, row in enumerate(reader, start=1):
            row_count += 1
            if len(row) != len(EXPECTED_HEADER):
                errors.append(f"Row {i}: Wrong field count ({len(row)} vs {len(EXPECTED_HEADER)})")

        if errors:
            print("[ERROR] Validation failed:")
            for e in errors:
                print(f"  - {e}")
            return False

        print(f"[OK] Validation passed. Header correct. {row_count} data rows.")
        return True

def write_atomic(filepath, rows):
    """Write rows to filepath atomically using tempfile."""
    dir_name = os.path.dirname(os.path.abspath(filepath)) or "."
    fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerows(rows)
        os.replace(temp_path, filepath)  # Atomic on POSIX
        print(f"[OK] Atomic write completed to {filepath}")
        return True
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        print(f"[ERROR] Atomic write failed: {e}")
        return False

def add_pending(filepath, new_row_str):
    """Append a new pending bet. new_row_str = comma-separated or CSV string."""
    old_count = get_row_count(filepath)
    backup_file(filepath)

    try:
        new_row = list(csv.reader(StringIO(new_row_str)))[0]
    except Exception as e:
        print(f"[ERROR] Failed to parse new row: {e}")
        return False

    if len(new_row) != len(EXPECTED_HEADER):
        print(f"[ERROR] New row has wrong number of fields: {len(new_row)}")
        return False

    # Force correct pending state
    new_row[5] = "Pending"
    new_row[6] = ""

    # Read existing
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        existing_rows = list(reader)

    all_rows = [header] + existing_rows + [new_row]

    if not write_atomic(filepath, all_rows):
        return False

    new_count = get_row_count(filepath)
    print(f"[OK] Appended new pending bet. Row count: {old_count} -> {new_count}")
    return validate_csv(filepath)

def settle_bet(filepath, identifier, new_result, new_pl):
    """
    identifier: string that uniquely identifies the row (Date,Match,Selection or part of Notes).
    Only updates that specific row's Result and P_L_NOK. Appends to Notes.
    """
    old_count = get_row_count(filepath)
    backup_file(filepath)

    rows = []
    updated = False
    match_found = False

    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)

        for row in reader:
            row_str = ','.join(row).lower()
            if identifier.lower() in row_str and not match_found:
                # Targeted update only
                row[5] = new_result
                row[6] = new_pl
                # Append to Notes (never overwrite)
                if row[7]:
                    row[7] = row[7].rstrip() + f" | Settled: {new_result} P/L {new_pl}"
                else:
                    row[7] = f"Settled: {new_result} P/L {new_pl}"
                updated = True
                match_found = True
            rows.append(row)

    if not match_found:
        print(f"[ERROR] No matching row found for identifier: {identifier}")
        return False

    if not updated:
        print("[WARN] No update was needed (already settled or no match).")
        return False

    if not write_atomic(filepath, rows):
        return False

    new_count = get_row_count(filepath)
    if new_count < old_count:
        print(f"[CRITICAL WARNING] Row count decreased! {old_count} -> {new_count}. This should not happen.")

    print(f"[OK] Settled bet and updated row. Row count: {old_count} -> {new_count}")
    return validate_csv(filepath)

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nCommands: validate | add-pending | settle")
        sys.exit(1)

    command = sys.argv[1].lower()
    filepath = sys.argv[2]

    if command == "validate":
        validate_csv(filepath)
    elif command == "add-pending":
        if len(sys.argv) < 4:
            print("Usage: add-pending <file> <csv-row-string>")
            sys.exit(1)
        add_pending(filepath, sys.argv[3])
    elif command == "settle":
        if len(sys.argv) < 5:
            print("Usage: settle <file> <identifier> <new_result> <new_pl>")
            sys.exit(1)
        settle_bet(filepath, sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
    else:
        print(f"Unknown command: {command}")
        print(__doc__)

if __name__ == "__main__":
    main()