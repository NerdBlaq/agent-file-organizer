"""
Undo engine for reversing moves recorded in moves-*.log files.
"""
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def parse_log_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    first_tab = line.find("\t")
    if first_tab < 0:
        return None, None
    src = line[:first_tab]
    dest = line[first_tab + 1:]
    return src, dest


def plan_reversal(
    lines: List[str],
    limit: Optional[int] = None
) -> Tuple[List[Tuple[Path, Path]], List[Tuple[Path, Path, str]], List[Tuple[Path, Path, str]]]:
    if limit is not None:
        valid_lines: List[str] = []
        for line in reversed(lines):
            if line.strip():
                valid_lines.append(line)
                if len(valid_lines) >= limit:
                    break
        lines_to_process = list(reversed(valid_lines))
    else:
        lines_to_process = list(reversed(lines))

    to_revert: List[Tuple[Path, Path]] = []
    conflicts: List[Tuple[Path, Path, str]] = []
    already_gone: List[Tuple[Path, Path, str]] = []

    for line in lines_to_process:
        if not line.strip():
            continue
        src_str, dest_str = parse_log_line(line)
        if src_str is None or dest_str is None:
            continue
        src, dest = Path(src_str), Path(dest_str)
        if not dest.exists():
            already_gone.append((src, dest, "destination no longer exists"))
            continue
        if src.exists():
            conflicts.append((src, dest, "original location is occupied again — won't overwrite"))
            continue
        to_revert.append((src, dest))
    return to_revert, conflicts, already_gone


def execute_undo(
    log_path: str | Path,
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    path = Path(log_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Log file does not exist: {path}")

    lines = path.read_text().splitlines()
    to_revert, conflicts, already_gone = plan_reversal(lines, limit=limit)

    reverted = 0
    if not dry_run:
        for src, dest in to_revert:
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest), str(src))
            reverted += 1

    return {
        "log_path": str(path),
        "dry_run": dry_run,
        "total_lines": len(lines),
        "reverted_count": reverted if not dry_run else len(to_revert),
        "to_revert": [(str(src), str(dest)) for src, dest in to_revert],
        "conflicts": [(str(src), str(dest), reason) for src, dest, reason in conflicts],
        "already_gone": [(str(src), str(dest), reason) for src, dest, reason in already_gone],
    }
