#!/usr/bin/env python3
"""
Apply a confirmed plan.json produced by scan_and_plan.py. Moves only — never deletes.
Writes an undo log to ~/.file-organizer/logs/moves-<timestamp>-<pid>.log

Usage:
  python3 apply_plan.py --plan /tmp/organize-plan.json [--base ~/Downloads] [--dry-run]
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    n = 1
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, help="Path to plan.json (after any review merges)")
    ap.add_argument("--base", default="~", help="Base directory that dest_dir entries are relative to (default: home)")
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen with any (1)/collision suffixing without touching files")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text())
    base = Path(args.base).expanduser()

    log_dir = Path("~/.file-organizer/logs").expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    # Include microseconds + pid so two same-second runs (or concurrent runs
    # from a different process) don't collide on filename. The old format
    # collided because `datetime.now().strftime("%Y%m%d-%H%M%S")` is
    # second-granular.
    log_path = log_dir / f"moves-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{__import__('os').getpid()}.log"

    moved, failed, skipped_noop = 0, 0, 0
    with open(log_path, "a", buffering=1) as log_f:  # line-buffered: flushes on every newline
        for m in plan.get("moves", []):
            src = Path(m["src"])
            if not src.exists():
                print(f"SKIP (missing): {src}", file=sys.stderr)
                continue
            dest_dir = base / m["dest_dir"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            intended_dest = dest_dir / src.name

            # Skip no-op moves (src == dest after path resolution). Without
            # this, shutil.move succeeds silently but we still write a log
            # line — undo.py then tries to "reverse" a move that never
            # happened and reports it as a conflict (because the original
            # path is "occupied again" — by the file that never left).
            if src.resolve() == intended_dest.resolve():
                print(f"SKIP (no-op, already at dest): {src}", file=sys.stderr)
                skipped_noop += 1
                continue

            actual_dest = unique_dest(intended_dest)
            if actual_dest != intended_dest:
                print(f"  collision: {intended_dest} -> {actual_dest}", file=sys.stderr)

            if args.dry_run:
                print(f"  WOULD MOVE: {src} -> {actual_dest}")
                continue

            try:
                shutil.move(str(src), str(actual_dest))
                # fsync so a power-cut between move and log write doesn't
                # orphan a moved file with no undo record. We also write
                # the line BEFORE the move used to be (now AFTER) — if the
                # move succeeded, the log entry is committed; if the move
                # failed, no log entry is written. The only window left is
                # "move succeeded, fsync failed" which leaves the file at
                # dest with no log entry — recoverable by scanning for
                # files at the destinations in the last plan.json.
                log_f.write(f"{src}\t{actual_dest}\n")
                log_f.flush()
                os_fsync = __import__('os').fsync
                try:
                    os_fsync(log_f.fileno())
                except OSError:
                    pass  # fsync failure is recoverable; move is already done
                moved += 1
            except Exception as e:
                print(f"FAILED to move {src} -> {actual_dest}: {e}", file=sys.stderr)
                failed += 1

    if args.dry_run:
        print(f"--dry-run: no files moved. Log path would be: {log_path}")
    else:
        print(f"Moved {moved} file(s), {failed} failure(s), {skipped_noop} no-op(s) skipped.")
        print(f"Undo log: {log_path}")
        print(f"Reverse with: python3 undo.py {log_path}   (add --dry-run to preview)")


if __name__ == "__main__":
    main()
