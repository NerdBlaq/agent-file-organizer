"""
Structure detection to identify existing organizational schemes (by year,
default taxonomy, custom schemes, or flat) before planning.
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from file_organizer.taxonomy import YEAR_RE, DEFAULT_CLUSTER_LEAF_NAMES

RECOMMENDATION = {
    "flat": "No existing structure here — nothing to reconcile, proceed straight to the standard plan.",
    "by-year": (
        "Already organized by year. Recommend EXTEND mode: new photos with a "
        "matching capture year should land in the existing year folder (creating "
        "new year folders as needed) rather than a separate 'Camera' folder."
    ),
    "matches-default-taxonomy": (
        "Existing folders already match this skill's own default names. "
        "EXTEND mode will just naturally add to them — no conflict to resolve."
    ),
    "custom": (
        "User has their own naming scheme that doesn't match year-based or "
        "default patterns (e.g. event/trip names, project names). Auto-mapping "
        "isn't reliable here — surface these folder names during ambiguous-item "
        "review so matches can be made by hand, and ask the user directly "
        "whether to EXTEND (fold new files in around this scheme, leaving it "
        "otherwise untouched) or REORGANIZE (replace it with the default/"
        "guided taxonomy — this moves files that already had a home, so it "
        "needs explicit confirmation, not just a default 'yes')."
    ),
}


def scan_directory(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists() or not path.is_dir():
        return None
    subdirs = [p.name for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")]
    loose_files = [p.name for p in path.iterdir() if p.is_file() and not p.name.startswith(".")]
    nested_file_count = 0
    subdir_shapes: Dict[str, str] = {}
    for sd in subdirs:
        sd_path = path / sd
        try:
            has_loose_files = any(p.is_file() for p in sd_path.iterdir())
            has_child_dirs = any(p.is_dir() and not p.name.startswith(".") for p in sd_path.iterdir())
            if has_loose_files and has_child_dirs:
                shape = "mixed"
            elif has_loose_files:
                shape = "flat"
            elif has_child_dirs:
                shape = "nested"
            else:
                shape = "empty"
            subdir_shapes[sd] = shape
            nested_file_count += sum(1 for _ in sd_path.rglob("*") if _.is_file())
        except PermissionError:
            subdir_shapes[sd] = "unknown"
    return {
        "subdirs": sorted(subdirs),
        "subdir_shapes": subdir_shapes,
        "loose_file_count": len(loose_files),
        "nested_file_count": nested_file_count,
    }


def classify_scheme(subdirs: List[str]) -> Tuple[str, Dict[str, Any]]:
    if not subdirs:
        return "flat", {}

    year_like = [d for d in subdirs if YEAR_RE.match(d)]
    default_like = [d for d in subdirs if d.lower() in DEFAULT_CLUSTER_LEAF_NAMES]

    threshold = max(1, round(len(subdirs) * 0.6))
    if len(year_like) >= threshold:
        return "by-year", {"year_folders": sorted(year_like)}
    if len(default_like) >= threshold:
        return "matches-default-taxonomy", {"matched": sorted(default_like)}
    return "custom", {"names": sorted(subdirs)}


def detect_structure(targets: List[str | Path]) -> Dict[str, Any]:
    report: Dict[str, Any] = {"directories": {}}
    any_existing_structure = False

    for t in targets:
        path = Path(t).expanduser()
        info = scan_directory(path)
        if info is None:
            continue
        scheme, detail = classify_scheme(info["subdirs"])
        if scheme != "flat":
            any_existing_structure = True
        report["directories"][str(path)] = {
            "root_name": path.name,
            "scheme": scheme,
            "detail": detail,
            "subdirs": info["subdirs"],
            "subdir_shapes": info["subdir_shapes"],
            "loose_file_count": info["loose_file_count"],
            "nested_file_count": info["nested_file_count"],
            "recommendation": RECOMMENDATION[scheme],
        }

    report["any_existing_structure"] = any_existing_structure
    return report


def render_structure_markdown(report: Dict[str, Any]) -> str:
    md_lines = ["# Existing structure report", ""]
    if not report.get("any_existing_structure"):
        md_lines.append("No existing organization detected in any target directory. Nothing to reconcile.")
    for dir_path, d in report.get("directories", {}).items():
        md_lines.append(f"## {dir_path}")
        md_lines.append(f"- Scheme: **{d['scheme']}**")
        md_lines.append(f"- Existing subfolders: {', '.join(d['subdirs']) or '(none)'}")
        md_lines.append(f"- Loose files at top level: {d['loose_file_count']}")
        md_lines.append(f"- Files already inside subfolders: {d['nested_file_count']}")
        md_lines.append(f"- {d['recommendation']}")
        md_lines.append("")
    return "\n".join(md_lines)
