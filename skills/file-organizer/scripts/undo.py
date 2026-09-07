#!/usr/bin/env python3
"""
Reverse a moves log written by apply_plan.py.

Usage:
  python3 undo.py ~/.file-organizer/logs/moves-20260814-093000.log            # preview, then apply
  python3 undo.py ~/.file-organizer/logs/moves-20260814-093000.log --dry-run  # preview only
  python3 undo.py ~/.file-organizer/logs/moves-20260814-093000.log --limit 5 # reverse only the last 5 moves
"""
import argparse
import os
import shutil
import sys
from pathlib import Path


def parse_log_line(line):
    """Split a 'src\tdest' log line into (src, dest)."""
    first_tab = line.find("\t")
    if first_tab < 0:
        return None, None
    src = line[:first_tab]
    dest = line[first_tab + 1:]
    return src, dest


def plan_reversal(lines, limit=None):
    """Return (to_revert, conflicts, already_gone) without touching the filesystem."""
    if limit is not None:
        valid_lines = []
        for line in reversed(lines):
            if line.strip():
                valid_lines.append(line)
                if len(valid_lines) >= limit:
                    break
        lines_to_process = list(reversed(valid_lines))
    else:
        lines_to_process = list(reversed(lines))

    to_revert, conflicts, already_gone = [], [], []
    for line in lines_to_process:
        if not line.strip():
            continue
        src_str, dest_str = parse_log_line(line)
        if src_str is None or dest_str is None:
            print(f"WARNING: malformed log line, skipping: {line!r}", file=sys.stderr)
            continue
        src, dest = Path(src_str), Path(dest_str)
        if not dest.exists():
            already_gone.append((src, dest, "destination no longer exists — already moved, renamed, or deleted since"))
            continue
        if src.exists():
            conflicts.append((src, dest, "original location is occupied again — won't overwrite"))
            continue
        to_revert.append((src, dest))
    return to_revert, conflicts, already_gone


def print_plan(to_revert, conflicts, already_gone):
    print(f"Would revert {len(to_revert)} file(s):")
    for src, dest in to_revert:
        print(f"  {dest}  ->  {src}")
    if conflicts:
        print(f"\n{len(conflicts)} conflict(s) — original location occupied again, will be left alone:")
        for src, dest, reason in conflicts:
            print(f"  {dest} -/-> {src}  ({reason})")
    if already_gone:
        print(f"\n{len(already_gone)} entr(y/ies) skipped — nothing to undo:")
        for src, dest, reason in already_gone:
            print(f"  {dest}  ({reason})")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log_path")
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen and stop — don't move anything")
    ap.add_argument("--limit", type=int, default=None, help="Only revert the last N moves from this log (most recent first). Useful for partial undo.")
    ap.add_argument("--yes", "-y", action="store_true", help="Skip the confirmation prompt before actually reversing (the dry-run summary still prints)")
    args = ap.parse_args()

    log_path = Path(args.log_path)
    if not log_path.exists():
        print(f"ERROR: log file does not exist: {log_path}", file=sys.stderr)
        sys.exit(1)

    try:
        st = log_path.stat()
        total_lines = sum(1 for _ in log_path.read_text().splitlines())
    except OSError as e:
        print(f"ERROR: cannot read log file: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Log: {log_path}")
    print(f"  size: {st.st_size} bytes")
    print(f"  modified: {st.st_mtime} ({datetime_local(st.st_mtime)})")
    print(f"  total move entries: {total_lines}")
    if args.limit:
        print(f"  limit: only the last {args.limit} entr(y/ies) will be considered")
    print()

    lines = log_path.read_text().splitlines()
    to_revert, conflicts, already_gone = plan_reversal(lines, limit=args.limit)
    print_plan(to_revert, conflicts, already_gone)

    if args.dry_run:
        print("\n--dry-run: nothing was moved.")
        return

    if not to_revert:
        print("\nNothing to revert.")
        return

    if not args.yes:
        print()
        resp = input(f"Reverse {len(to_revert)} file(s)? [y/N] ")
        if resp.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return

    reverted = 0
    for src, dest in to_revert:
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest), str(src))
        reverted += 1

    print(f"Reverted {reverted} file(s), {len(conflicts)} conflict(s) left in place.")


def datetime_local(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts).isoformat()


if __name__ == "__main__":
    main()
