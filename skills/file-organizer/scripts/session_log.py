#!/usr/bin/env python3
"""
v1.1.3 — the moves log records WHAT moved (src -> dest), but nothing records
WHY: what the user actually asked for, what mode was chosen, what they
confirmed before anything ran. This script writes a structured session log
so that reconstructing an incident is "read this file" instead of "scroll
back through the conversation."

This is intentionally NOT automatic — call it yourself at the start of a
run (what was asked, what mode was picked) and again at the end (outcome,
and exactly what confirmation was given before applying).

Usage:
  python3 session_log.py --event run_started --user-request "organize my Downloads" --mode quick
  python3 session_log.py --event confirmed --confirmation "yes go ahead"
  python3 session_log.py --show
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def log_session(event, log_dir="~/.file-organizer/logs", user_request=None, mode=None,
                 structure_mode=None, targets=None, confirmation=None, plan_summary=None,
                 outcome=None, notes=None):
    log_dir = Path(log_dir).expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    sessions_path = log_dir / "sessions.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "user_request": user_request,
        "mode": mode,
        "structure_mode": structure_mode,
        "targets": targets,
        "confirmation": confirmation,
        "plan_summary": plan_summary,
        "outcome": outcome,
        "notes": notes,
    }
    entry = {k: v for k, v in entry.items() if v is not None}

    with open(sessions_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return sessions_path


def read_sessions(log_dir="~/.file-organizer/logs"):
    sessions_path = Path(log_dir).expanduser() / "sessions.jsonl"
    if not sessions_path.exists():
        return []
    entries = []
    for line in sessions_path.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--event", help="short label: run_started, mode_chosen, plan_built, confirmed, applied, recovery, etc.")
    ap.add_argument("--user-request", help="the user's own request, verbatim or faithfully summarized")
    ap.add_argument("--mode", help="quick / guided / autonomous")
    ap.add_argument("--structure-mode", help="extend / reorganize / fresh-only")
    ap.add_argument("--targets", nargs="*", help="directories involved in this run")
    ap.add_argument("--confirmation", help="what the user actually said to approve this action")
    ap.add_argument("--notes", help="anything else worth recording")
    ap.add_argument("--log-dir", default="~/.file-organizer/logs")
    ap.add_argument("--show", action="store_true", help="print the recorded session log instead of writing an entry")
    args = ap.parse_args()

    if args.show:
        for e in read_sessions(args.log_dir):
            print(json.dumps(e, indent=2))
        return

    if not args.event:
        print("ERROR: --event is required unless using --show", file=sys.stderr)
        sys.exit(1)

    path = log_session(
        event=args.event, log_dir=args.log_dir, user_request=args.user_request,
        mode=args.mode, structure_mode=args.structure_mode, targets=args.targets,
        confirmation=args.confirmation, notes=args.notes,
    )
    print(f"Logged to {path}")


if __name__ == "__main__":
    main()
