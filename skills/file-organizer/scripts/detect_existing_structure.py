#!/usr/bin/env python3
"""
Detect whether a directory already has an organizational scheme (by year,
already matches this skill's default taxonomy, a custom user-made scheme,
or genuinely flat/unsorted) before any plan is built. This exists so the
skill can *extend* what the user already has instead of creating a parallel,
redundant folder structure next to it.

Usage:
  python3 detect_existing_structure.py --targets ~/Pictures ~/Videos ~/Music --output /tmp/structure.json
"""
import argparse
import json
import re
from pathlib import Path

YEAR_RE = re.compile(r"^(19|20)\d{2}$")

# Leaf names this skill's own default taxonomy would create — if the user's
# existing folders already match these, there's nothing to reconcile.
DEFAULT_CLUSTER_LEAF_NAMES = {
    "screenshots", "camera", "people", "unsorted", "receipts",
    "movies", "clips", "screen recordings", "installers", "archives",
    "disk images", "diskimages", "fonts", "code",
}


def scan_directory(path: Path):
    if not path.exists() or not path.is_dir():
        return None
    subdirs = [p.name for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")]
    loose_files = [p.name for p in path.iterdir() if p.is_file() and not p.name.startswith(".")]
    nested_file_count = 0
    # Per-subdir shape. The original version collapsed to a single label and
    # lost information: a Music/<Artist>/ folder that holds BOTH loose tracks
    # AND an Albums/ subfolder is genuinely "mixed", not just "flat" — and
    # the planner needs to know that to decide whether to add Unknown Album
    # next to existing tracks. Five shapes now:
    #   flat       — only loose files at this level
    #   nested     — only child dirs at this level (e.g. Albums/, Singles/)
    #   mixed      — both loose files and child dirs coexist
    #   empty      — no loose files and no child dirs yet (a brand-new
    #                folder the user just made; planner shouldn't add a
    #                layer the user didn't ask for)
    #   unknown    — couldn't read it (permissions)
    subdir_shapes = {}
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


def classify_scheme(subdirs):
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--targets", nargs="+", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    report = {"directories": {}}
    any_existing_structure = False

    for t in args.targets:
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

    out_path = Path(args.output)
    out_path.write_text(json.dumps(report, indent=2))

    md_lines = ["# Existing structure report", ""]
    if not any_existing_structure:
        md_lines.append("No existing organization detected in any target directory. Nothing to reconcile.")
    for dir_path, d in report["directories"].items():
        md_lines.append(f"## {dir_path}")
        md_lines.append(f"- Scheme: **{d['scheme']}**")
        md_lines.append(f"- Existing subfolders: {', '.join(d['subdirs']) or '(none)'}")
        md_lines.append(f"- Loose files at top level: {d['loose_file_count']}")
        md_lines.append(f"- Files already inside subfolders: {d['nested_file_count']}")
        md_lines.append(f"- {d['recommendation']}")
        md_lines.append("")

    out_path.with_suffix(".md").write_text("\n".join(md_lines))
    print(f"Structure report written to {out_path} and {out_path.with_suffix('.md')}")
    print(f"Existing organization found: {any_existing_structure}")


if __name__ == "__main__":
    main()
