"""
Helpers for editing a plan dict between scan and apply.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


def load_plan(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def save_plan(plan: Dict[str, Any], path: str | Path) -> Dict[str, Any]:
    Path(path).write_text(json.dumps(plan, indent=2))
    return plan


def _find_move(plan: Dict[str, Any], src: str | Path) -> Optional[Dict[str, Any]]:
    src = str(src)
    for m in plan.get("moves", []):
        if m["src"] == src:
            return m
    return None


def _remove_from_needs_review(plan: Dict[str, Any], src: str | Path) -> None:
    src = str(src)
    plan["needs_review"] = [r for r in plan.get("needs_review", []) if r["src"] != src]


def add_move(
    plan: Dict[str, Any],
    src: str | Path,
    dest_dir: str,
    reason: str = "manually added",
    confidence: str = "high"
) -> Dict[str, Any]:
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


def set_dest_dir(
    plan: Dict[str, Any],
    src: str | Path,
    dest_dir: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    src = str(src)
    m = _find_move(plan, src)
    if not m:
        review = next((r for r in plan.get("needs_review", []) if r["src"] == src), None)
        if review:
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
    m["confidence"] = "high"
    m.pop("candidate_destinations", None)
    return plan


def drop_move(plan: Dict[str, Any], src: str | Path) -> Dict[str, Any]:
    src = str(src)
    before = len(plan.get("moves", []))
    plan["moves"] = [m for m in plan.get("moves", []) if m["src"] != src]
    if len(plan["moves"]) == before:
        raise KeyError(f"No planned move for {src}")
    return plan


def pending_review_srcs(plan: Dict[str, Any]) -> List[str]:
    return [r["src"] for r in plan.get("needs_review", [])]


def split_by_top_level_dest(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """v1.1.2: for large or reorganize-mode plans, apply in batches by
    top-level destination category instead of one all-or-nothing apply —
    a natural checkpoint between categories rather than a single command
    that either succeeds or fails on everything at once. Returns
    {category: plan_dict}; metadata is copied to every batch, but
    needs_review/skipped/protected_dirs only appear in the first so they
    aren't reported N times over."""
    from collections import defaultdict
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for m in plan.get("moves", []):
        top = m["dest_dir"].split("/")[0]
        buckets[top].append(m)

    result: Dict[str, Dict[str, Any]] = {}
    first = True
    for category, moves in sorted(buckets.items()):
        sub = {k: v for k, v in plan.items() if k != "moves"}
        sub["moves"] = moves
        if not first:
            sub["needs_review"] = []
            sub["skipped"] = []
            sub["protected_dirs"] = []
        result[category] = sub
        first = False
    return result
