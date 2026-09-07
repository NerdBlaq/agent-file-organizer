---
name: file-organizer
description: Organizes cluttered user directories (Downloads, Videos, Pictures/Photos, Music, Documents) across Windows, macOS, and Linux by sorting files into the correct type-based folders and further clustering them by content (e.g. pulling family/people photos out of Downloads into Pictures, grouping screenshots separately from camera photos, sorting music by artist/album, separating screen recordings from real videos, recognizing Minecraft mod jars, protecting game/software install folders from being torn apart). Works universally across all file managers (Windows Explorer, macOS Finder, Linux Nautilus/Dolphin/Thunar) by operating on the filesystem directly. Use whenever the user asks to organize, sort, clean up, declutter, tidy, or auto-arrange folders, or wants files clustered by what they actually are rather than just extension.
---

# File Organizer

## Universal Cross-Platform Support

This works directly on the filesystem using standard, safe path operations (`shutil.move` and `Path`). Any file manager (Windows File Explorer, macOS Finder, Linux Nautilus, Dolphin, Thunar, etc.) instantly reflects the organized layout. There is no OS-specific or file-manager-specific API required.

Before doing anything else, confirm you have access to the target directories:

```bash
whoami && ls ~/Downloads ~/Pictures ~/Videos ~/Music 2>/dev/null || echo "Checked directories"
```

If the target is an external drive or a mount point rather than the home directory, note that explicitly before scanning — it changes what the correct `--base` is at apply time (see safety rail 9).

## Philosophy

Don't treat this as "extension X always goes in folder Y." A `.jpg` that's a screenshot of a receipt, a `.jpg` that's a family photo, and a `.jpg` that's a meme all deserve different homes even though they share an extension. The goal is to sort files the way a careful, judgment-using person would: by what the file *is* and *means*, using type as a first pass and content signals (metadata, filename semantics, and — for small ambiguous batches — actually looking at the file) to refine from there. `references/taxonomy.md` has a fuller default rule set, but treat it as a starting point to reason from, not a spec to satisfy mechanically.

**The scanner's output is a first draft, not a verdict.** `scan_and_plan.py` classifies file-by-file with no memory of the file next to it, so it will sometimes be confidently wrong or genuinely unable to tell. Every move it proposes carries a `confidence` (`high`/`medium`/`low`), and anything below `high` also carries `candidate_destinations` — plausible alternates. Read those before accepting a plan wholesale, and use `lib/plan_editing.py` (see Step 3) to override them.

Photos with no clear, confident subject default to staying in Downloads (in an `Unsorted` subfolder) rather than being force-fit into Pictures — a wrong guess buried three folders deep in Pictures is harder to find later than an unsorted file left where it landed.

**Some directories are never individually sorted, in any mode.** A directory is protected either because it contains a `.exe`/`.dll`/`.so`/`.dylib`/`.bin`/`.msi` file anywhere in its subtree, or because its own name matches a known curated-content pattern (`games`, `my games`, `shaderpacks`, `mc extras`, etc. — extensible via config's `protected_folder_names`). The name-based check exists because most real cases have no binary at all to detect: a folder of compressed game archives, a save-data folder of configs and `.dat` files, a shader pack of `.zip`s — confirmed torn apart in real incidents specifically because nothing in them was a recognizable executable. This exists because reorganize mode flattening a curated document folder is a misfiling (annoying, fully recoverable); the same behavior against a game or application install actually breaks it, which is a different order of harm that no taxonomy override should be able to touch.

If there's a specific folder that must never be touched regardless of what it contains or is named — a personal reference archive that's already exactly how the user wants it, say — that's what `exclude` in config is for (see `assets/config.example.yaml`): an exact path, not a pattern, and it's respected in every mode including `reorganize`.

## Non-negotiable safety rails

These apply in every mode below, no exceptions:

1. **Dry-run before doing anything.** Always build a plan first (`scripts/scan_and_plan.py`), show the user a summary, and get explicit confirmation before a single file moves.
2. **Move, never delete.** This skill never deletes files. If something looks like a true duplicate, flag it in the plan for the user to decide — don't remove it yourself.
3. **Never touch system/dotfiles/hidden files**, or anything outside the directories the user named.
4. **Never silently overwrite.** On a name collision, append a short numeric suffix before the extension.
5. **Log every move.** `scripts/apply_plan.py` writes an append-only undo log to `~/.file-organizer/logs/moves-<timestamp>-<pid>.log`. Tell the user this path exists and that `scripts/undo.py <log path>` reverses it — run it with `--dry-run` first to preview reversals safely.
6. **Skip files that look in-use** (open in another app, mid-download `.part`/`.crdownload`/`.tmp` files) — leave them alone and note them in the plan as skipped.
7. **Don't re-suggest what a previous run already placed.** `scan_and_plan.py` reads prior runs' undo logs and skips any file still sitting exactly where a past run put it.
8. **Never declare a recovery complete on the strength of one incomplete check.** A single `find` for one filename pattern is not verification. After running `undo.py`, run `scripts/verify_recovery.py <log path>` and only tell the user things are restored if it reports every logged file back at its original location. This exists because of a real incident: an agent said "I have already restored your files to their original state" based on one failed search, and got lucky that it happened to be true — the process, not just the outcome, was the problem.
9. **Never move a file across a filesystem/mount boundary without being told to.** `apply_plan.py` derives `--base` from the plan's own recorded targets (not home) when not given explicitly, and aborts before moving anything if a computed destination would land on a different filesystem than the base — pass `--allow-cross-filesystem` only if that's actually intended. This exists because of a real incident: a run with no `--base` moved files from an external drive onto the OS partition because `--base` used to default to `~` unconditionally.
10. **Never reach inside a software/game package to sort its files individually.** See Philosophy above — `plan.md` lists any protected directories found.
11. **Never create a same-named nested duplicate.** If a file is already directly inside a folder named e.g. "Documents" and its classified bucket is also "Documents", it's left in place rather than filed into a "Documents/Documents" duplicate. This exists because of a real, repeated incident: scanning a directory whose own name coincided with a taxonomy bucket name produced exactly this nesting, confirmed in two separate incident logs.
12. **Record why a run happened, not just what moved.** `scripts/session_log.py` (or the `log-session`/MCP equivalents) write a structured entry — what was asked, what mode was chosen, what the user actually said to confirm — separate from the mechanical moves log. Call it at the start of a run and again at confirmation/apply. This exists because every incident review of this project has had to be reconstructed by hand from chat transcripts; a structured record makes that "read a file" instead.

## Step 0 — Pick a speed, not just a mode

- **Quick** — for someone who just wants Downloads sorted and doesn't care about the mechanism. Run `scan_and_plan.py --quick`: fresh-only mode (existing subfolders left alone, no structure detection), only the directories actually named get touched. Show the plan, confirm, apply.
- **Custom** — proceed to Step 0.5 and Step 1 below for full control.

Before scanning, log the request: `python3 scripts/session_log.py --event run_started --user-request "<what the user actually asked for>" --mode quick|guided|autonomous`. This takes one line and is the single most useful thing for reconstructing what happened if anything goes wrong later — don't skip it because the run looks routine.

## Step 0.5 — Detect existing organization before proposing anything (Custom path only)

```bash
python3 scripts/detect_existing_structure.py --targets ~/Pictures ~/Music ~/Videos --output /tmp/structure.json
```

This classifies each directory's existing subfolders into one of:
- **flat** — nothing there yet, no decision needed
- **by-year** — e.g. `Pictures/2024`, `Pictures/2025`
- **matches-default-taxonomy** — existing folders match standard defaults
- **custom** — user's own scheme (event names, project names, artist names)

If everything comes back flat, skip straight to Step 1. Otherwise, this is a required checkpoint, and the choice isn't a neutral A/B menu:

> **Apply to already-organized folders too?**
> ☐ *(default)* **Extend (safe)** — new and stray files fold into what's already there, following the same pattern; anything already inside a recognized folder is left alone.
> ☑ **Reorganize (re-files everything, may lose context)** — already-sorted files become eligible to move too. A file's *location* is sometimes the only place information lives: a track sitting in `Music/Fela Kuti/` with no ID3 tags and a filename that says nothing about the artist will fall into `Music/Unsorted` under Reorganize — the folder name was the only record of who made it, and this throws it away.

`--structure-mode` also accepts per-target overrides (`Pictures=extend,Music=reorganize`) if the user wants different handling for different folders — don't default to one global mode when they've expressed different comfort levels for different directories. If config already sets `structure_mode: extend`, this prompt can be skipped. **If it sets `reorganize`, do not skip the prompt anyway** — a config value can pre-answer a safe default, it can't pre-authorize a destructive one for a future run nobody's watching.

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

`plan.md` puts dependency caveats (missing Pillow/mutagen), review-cap truncation counts, and any protected package directories at the top — read those before the move list, they change how much to trust everything below them.

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

When actually looking at an ambiguous photo: a photo with people in it goes to `Pictures/People`; don't infer identity, relationships, or anything beyond "has people in it." Nothing confident to go on means leave it — don't force a guess to clear the review queue.

## Step 4 — Confirm and apply

Show the user the summary and wait for explicit confirmation. Log it — `python3 scripts/session_log.py --event confirmed --confirmation "<what they actually said>"` — using their own words, not a paraphrase like "user approved." Then:

```bash
python3 scripts/apply_plan.py --plan /tmp/organize-plan.json
```

This derives `--base` from the plan's own targets if not given explicitly, and aborts before moving anything if a destination would cross a filesystem boundary.

**For large plans, especially `reorganize`-mode ones, apply in batches instead of one shot.** Use `lib/plan_editing.py`'s `split_by_top_level_dest(plan)` to get one sub-plan per top-level destination category, apply and show the result for one category, and only move to the next after the user's seen it. There's no hard threshold — use judgment — but a reorganize-mode plan touching hundreds of files or several categories the user hasn't specifically pre-approved is exactly the situation this is for.

If something goes wrong mid-run, don't guess at the recovery — use `verify_recovery.py`, not a one-off search, before telling the user anything is fixed.

## Step 5 — Recap

Report a concise, concrete summary: how many files moved to each destination, how many were left unsorted, skipped items, any protected package directories left untouched, and the undo log path. Log the outcome: `python3 scripts/session_log.py --event applied --notes "<counts, protected dirs, anything unusual>"`.

## What this skill deliberately does NOT do

It doesn't invent a bespoke folder taxonomy per drive ("Analysis Phase" / adaptive taxonomy). `detect_existing_structure.py` + Extend mode already does "recognize the user's own named folders and don't fight them" — a second, parallel custom-taxonomy engine would duplicate that logic rather than fix a case where it wasn't used. If Extend mode itself proves insufficient in practice, that's worth revisiting on its own terms.

## Reference files

- `references/taxonomy.md` — the full default extension → bucket table and content-clustering heuristics.
- `references/behavior.md` — behavior specifications.
- `assets/config.example.yaml` — template for Guided mode.
- `scripts/detect_existing_structure.py` — structure scanner.
- `scripts/scan_and_plan.py` — dry-run plan generator.
- `lib/plan_editing.py` — plan editing helpers, including `split_by_top_level_dest` for batch application.
- `scripts/apply_plan.py` — move executor with collision safety, path-isolation, and Integrity Guard enforcement.
- `scripts/undo.py` — moves reverser with `--dry-run` preview.
- `scripts/verify_recovery.py` — checks a moves log against actual filesystem state; run before ever declaring a recovery complete.
- `scripts/session_log.py` — structured record of what was asked, chosen, and confirmed, separate from the mechanical moves log.
