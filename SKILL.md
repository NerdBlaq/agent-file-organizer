---
name: file-organizer
description: Organizes cluttered user directories (Downloads, Videos, Pictures/Photos, Music, Documents) across Windows, macOS, and Linux by sorting files into the correct type-based folders and further clustering them by content (e.g. pulling family/people photos out of Downloads into Pictures, grouping screenshots separately from camera photos, sorting music by artist/album, separating screen recordings from real videos, recognizing Minecraft mod jars). Works universally across all file managers (Windows Explorer, macOS Finder, Linux Nautilus/Dolphin/Thunar) by operating on the filesystem directly. Use whenever the user asks to organize, sort, clean up, declutter, tidy, or auto-arrange folders, or wants files clustered by what they actually are rather than just extension.
---

# File Organizer

## Universal Cross-Platform Support

This works directly on the filesystem using standard, safe path operations (`shutil.move` and `Path`). Any file manager (Windows File Explorer, macOS Finder, Linux Nautilus, Dolphin, Thunar, etc.) instantly reflects the organized layout. There is no OS-specific or file-manager-specific API required.

Before doing anything else, confirm you have access to the target directories:

```bash
whoami && ls ~/Downloads ~/Pictures ~/Videos ~/Music 2>/dev/null || echo "Checked directories"
```

## Philosophy

Don't treat this as "extension X always goes in folder Y." A `.jpg` that's a screenshot of a receipt, a `.jpg` that's a family photo, and a `.jpg` that's a meme all deserve different homes even though they share an extension. The goal is to sort files the way a careful, judgment-using person would: by what the file *is* and *means*, using type as a first pass and content signals (metadata, filename semantics, and — for small ambiguous batches — actually looking at the file) to refine from there. `references/taxonomy.md` has a fuller default rule set, but treat it as a starting point to reason from, not a spec to satisfy mechanically.

**The scanner's output is a first draft, not a verdict.** `scan_and_plan.py` classifies file-by-file with no memory of the file next to it, so it will sometimes be confidently wrong or genuinely unable to tell. Every move it proposes carries a `confidence` (`high`/`medium`/`low`), and anything below `high` also carries `candidate_destinations` — plausible alternates. Read those before accepting a plan wholesale, and use `lib/plan_editing.py` (see Step 3) to override them.

Photos with no clear, confident subject default to staying in Downloads (in an `Unsorted` subfolder) rather than being force-fit into Pictures — a wrong guess buried three folders deep in Pictures is harder to find later than an unsorted file left where it landed.

## Non-negotiable safety rails

These apply in every mode below, no exceptions:

1. **Dry-run before doing anything.** Always build a plan first (`scripts/scan_and_plan.py`), show the user a summary, and get explicit confirmation before a single file moves.
2. **Move, never delete.** This skill never deletes files. If something looks like a true duplicate, flag it in the plan for the user to decide — don't remove it yourself.
3. **Never touch system/dotfiles/hidden files**, or anything outside the directories the user named.
4. **Never silently overwrite.** On a name collision, append a short numeric suffix before the extension.
5. **Log every move.** `scripts/apply_plan.py` writes an append-only undo log to `~/.file-organizer/logs/moves-<timestamp>.log`. Tell the user this path exists and that `scripts/undo.py <log path>` reverses it — run it with `--dry-run` first to preview reversals safely.
6. **Skip files that look in-use** (open in another app, mid-download `.part`/`.crdownload`/`.tmp` files) — leave them alone and note them in the plan as skipped.
7. **Don't re-suggest what a previous run already placed.** `scan_and_plan.py` reads prior runs' undo logs and skips any file still sitting exactly where a past run put it.

## Step 0 — Pick a speed, not just a mode

- **Quick** — for someone who just wants Downloads sorted and doesn't care about the mechanism. Run `scan_and_plan.py --quick`: fresh-only mode (existing subfolders left alone, no structure detection), only the directories actually named get touched. Show the plan, confirm, apply.
- **Custom** — proceed to Step 0.5 and Step 1 below for full control.

## Step 0.5 — Detect existing organization before proposing anything (Custom path only)

```bash
python3 scripts/detect_existing_structure.py --targets ~/Pictures ~/Music ~/Videos --output /tmp/structure.json
```

This classifies each directory's existing subfolders into one of:
- **flat** — nothing there yet, no decision needed
- **by-year** — e.g. `Pictures/2024`, `Pictures/2025`
- **matches-default-taxonomy** — existing folders match standard defaults
- **custom** — user's own scheme (event names, project names, artist names)

## Step 1 — Guided or Autonomous (Custom path only)

- **A) Guided** — the user tells you the rules/preferences up front (which folders to include, custom clusters). Use `assets/config.example.yaml` as a starting template.
- **B) Autonomous** — no upfront rules; use the default taxonomy in `references/taxonomy.md` and your own judgment with a dry-run first.

## Step 2 — Build the plan

```bash
python3 scripts/scan_and_plan.py --targets ~/Downloads --output /tmp/organize-plan.json \
  [--include ~/Pictures ~/Videos ~/Music] [--config path/to/config.yaml] [--recursive] \
  [--structure-report /tmp/structure.json --structure-mode extend|reorganize|fresh-only] \
  [--quick]
```

## Step 3 — Resolve ambiguous items and review low/medium-confidence guesses

For ambiguous items or candidate adjustments, use `lib/plan_editing.py`:

```python
from lib.plan_editing import load_plan, save_plan, add_move, set_dest_dir, drop_move

plan = load_plan("/tmp/organize-plan.json")
plan = add_move(plan, "/path/to/Downloads/vacation_pic.png", "Pictures/People", reason="visual review: has people")
plan = set_dest_dir(plan, "/path/to/Downloads/mystery-app.jar", "Downloads/Mods", reason="visually confirmed mod")
plan = drop_move(plan, "/path/to/Downloads/track01.mp3")  # leave in place
save_plan(plan, "/tmp/organize-plan.json")
```

## Step 4 — Confirm and apply

Show the user the summary and wait for explicit confirmation. Then:

```bash
python3 scripts/apply_plan.py --plan /tmp/organize-plan.json
```

## Step 5 — Recap

Report a concise, concrete summary: how many files moved to each destination, how many were left unsorted, skipped items, and the undo log path.

## Reference files

- `references/taxonomy.md` — the full default extension → bucket table and content-clustering heuristics.
- `references/behavior.md` — behavior specifications.
- `assets/config.example.yaml` — template for Guided mode.
- `scripts/detect_existing_structure.py` — structure scanner.
- `scripts/scan_and_plan.py` — dry-run plan generator.
- `lib/plan_editing.py` — plan editing helpers.
- `scripts/apply_plan.py` — move executor with collision safety.
- `scripts/undo.py` — moves reverser with `--dry-run` preview.
