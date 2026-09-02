"""
Core file scanning and classification engine. Builds dry-run move plans.
"""
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

try:
    from PIL import Image  # type: ignore
    from PIL.ExifTags import TAGS  # type: ignore
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

try:
    import mutagen  # type: ignore
    HAVE_MUTAGEN = True
except ImportError:
    HAVE_MUTAGEN = False

from file_organizer.taxonomy import (
    EXT_BUCKETS,
    EXT_TO_BUCKET,
    SCREENSHOT_NAME_RE,
    SCREEN_RECORDING_NAME_RE,
    IN_PROGRESS_RE,
    RECEIPT_NAME_RE,
    MOD_JAR_RE,
    CANDIDATE_DESTINATIONS,
)


def load_config(path: Optional[str | Path]) -> Dict[str, Any]:
    if not path:
        return {}
    if yaml is None:
        print(f"WARNING: pyyaml not installed, ignoring config {path}", file=sys.stderr)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def is_locked_or_in_progress(path: Path) -> bool:
    return bool(IN_PROGRESS_RE.search(path.name))


def read_exif_signal(path: Path) -> Tuple[bool, Optional[str]]:
    if not HAVE_PIL:
        return False, None
    try:
        img = Image.open(path)
        exif = img.getexif()
        if not exif:
            return False, None
        tags = {TAGS.get(k, k): v for k, v in exif.items()}
        has_signal = bool(tags.get("Make") or tags.get("Model") or tags.get("DateTimeOriginal"))
        year = None
        dt = tags.get("DateTimeOriginal")
        if isinstance(dt, str) and len(dt) >= 10 and dt[:4].isdigit() and dt[4:5] == ":":
            year_candidate = dt[:4]
            if 1900 <= int(year_candidate) <= 2100:
                year = year_candidate
        return has_signal, year
    except Exception:
        return False, None


def read_audio_tags(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if HAVE_MUTAGEN:
        try:
            f = mutagen.File(path, easy=True)
            if f:
                artist = (f.get("artist") or [None])[0]
                album = (f.get("album") or [None])[0]
                if artist:
                    return artist, album
        except Exception:
            pass
    # Fallback: "Artist - Title.ext"
    m = re.match(r"^(?P<artist>.+?)\s*-\s*(?P<title>.+)$", path.stem)
    if m:
        return m.group("artist").strip(), None
    return None, None


def match_custom_clusters(path: Path, custom_clusters: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    name_lower = path.name.lower()
    ext = path.suffix.lower().lstrip(".")
    for rule in custom_clusters or []:
        for substr in rule.get("match_filename_contains", []) or []:
            if substr.lower() in name_lower:
                return rule["name"]
        for e in rule.get("match_extension", []) or []:
            if ext == e.lower():
                return rule["name"]
    return None


def load_prior_run_destinations(log_dir: Path) -> Set[str]:
    destinations: Set[str] = set()
    if not log_dir.exists():
        return destinations
    for log_file in log_dir.glob("moves-*.log"):
        try:
            raw = log_file.read_text()
        except OSError:
            continue
        for line_no, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            first_tab = line.find("\t")
            if first_tab < 0:
                continue
            second_tab = line.find("\t", first_tab + 1)
            if second_tab < 0:
                continue
            dest = line[second_tab + 1:]
            destinations.add(dest)
    return destinations


def classify(
    path: Path,
    config: Dict[str, Any],
    ambiguous_budget: Dict[str, int],
    all_schemes: Optional[Dict[str, Any]] = None,
    prior_run_destinations: Optional[Set[str]] = None,
    from_target: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    if path.name.startswith("."):
        return None

    def _with_from_target(move_dict: Dict[str, Any]) -> Dict[str, Any]:
        if from_target is not None:
            move_dict["from_target"] = str(from_target)
        return move_dict

    if prior_run_destinations and str(path) in prior_run_destinations:
        return _with_from_target({"src": str(path), "action": "skip", "reason": "already placed here by a previous run (see undo log)"})
    if is_locked_or_in_progress(path):
        return _with_from_target({"src": str(path), "action": "skip", "reason": "in-progress or lock-like file"})

    custom = match_custom_clusters(path, config.get("custom_clusters"))
    if custom:
        return _with_from_target({"src": str(path), "action": "move", "dest_dir": custom, "reason": "custom cluster rule match", "confidence": "high"})

    ext = path.suffix.lower().lstrip(".")
    bucket = EXT_TO_BUCKET.get(ext)
    all_schemes = all_schemes or {}
    pictures_scheme = all_schemes.get("pictures", {})
    scheme = pictures_scheme.get("scheme")
    scheme_detail = pictures_scheme.get("detail", {})

    if bucket == "Pictures":
        if SCREENSHOT_NAME_RE.search(path.name):
            existing_name = None
            for n in scheme_detail.get("names", []) or scheme_detail.get("matched", []) or []:
                if n.lower() == "screenshots":
                    existing_name = n
                    break
            if existing_name:
                return _with_from_target({"src": str(path), "action": "move", "dest_dir": f"Pictures/{existing_name}", "reason": "filename matches screenshot pattern; reusing existing folder", "confidence": "high"})
            return _with_from_target({"src": str(path), "action": "move", "dest_dir": "Pictures/Screenshots", "reason": "filename matches screenshot pattern", "confidence": "high"})
        
        has_camera_signal, year = read_exif_signal(path)
        if has_camera_signal:
            if scheme == "by-year" and year:
                return _with_from_target({"src": str(path), "action": "move", "dest_dir": f"Pictures/{year}", "reason": "EXIF year matches existing by-year organization; extending that scheme", "confidence": "high"})
            existing_camera_name = None
            for n in scheme_detail.get("names", []) or scheme_detail.get("matched", []) or []:
                if n.lower() == "camera":
                    existing_camera_name = n
                    break
            if existing_camera_name:
                base = f"Pictures/{existing_camera_name}"
                if config.get("camera_photos_by_year") and year:
                    return _with_from_target({"src": str(path), "action": "move", "dest_dir": f"{base}/{year}", "reason": "EXIF camera/date signal; reusing existing camera folder", "confidence": "high"})
                return _with_from_target({"src": str(path), "action": "move", "dest_dir": base, "reason": "EXIF camera/date signal; reusing existing camera folder", "confidence": "high"})
            dest = "Pictures/Camera"
            if config.get("camera_photos_by_year") and year:
                dest = f"Pictures/Camera/{year}"
            return _with_from_target({"src": str(path), "action": "move", "dest_dir": dest, "reason": "EXIF camera/date signal present", "confidence": "high"})
        
        if RECEIPT_NAME_RE.search(path.name):
            return _with_from_target({
                "src": str(path), "action": "move", "dest_dir": "Documents/Receipts",
                "reason": "filename matches receipt/invoice pattern", "confidence": "medium",
                "candidate_destinations": CANDIDATE_DESTINATIONS["receipt-in-pictures"]
            })
        
        ambiguous_budget["total_seen"] = ambiguous_budget.get("total_seen", 0) + 1
        if ambiguous_budget.get("remaining", 0) > 0:
            ambiguous_budget["remaining"] -= 1
            reason = "image with no EXIF/filename signal; needs visual review"
            if scheme == "custom" and scheme_detail.get("names"):
                reason += f"; existing custom folders here that might be a better fit: {', '.join(scheme_detail['names'])}"
            return _with_from_target({"src": str(path), "action": "review", "reason": reason})
        
        default_dest = config.get("ambiguous_photo_default", "Downloads/Unsorted")
        candidates = [default_dest, "Pictures/People", "Pictures/Camera"]
        return _with_from_target({
            "src": str(path), "action": "move", "dest_dir": default_dest,
            "reason": "ambiguous and review cap reached; left per ambiguous_photo_default", "confidence": "low",
            "candidate_destinations": candidates
        })

    if bucket == "Videos":
        if SCREEN_RECORDING_NAME_RE.search(path.name):
            return _with_from_target({"src": str(path), "action": "move", "dest_dir": "Videos/Screen Recordings", "reason": "filename matches screen-recording pattern", "confidence": "high"})
        return _with_from_target({
            "src": str(path), "action": "move", "dest_dir": "Videos",
            "reason": "video extension, no finer signal available", "confidence": "medium",
            "candidate_destinations": CANDIDATE_DESTINATIONS["video-no-signal"]
        })

    if bucket == "Music":
        artist, album = read_audio_tags(path)
        if artist:
            music_scheme = all_schemes.get("music", {})
            existing_artist_folder = next(
                (d for d in music_scheme.get("subdirs", []) if d.lower() == artist.lower()), None
            )
            artist_shape = (
                music_scheme.get("subdir_shapes", {}).get(existing_artist_folder)
                if existing_artist_folder else None
            )
            if existing_artist_folder and artist_shape in ("flat", "empty"):
                dest = f"Music/{existing_artist_folder}"
                return _with_from_target({"src": str(path), "action": "move", "dest_dir": dest, "reason": f"existing artist folder is {artist_shape}; matching that shape", "confidence": "high"})
            artist_name = existing_artist_folder or artist
            dest = f"Music/{artist_name}/{album}" if album else f"Music/{artist_name}/Unknown Album"
            if album:
                return _with_from_target({"src": str(path), "action": "move", "dest_dir": dest, "reason": "tag/filename artist signal", "confidence": "high"})
            return _with_from_target({
                "src": str(path), "action": "move", "dest_dir": dest,
                "reason": "tag/filename artist signal, no album", "confidence": "medium",
                "candidate_destinations": [dest, f"Music/{artist_name}", "Music/Unsorted"]
            })
        return _with_from_target({
            "src": str(path), "action": "move", "dest_dir": "Music/Unsorted",
            "reason": "no artist tag or filename pattern found", "confidence": "low",
            "candidate_destinations": ["Music/Unsorted", "Downloads/Unsorted"]
        })

    if bucket == "Documents":
        if RECEIPT_NAME_RE.search(path.name):
            return _with_from_target({"src": str(path), "action": "move", "dest_dir": "Documents/Receipts", "reason": "filename matches receipt/invoice pattern", "confidence": "high"})
        return _with_from_target({"src": str(path), "action": "move", "dest_dir": "Documents", "reason": "extension matches Documents bucket", "confidence": "high"})

    if bucket in ("Archives", "Installers", "DiskImages", "Fonts", "Code"):
        return _with_from_target({"src": str(path), "action": "move", "dest_dir": bucket, "reason": f"extension matches {bucket} bucket", "confidence": "high"})

    if ext == "jar":
        if MOD_JAR_RE.search(path.name):
            return _with_from_target({
                "src": str(path), "action": "move", "dest_dir": "Downloads/Mods",
                "reason": "filename matches Minecraft mod-loader pattern", "confidence": "medium",
                "candidate_destinations": ["Downloads/Mods", "Downloads/Unsorted", "Documents"]
            })
        default_dest = config.get("unknown_extension_default", "Downloads/Unsorted")
        return _with_from_target({
            "src": str(path), "action": "move", "dest_dir": default_dest,
            "reason": "jar file, no mod-loader signal in filename", "confidence": "low",
            "candidate_destinations": [default_dest, "Downloads/Mods", "Documents"]
        })

    default_dest = config.get("unknown_extension_default", "Downloads/Unsorted")
    return _with_from_target({
        "src": str(path), "action": "move", "dest_dir": default_dest,
        "reason": "unrecognized extension", "confidence": "low",
        "candidate_destinations": [default_dest, "Documents", "Archives"]
    })


def find_duplicates(paths: List[Path]) -> List[List[str]]:
    by_size: Dict[int, List[Path]] = {}
    for p in paths:
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        by_size.setdefault(sz, []).append(p)
    groups: List[List[str]] = []
    CHUNK = 1024 * 1024

    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        sigs: Dict[str, List[Path]] = {}
        for c in candidates:
            try:
                with open(c, "rb") as f:
                    head = f.read(CHUNK)
                    if c.stat().st_size > CHUNK:
                        f.seek(-CHUNK, 2)
                        tail = f.read(CHUNK)
                    else:
                        tail = b""
                h = hashlib.sha256()
                h.update(head)
                h.update(tail)
                h.update(str(size).encode())
                s = h.hexdigest()
                sigs.setdefault(s, []).append(c)
            except OSError:
                continue
        for s, group in sigs.items():
            if len(group) >= 2:
                groups.append(sorted(str(g) for g in group))
    return groups


def recognized_subdirs_for(target: Path, structure_report: Optional[Dict[str, Any]]) -> Set[str]:
    if not structure_report:
        return set()
    entry = structure_report.get("directories", {}).get(str(target))
    if not entry:
        return set()
    return set(entry.get("subdirs", []))


def walk_target(target: Path, recursive: bool, exclude_set: List[str], structure_mode: Optional[str], recognized: Set[str]):
    if not recursive:
        for entry in target.iterdir():
            if entry.is_file():
                yield entry
        return

    for root, dirs, files in os.walk(target):
        root_path = Path(root)
        if any(str(root_path).startswith(str(Path(e).expanduser())) for e in exclude_set):
            dirs[:] = []
            continue
        if root_path != target:
            top_subdir = root_path.relative_to(target).parts[0]
            if structure_mode != "reorganize" and top_subdir in recognized:
                dirs[:] = []
                continue
        for name in files:
            yield root_path / name


def build_plan(
    targets: List[str | Path],
    include: Optional[List[str | Path]] = None,
    config: Optional[Dict[str, Any]] = None,
    recursive: bool = False,
    ambiguous_cap: int = 30,
    structure_report: Optional[Dict[str, Any]] = None,
    structure_mode: Optional[str] = None,
    quick: bool = False,
    log_dir: str | Path = "~/.file-organizer/logs",
) -> Dict[str, Any]:
    config = dict(config or {})
    if "ambiguous_cap" in config:
        ambiguous_cap = config["ambiguous_cap"]
    elif "ambiguous_review_cap" in config:
        ambiguous_cap = config["ambiguous_review_cap"]
    exclude_set = config.get("exclude", []) or []

    legacy_default = config.get("ambiguous_default", "Downloads/Unsorted")
    config.setdefault("ambiguous_photo_default", config.get("ambiguous_photo_default", legacy_default))
    config.setdefault("unknown_extension_default", config.get("unknown_extension_default", legacy_default))

    if quick:
        structure_mode = "fresh-only"
        structure_report = None
        if "ambiguous_default" not in config:
            config["ambiguous_default"] = "Downloads/Unsorted"

    all_schemes: Dict[str, Any] = {}
    if structure_report:
        for path_key, entry in structure_report.get("directories", {}).items():
            all_schemes[str(Path(path_key).expanduser().resolve())] = entry
            base = entry.get("root_name", "").lower()
            if base:
                all_schemes.setdefault(base, entry)

    per_target_modes: Dict[str, str] = {}
    if structure_mode is None:
        global_default_mode = "extend" if structure_report else "fresh-only"
    else:
        for piece in structure_mode.split(","):
            piece = piece.strip()
            if "=" in piece:
                t, m = piece.split("=", 1)
                per_target_modes[t.strip()] = m.strip()
        if any("=" in p for p in structure_mode.split(",")):
            global_default_mode = None
        else:
            global_default_mode = structure_mode.strip()

    base_recursive = recursive or config.get("recursive", False)
    prior_run_destinations = load_prior_run_destinations(Path(log_dir).expanduser())
    all_targets = [Path(t).expanduser() for t in (targets + (include or []))]
    ambiguous_budget = {"remaining": ambiguous_cap, "total_seen": 0}

    moves: List[Dict[str, Any]] = []
    reviews: List[Dict[str, Any]] = []
    skips: List[Dict[str, Any]] = []
    all_classified_paths: List[Path] = []
    target_modes_used: Dict[str, Optional[str]] = {}

    for target in all_targets:
        if not target.exists():
            continue
        target_mode = per_target_modes.get(str(target)) or per_target_modes.get(target.name) or global_default_mode
        effective_recursive = base_recursive or target_mode in ("extend", "reorganize")
        target_modes_used[str(target)] = target_mode
        recognized = recognized_subdirs_for(target, structure_report)
        for path in walk_target(target, effective_recursive, exclude_set, target_mode, recognized):
            result = classify(path, config, ambiguous_budget, all_schemes, prior_run_destinations, from_target=target)
            if result is None:
                continue
            all_classified_paths.append(path)
            if result["action"] == "move":
                moves.append(result)
            elif result["action"] == "review":
                reviews.append(result)
            elif result["action"] == "skip":
                skips.append(result)

    duplicates = find_duplicates(all_classified_paths)
    review_truncated = None
    if ambiguous_budget["total_seen"] > ambiguous_cap:
        review_truncated = {"shown": ambiguous_cap, "total": ambiguous_budget["total_seen"]}

    notes: List[str] = []
    if not HAVE_PIL:
        notes.append("Pillow not installed: EXIF was NOT checked on images (filename-only fallback).")
    if not HAVE_MUTAGEN:
        notes.append("mutagen not installed: ID3/audio tags were NOT checked on tracks (filename-only fallback).")

    return {
        "generated_at": datetime.now().isoformat(),
        "targets": [str(t) for t in all_targets],
        "structure_mode": structure_mode,
        "target_modes": target_modes_used,
        "quick_mode": quick,
        "moves": moves,
        "needs_review": reviews,
        "skipped": skips,
        "duplicates": duplicates,
        "review_truncated": review_truncated,
        "notes": notes,
    }


def render_plan_markdown(plan: Dict[str, Any]) -> str:
    dest_counts = Counter(m["dest_dir"] for m in plan.get("moves", []))
    md_lines = [f"# Organize plan — {plan.get('generated_at', 'unknown')}", ""]
    for n in plan.get("notes", []):
        md_lines.append(f"⚠️ {n}")
    if plan.get("notes"):
        md_lines.append("")
    if plan.get("review_truncated"):
        trunc = plan["review_truncated"]
        md_lines.append(f"⚠️ Only {trunc['shown']} of {trunc['total']} ambiguous images were reviewed.")
        md_lines.append("")
    md_lines.append(f"Targets: {', '.join(plan.get('targets', []))}")
    md_lines.append("")
    md_lines.append("## Proposed moves by destination")
    for dest, count in sorted(dest_counts.items()):
        md_lines.append(f"- {dest}: {count} file(s)")
    
    low_conf = [m for m in plan.get("moves", []) if m.get("confidence") == "low"]
    med_conf = [m for m in plan.get("moves", []) if m.get("confidence") == "medium"]
    if low_conf or med_conf:
        md_lines.append("")
        md_lines.append(f"## Low/medium-confidence moves ({len(low_conf)} low, {len(med_conf)} medium)")
        for m in low_conf + med_conf:
            cands = m.get("candidate_destinations")
            cand_str = f" (alternatives: {', '.join(cands)})" if cands else ""
            md_lines.append(f"- [{m.get('confidence')}] {m['src']} → {m['dest_dir']}{cand_str} — {m.get('reason', '')}")

    if plan.get("needs_review"):
        md_lines.append("")
        md_lines.append(f"## Needs visual review ({len(plan['needs_review'])})")
        for r in plan["needs_review"]:
            md_lines.append(f"- {r['src']}")

    if plan.get("skipped"):
        md_lines.append("")
        md_lines.append(f"## Skipped ({len(plan['skipped'])})")
        for s in plan["skipped"]:
            md_lines.append(f"- {s['src']} — {s.get('reason', '')}")

    if plan.get("duplicates"):
        md_lines.append("")
        md_lines.append(f"## Duplicates ({len(plan['duplicates'])} group(s))")
        for group in plan["duplicates"]:
            md_lines.append(f"- ({len(group)} identical files)")
            for g in group:
                md_lines.append(f"    - {g}")

    return "\n".join(md_lines)
