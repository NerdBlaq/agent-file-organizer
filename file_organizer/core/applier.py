"""
Applies a plan produced by the scanner. Moves files safely without overwrite.
Writes append-only undo logs.
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


def apply_plan(
    plan: Dict[str, Any],
    base_dir: str | Path = "~",
    dry_run: bool = False,
    log_dir: str | Path = "~/.file-organizer/logs"
) -> Dict[str, Any]:
    base = Path(base_dir).expanduser()
    logs_path = Path(log_dir).expanduser()
    logs_path.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_path / f"moves-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{os.getpid()}.log"
    moved, failed, skipped_noop = 0, 0, 0
    collisions: List[Tuple[str, str]] = []
    actions: List[Dict[str, str]] = []

    with open(log_file, "a", buffering=1) as log_f:
        for m in plan.get("moves", []):
            src = Path(m["src"])
            if not src.exists():
                actions.append({"src": str(src), "status": "skipped_missing"})
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
        "moved": moved,
        "failed": failed,
        "skipped_noop": skipped_noop,
        "dry_run": dry_run,
        "log_path": str(log_file),
        "collisions": collisions,
        "actions": actions,
    }
