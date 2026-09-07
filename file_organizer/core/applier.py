"""
Applies a plan produced by the scanner. Moves files safely without overwrite.
Writes append-only undo logs.

v1.1.2: base_dir no longer silently defaults to home. Callers should pass
base_dir=None to have it derived from the plan's own recorded targets
instead — this is the fix for a real incident where a scan of an external
drive, applied with no base specified, moved files onto the OS home
directory because base_dir defaulted to "~" unconditionally. On top of
that, apply_plan() now runs a pre-flight filesystem-boundary check before
moving anything: if a computed destination would land on a different
filesystem/mount than the base, the whole run aborts with nothing moved,
unless allow_cross_filesystem=True.
"""
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List


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


def derive_base_from_targets(plan: Dict[str, Any]) -> Path:
    """v1.1.2: derive the base from the common ancestor of whatever
    directories the scanner actually scanned (plan['targets']), instead of
    defaulting to home. A scan of /media/user/drive/Documents produces a
    base under /media/user/drive, never silently under the OS home
    directory."""
    targets = plan.get("targets", [])
    if not targets:
        return Path("~").expanduser()
    paths = [Path(t).expanduser() for t in targets]
    try:
        common = Path(os.path.commonpath([str(p) for p in paths]))
    except ValueError:
        # Targets span different drives/roots entirely — nothing sane to
        # derive, fall back to home rather than guessing.
        return Path("~").expanduser()
    return common


def filesystem_id(path: Path):
    """Walk up to the nearest existing ancestor and return its device
    identifier (os.stat().st_dev — populated on Windows too, from the
    volume). Used to catch a move that would cross a filesystem/drive
    boundary."""
    p = path
    while not p.exists():
        if p.parent == p:
            return None
        p = p.parent
    try:
        return os.stat(p).st_dev
    except OSError:
        return None


def apply_plan(
    plan: Dict[str, Any],
    base_dir: Optional[str | Path] = None,
    dry_run: bool = False,
    log_dir: str | Path = "~/.file-organizer/logs",
    allow_cross_filesystem: bool = False,
) -> Dict[str, Any]:
    base = Path(base_dir).expanduser() if base_dir else derive_base_from_targets(plan)
    base.mkdir(parents=True, exist_ok=True)
    logs_path = Path(log_dir).expanduser()
    logs_path.mkdir(parents=True, exist_ok=True)

    # Pre-flight filesystem-boundary check, BEFORE any file is touched.
    base_fs = filesystem_id(base)
    if not allow_cross_filesystem and base_fs is not None:
        violations = []
        for m in plan.get("moves", []):
            src = Path(m["src"])
            if not src.exists():
                continue
            src_fs = filesystem_id(src)
            if src_fs is not None and src_fs != base_fs:
                violations.append(str(src))
        if violations:
            return {
                "moved": 0,
                "failed": 0,
                "skipped_noop": 0,
                "dry_run": dry_run,
                "log_path": None,
                "collisions": [],
                "actions": [],
                "aborted": True,
                "abort_reason": (
                    f"{len(violations)} file(s) would move across a filesystem/mount boundary "
                    f"(base resolves to device {base_fs}, these files do not). Nothing was moved. "
                    "Pass allow_cross_filesystem=True if this is actually intended."
                ),
                "cross_filesystem_violations": violations,
            }

    log_file = logs_path / f"moves-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{os.getpid()}.log"
    moved, failed, skipped_noop, protected_skipped = 0, 0, 0, 0
    collisions: List[Tuple[str, str]] = []
    actions: List[Dict[str, str]] = []

    with open(log_file, "a", buffering=1) as log_f:
        for m in plan.get("moves", []):
            src = Path(m["src"])
            if not src.exists():
                actions.append({"src": str(src), "status": "skipped_missing"})
                continue
            if m.get("protected"):
                # v1.1.2: belt-and-suspenders — Integrity Guard entries
                # shouldn't be in the moves list at all, but refuse them
                # here too in case something upstream put one there anyway.
                protected_skipped += 1
                actions.append({"src": str(src), "status": "skipped_protected"})
                continue
            dest_dir = base / m["dest_dir"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            intended_dest = dest_dir / src.name

            if src.resolve() == intended_dest.resolve():
                skipped_noop += 1
                actions.append({"src": str(src), "status": "skipped_noop"})
                continue

            actual_dest = unique_dest(intended_dest)
            if actual_dest != intended_dest:
                collisions.append((str(intended_dest), str(actual_dest)))

            if dry_run:
                actions.append({"src": str(src), "dest": str(actual_dest), "status": "would_move"})
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
                actions.append({"src": str(src), "dest": str(actual_dest), "status": "moved"})
            except Exception as e:
                failed += 1
                actions.append({"src": str(src), "dest": str(actual_dest), "status": "failed", "error": str(e)})

    return {
        "base": str(base),
        "moved": moved,
        "failed": failed,
        "skipped_noop": skipped_noop,
        "protected_skipped": protected_skipped,
        "dry_run": dry_run,
        "log_path": str(log_file),
        "collisions": collisions,
        "actions": actions,
        "aborted": False,
    }
