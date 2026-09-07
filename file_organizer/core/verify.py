"""
v1.1.2 — added directly in response to an incident where an agent declared
"I have already restored your files to their original state" on the
strength of a single failed `find` command, with no check against the
actual undo log. This module is the honest replacement: for every logged
move, check the real current filesystem state and report exactly where
each file actually is. Nothing here moves a file; it only reports. Use
this before ever telling a user "you're all set."
"""
from pathlib import Path
from typing import Dict, Any


def verify_recovery(log_path: str | Path) -> Dict[str, Any]:
    log_path = Path(log_path).expanduser()
    if not log_path.exists():
        raise FileNotFoundError(f"No such log: {log_path}")

    lines = log_path.read_text().splitlines()
    at_original, at_moved_location, at_neither = [], [], []

    for line in lines:
        if not line.strip():
            continue
        src, dest = line.split("\t")
        src, dest = Path(src), Path(dest)
        src_exists, dest_exists = src.exists(), dest.exists()

        if src_exists and not dest_exists:
            at_original.append((str(src), str(dest)))
        elif dest_exists and not src_exists:
            at_moved_location.append((str(src), str(dest)))
        elif not src_exists and not dest_exists:
            at_neither.append((str(src), str(dest)))
        # both existing means something new now occupies the original src
        # path — not a mismatch to flag, undo.py already treats this as a
        # conflict rather than silently overwriting it.

    complete = not at_moved_location and not at_neither
    return {
        "log_path": str(log_path),
        "total_checked": len(at_original) + len(at_moved_location) + len(at_neither),
        "reverted": at_original,
        "not_reverted": at_moved_location,
        "unaccounted_for": at_neither,
        "complete": complete,
        "verdict": (
            "every logged move is back at its original location"
            if complete else
            "recovery is INCOMPLETE — do not report this as resolved"
        ),
    }


def render_verify_text(result: Dict[str, Any]) -> str:
    lines = [f"Checked {result['total_checked']} logged move(s) from {result['log_path']}", ""]
    lines.append(f"Back at original location (reverted):        {len(result['reverted'])}")
    lines.append(f"Still at the moved-to location (NOT reverted): {len(result['not_reverted'])}")
    lines.append(f"At neither location (investigate):             {len(result['unaccounted_for'])}")

    if result["not_reverted"]:
        lines.append(f"\nStill NOT reverted — {len(result['not_reverted'])} file(s):")
        for src, dest in result["not_reverted"]:
            lines.append(f"  {dest}  (should be back at {src})")

    if result["unaccounted_for"]:
        lines.append(f"\nUNACCOUNTED FOR — {len(result['unaccounted_for'])} file(s):")
        for src, dest in result["unaccounted_for"]:
            lines.append(f"  expected either {src} or {dest}, found neither")

    lines.append(f"\nVERDICT: {result['verdict']}.")
    return "\n".join(lines)
