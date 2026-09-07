"""
v1.1.3 — the moves log records WHAT moved (src -> dest), but nothing records
WHY: what the user actually asked for, what mode was chosen, what they
confirmed before anything ran. Every incident review in this project's
history has had to be reconstructed by hand from chat transcripts and
screenshots. This module is a structured session log the calling agent
writes to directly, so that reconstruction becomes "read this file" instead
of "scroll back through the conversation."

This is intentionally NOT automatic — the scripts have no access to "the
conversation," only the calling agent does. The agent is expected to call
log_session() (or the CLI/MCP wrappers) at the start of a run (recording
what was asked and what mode was picked) and again at the end (recording
the outcome and exactly what confirmation was given before applying).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


def log_session(
    event: str,
    log_dir: str | Path = "~/.file-organizer/logs",
    user_request: Optional[str] = None,
    mode: Optional[str] = None,
    structure_mode: Optional[str] = None,
    targets: Optional[List[str]] = None,
    confirmation: Optional[str] = None,
    plan_summary: Optional[Dict[str, Any]] = None,
    outcome: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> Path:
    """Append one structured entry to sessions.jsonl. Every field beyond
    `event` is optional — call this at whatever points make sense (request
    received, mode chosen, plan built, confirmation received, applied,
    recovered), filling in only what's relevant to that point in the run.

    event: a short label for what this entry records, e.g. "run_started",
        "mode_chosen", "plan_built", "confirmed", "applied", "recovery".
    user_request: the user's own words, or a faithful summary of them —
        not a paraphrase that loses what they actually asked for.
    confirmation: what the user actually said to approve an action, verbatim
        where practical — "looks good", "yes reorganize the games folder too",
        etc. This is the field an incident review most needs and most often
        doesn't have.
    """
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


def read_sessions(log_dir: str | Path = "~/.file-organizer/logs") -> List[Dict[str, Any]]:
    """Read back all session entries, oldest first. Returns [] if no
    session log exists yet rather than raising — a fresh install has no
    history and that's not an error."""
    sessions_path = Path(log_dir).expanduser() / "sessions.jsonl"
    if not sessions_path.exists():
        return []
    entries = []
    for line in sessions_path.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries
