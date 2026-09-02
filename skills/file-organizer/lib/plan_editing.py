"""
Small helpers for editing a plan.json between scan_and_plan.py and
apply_plan.py — e.g. resolving an ambiguous-image review, swapping a
low-confidence destination for one of its candidate_destinations, or
dropping a proposed move entirely because the user disagreed with it.

Deliberately NOT a class/state machine — plan.json is just a dict on disk,
and these are pure functions that take a plan dict and return a new one.
Load, mutate, save; each call is independent and safe to compose.

Usage:
  from lib.plan_editing import load_plan, save_plan, add_move, set_dest_dir, drop_move

  plan = load_plan("/tmp/organize-plan.json")
  plan = set_dest_dir(plan, "/home/michael/Downloads/vacation_pic.png", "Pictures/People")
  plan = add_move(plan, "/home/michael/Downloads/IMG_random.png", "Downloads/Unsorted", reason="visual review: inconclusive")
  plan = drop_move(plan, "/home/michael/Downloads/track01.mp3")
  save_plan(plan, "/tmp/organize-plan.json")
"""
import json
from pathlib import Path


def load_plan(path):
    return json.loads(Path(path).read_text())


def save_plan(plan, path):
    Path(path).write_text(json.dumps(plan, indent=2))
    return plan


def _find_move(plan, src):
    src = str(src)
    for m in plan.get("moves", []):
        if m["src"] == src:
            return m
    return None


def _remove_from_needs_review(plan, src):
    src = str(src)
    plan["needs_review"] = [r for r in plan.get("needs_review", []) if r["src"] != src]


def add_move(plan, src, dest_dir, reason="manually added", confidence="high"):
    """Add a new move, or overwrite the existing one for the same src.
    Also clears the file out of needs_review if it was sitting there
    (this is how an ambiguous-image review gets resolved: add_move with
    the chosen destination, and the review entry disappears)."""
    src = str(src)
    existing = _find_move(plan, src)
    if existing:
        existing.update({"dest_dir": dest_dir, "reason": reason, "confidence": confidence})
        existing.pop("candidate_destinations", None)
    else:
        plan.setdefault("moves", []).append(
            {"src": src, "action": "move", "dest_dir": dest_dir, "reason": reason, "confidence": confidence}
        )
    _remove_from_needs_review(plan, src)
    return plan


def set_dest_dir(plan, src, dest_dir, reason=None):
    """Change the destination of an already-planned move — e.g. picking one
    of its own candidate_destinations instead of the default guess.

    Looks up in BOTH plan['moves'] and plan['needs_review']: a needs_review
    entry that you redirect to a specific destination is promoted into the
    moves list (rather than raised as a KeyError as it used to). Use
    add_move directly if you want to set a custom confidence/reason.
    """
    src = str(src)
    m = _find_move(plan, src)
    if not m:
        review = next((r for r in plan.get("needs_review", []) if r["src"] == src), None)
        if review:
            # Promote the review entry: convert it to a high-confidence move.
            plan.setdefault("moves", []).append({
                "src": src,
                "action": "move",
                "dest_dir": dest_dir,
                "reason": reason or "resolved from needs_review",
                "confidence": "high",
            })
            _remove_from_needs_review(plan, src)
            return plan
        raise KeyError(
            f"No planned move or review entry for {src} — pass an existing src, "
            "or use add_move to add a fresh entry"
        )
    m["dest_dir"] = dest_dir
    if reason:
        m["reason"] = reason
    m["confidence"] = "high"  # a human/Claude picking a specific destination is a confident choice
    m.pop("candidate_destinations", None)
    return plan


def drop_move(plan, src):
    """Remove a planned move entirely — the file will be left exactly where it is."""
    src = str(src)
    before = len(plan.get("moves", []))
    plan["moves"] = [m for m in plan.get("moves", []) if m["src"] != src]
    if len(plan["moves"]) == before:
        raise KeyError(f"No planned move for {src}")
    return plan


def pending_review_srcs(plan):
    """Convenience: list of src paths still waiting on a visual-review decision."""
    return [r["src"] for r in plan.get("needs_review", [])]
