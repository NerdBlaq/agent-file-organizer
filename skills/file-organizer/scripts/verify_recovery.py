#!/usr/bin/env python3
"""
v1.1.2 — added directly in response to an incident where an agent declared
"I have already restored your files to their original state" on the
strength of a single failed `find` command, with no check against the
actual undo log. This script is the honest replacement: for every logged
move, check the real current filesystem state and report exactly where
each file actually is — reverted, not yet reverted, or neither (something
else happened to it since). Nothing here moves a file; it only reports.
Use this before ever telling a user "you're all set."

Usage:
  python3 verify_recovery.py ~/.file-organizer/logs/moves-20260904-045731-123456-789.log
"""
import argparse
import sys
from pathlib import Path


def verify(log_path: Path):
    lines = log_path.read_text().splitlines()
    at_original, at_moved_location, at_neither = [], [], []

    for line in lines:
        if not line.strip():
            continue
        src, dest = line.split("\t")
        src, dest = Path(src), Path(dest)
        src_exists, dest_exists = src.exists(), dest.exists()

        if src_exists and not dest_exists:
            at_original.append((src, dest))
        elif dest_exists and not src_exists:
            at_moved_location.append((src, dest))
        elif not src_exists and not dest_exists:
            at_neither.append((src, dest))

    return at_original, at_moved_location, at_neither


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log_path")
    args = ap.parse_args()

    log_path = Path(args.log_path).expanduser()
    if not log_path.exists():
        print(f"No such log: {log_path}", file=sys.stderr)
        sys.exit(1)

    at_original, at_moved_location, at_neither = verify(log_path)
    total = len(at_original) + len(at_moved_location) + len(at_neither)

    print(f"Checked {total} logged move(s) from {log_path}\n")
    print(f"Back at original location (reverted):        {len(at_original)}")
    print(f"Still at the moved-to location (NOT reverted): {len(at_moved_location)}")
    print(f"At neither location (moved/renamed/deleted since — investigate): {len(at_neither)}")

    if at_moved_location:
        print(f"\nStill NOT reverted — {len(at_moved_location)} file(s):")
        for src, dest in at_moved_location:
            print(f"  {dest}  (should be back at {src})")

    if at_neither:
        print(f"\nUNACCOUNTED FOR — {len(at_neither)} file(s), do not report this as 'restored':")
        for src, dest in at_neither:
            print(f"  expected either {src} or {dest}, found neither")

    if at_moved_location or at_neither:
        print("\nVERDICT: recovery is INCOMPLETE. Do not tell the user this is resolved.")
        sys.exit(1)
    else:
        print("\nVERDICT: every logged move for this file is back at its original location.")


if __name__ == "__main__":
    main()
