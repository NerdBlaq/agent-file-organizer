#!/usr/bin/env python3
"""
Apply a confirmed plan.json produced by scan_and_plan.py. Moves only — never deletes.
Writes an undo log to ~/.file-organizer/logs/moves-<timestamp>-<pid>.log

v1.1.2: --base no longer silently defaults to home. If not given explicitly,
it's derived from the plan's own recorded 'targets' field instead — the fix
for a real incident where a scan of an external drive, applied with no
--base, moved files onto the OS home directory. On top of that, every move
is checked against a filesystem-boundary guard before anything moves: if a
computed destination would land on a different filesystem/mount than the
base, the run aborts before touching any file, unless
--allow-cross-filesystem is passed.

Usage:
  python3 apply_plan.py --plan /tmp/organize-plan.json                  # base auto-derived from plan targets
  python3 apply_plan.py --plan /tmp/organize-plan.json --base ~/Downloads
  python3 apply_plan.py --plan /tmp/organize-plan.json --dry-run
  python3 apply_plan.py --plan /tmp/organize-plan.json --allow-cross-filesystem
"""
import argparse
import json
import os
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


def derive_base_from_targets(plan) -> Path:
    """v1.1.2: derive the base from the common ancestor of whatever
    directories scan_and_plan.py actually scanned (plan['targets']),
    instead of defaulting to home."""
    targets = plan.get("targets", [])
    if not targets:
        return Path("~").expanduser()
    paths = [Path(t).expanduser() for t in targets]
    try:
        common = Path(os.path.commonpath([str(p) for p in paths]))
    except ValueError:
        return Path("~").expanduser()
    return common


def filesystem_id(path: Path):
    """Walk up to the nearest existing ancestor and return its device id
    (os.stat().st_dev). Used to catch a move that would cross a
    filesystem/mount boundary."""
    p = path
    while not p.exists():
        if p.parent == p:
            return None
        p = p.parent
    try:
        return os.stat(p).st_dev
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, help="Path to plan.json (after any review merges)")
    ap.add_argument("--base", default=None,
                     help="Base directory that dest_dir entries are relative to. If omitted, derived from "
                          "the plan's own 'targets' field instead of defaulting to home (v1.1.2).")
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen without touching files")
    ap.add_argument("--allow-cross-filesystem", action="store_true",
                     help="Permit moves whose destination resolves onto a different filesystem/mount than "
                          "the base. Off by default — this is exactly the failure mode from a real incident "
                          "where files were moved from an external drive onto the OS partition unintentionally.")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text())
    base = Path(args.base).expanduser() if args.base else derive_base_from_targets(plan)
    base.mkdir(parents=True, exist_ok=True)

    # Pre-flight filesystem-boundary check, BEFORE any file is touched.
    base_fs = filesystem_id(base)
    if not args.allow_cross_filesystem and base_fs is not None:
        violations = []
        for m in plan.get("moves", []):
            src = Path(m["src"])
            if not src.exists():
                continue
            src_fs = filesystem_id(src)
            if src_fs is not None and src_fs != base_fs:
                violations.append(str(src))
        if violations:
            print(f"ABORTED before moving anything: {len(violations)} file(s) would move across a "
                  f"filesystem/mount boundary (base is on device {base_fs}, these are not):", file=sys.stderr)
            for v in violations[:10]:
                print(f"  {v}", file=sys.stderr)
            if len(violations) > 10:
                print(f"  ... and {len(violations) - 10} more", file=sys.stderr)
            print("If this is actually intended, rerun with --allow-cross-filesystem.", file=sys.stderr)
            sys.exit(1)

    log_dir = Path("~/.file-organizer/logs").expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"moves-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{os.getpid()}.log"

    moved, failed, skipped_noop, protected_skipped = 0, 0, 0, 0
    with open(log_path, "a", buffering=1) as log_f:
        for m in plan.get("moves", []):
            src = Path(m["src"])
            if not src.exists():
                print(f"SKIP (missing): {src}", file=sys.stderr)
                continue
            if m.get("protected"):
                print(f"SKIP (protected package directory, not moving): {src}", file=sys.stderr)
                protected_skipped += 1
                continue
            dest_dir = base / m["dest_dir"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            intended_dest = dest_dir / src.name

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
                log_f.write(f"{src}\t{actual_dest}\n")
                log_f.flush()
                try:
                    os.fsync(log_f.fileno())
                except OSError:
                    pass
                moved += 1
            except Exception as e:
                print(f"FAILED to move {src} -> {actual_dest}: {e}", file=sys.stderr)
                failed += 1

    print(f"Base: {base}")
    if args.dry_run:
        print(f"--dry-run: no files moved. Log path would be: {log_path}")
    else:
        print(f"Moved {moved} file(s), {failed} failure(s), {skipped_noop} no-op(s), {protected_skipped} protected-directory item(s) skipped.")
        print(f"Undo log: {log_path}")
        print(f"Reverse with: python3 undo.py {log_path}   (add --dry-run to preview)")


if __name__ == "__main__":
    main()
