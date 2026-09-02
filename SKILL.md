---
name: file-organizer
description: Organizes cluttered Linux home-folder directories (Downloads, Videos, Pictures/Photos, Music, Documents) by sorting files into the correct type-based folder and further clustering them by content (e.g. pulling family/people photos out of Downloads into Pictures, grouping screenshots separately from camera photos, sorting music by artist/album, separating screen recordings from real videos, recognizing Minecraft mod jars). Works on Zorin OS and other XDG-layout Linux desktops (Thunar, Nautilus, etc.) by operating on the filesystem directly, not through any file manager's UI. Use whenever the user asks to organize, sort, clean up, declutter, tidy, or auto-arrange Downloads/Videos/Pictures/Photos/Music, or wants files clustered by what they actually are rather than just extension. Requires real filesystem access (e.g. via Claude Code running locally) — does not work in a browser-only sandboxed chat session.
---

# File Organizer

## What this actually touches

This works directly on the filesystem with `shutil.move`; whatever file manager the user has open (Thunar, Nautilus, whatever) just reflects the new layout next time it's open. There's no file-manager API involved and none is needed. The real prerequisite is **actual bash/filesystem access to the user's home directory**.

Before doing anything else, confirm you have that access:

```bash
whoami && echo "$HOME" && ls ~/Downloads ~/Pictures ~/Videos ~/Music 2>/dev/null
```

If this isn't a real session with the user's actual home directory (e.g. you're in a disposable claude.ai sandbox), say so plainly and stop — a dry-run plan against a filesystem that isn't the user's machine is worthless busywork, not a real deliverable.

## Philosophy

Don't treat this as "extension X always goes in folder Y." A `.jpg` that's a screenshot of a receipt, a `.jpg` that's a family photo, and a `.jpg` that's a meme all deserve different homes even though they share an extension. The goal is to sort files the way a careful, judgment-using person would: by what the file *is* and *means*, using type as a first pass and content signals (metadata, filename semantics, and — for small ambiguous batches — actually looking at the file) to refine from there. `references/taxonomy.md` has a fuller default rule set, but treat it as a starting point to reason from, not a spec to satisfy mechanically.

**The scanner's output is a first draft, not a verdict.** `scan_and_plan.py` classifies file-by-file with no memory of the file next to it, so it will sometimes be confidently wrong or genuinely unable to tell. Every move it proposes carries a `confidence` (`high`/`medium`/`low`), and anything below `high` also carries `candidate_destinations` — plausible alternates. Read those before accepting a plan wholesale, and use `lib/plan_editing.py` (see Step 3) to override them. A "low confidence" label doesn't mean "no signal at all" — a `fabric-api-1.20.4-mc1.20.4.jar` and a file called `xyz123.dat` are both "low confidence" in the sense of not hitting a `high` rule, but one of them has an obvious answer a human would spot instantly. Check `candidate_destinations` before defaulting to Downloads/Unsorted just because the label says "low."

Photos with no clear, confident subject default to staying in Downloads (in an `Unsorted` subfolder) rather than being force-fit into Pictures — that's the user's own stated default and it's the right call: a wrong guess buried three folders deep in Pictures is harder to find later than an unsorted file left where it landed.

## Non-negotiable safety rails

These apply in every mode below, no exceptions:

1. **Dry-run before doing anything.** Always build a plan first (`scripts/scan_and_plan.py`), show the user a summary, and get explicit confirmation before a single file moves.
2. **Move, never delete.** This skill never deletes files. If something looks like a true duplicate, flag it in the plan for the user to decide — don't remove it yourself.
3. **Never touch dotfiles/hidden files, or anything outside the directories the user named.**
4. **Never silently overwrite.** On a name collision, append a short numeric suffix before the extension.
5. **Log every move.** `scripts/apply_plan.py` writes an append-only undo log to `~/.file-organizer/logs/moves-<timestamp>.log` (format: `original_path\tnew_path`). Tell the user this path exists and that `scripts/undo.py <log path>` reverses it — run it with `--dry-run` first if you (or they) want to see exactly what it would revert before it touches anything.
6. **Skip files that look in-use** (open in another app, mid-download `.part`/`.crdownload`/`.tmp` files) — leave them alone and note them in the plan as skipped.
7. **Don't re-suggest what a previous run already placed.** `scan_and_plan.py` reads prior runs' undo logs and skips any file still sitting exactly where a past run put it — it won't nag about the same `Downloads/Unsorted/whatever.xyz` every single time you rerun it.

## Step 0 — Pick a speed, not just a mode

Before anything else, this is really two questions bundled as one: does the user want to answer a few questions, or just get a sensible result fast?

**Detect the implicit answer first.** A request like "just clean up my Downloads" or "tidy up my Downloads folder" is an unambiguous Quick request — skip the question and go straight to Step 2 with `--quick`. A request like "help me organize my pictures" or "set up how I want my music sorted" is an unambiguous Custom request — skip the question and go to Step 0.5.

Only ask if the request is genuinely ambiguous (e.g. "organize my stuff" with no folder names or specifics). When asking, keep it to one line, not three stacked prompts:

> "Should I just sort things with sensible defaults, or do you want to set preferences first (which folders, custom clusters, how to handle existing organization)?"

- **Quick** — skip Step 0.5 and the Guided config entirely. Run `scan_and_plan.py --quick`: fresh-only mode (existing subfolders left alone, no structure detection), only the directories actually named get touched, ambiguous photos and unknown-extension files go to the `ambiguous_photo_default` / `unknown_extension_default` (default `Downloads/Unsorted`). Show the plan, confirm, apply. For someone who just wants Downloads sorted and doesn't care about the mechanism.
- **Custom** — proceed to Step 0.5 and Step 1 below for full control.

## Step 0.5 — Detect existing organization before proposing anything (Custom path only)

Before building a plan for `~/Pictures`, `~/Videos`, `~/Music`, or any directory the user has likely already touched by hand, check what's already there:

```bash
python3 scripts/detect_existing_structure.py --targets ~/Pictures ~/Music ~/Videos --output /tmp/structure.json
```

This classifies each directory's existing subfolders into one of:
- **flat** — nothing there yet, no decision needed
- **by-year** — e.g. `Pictures/2024`, `Pictures/2025`
- **matches-default-taxonomy** — the user's folders already happen to line up with this skill's own default names
- **custom** — the user's own scheme (event names, project names, artist names) that doesn't match a pattern this skill can infer automatically

If everything comes back `flat`, skip straight to Step 1 — there's nothing to reconcile. Otherwise, this is a required checkpoint. Render it as a single yes/no question — not a two-option menu, because the two choices are not equivalent in risk:

> **Apply this run to your already-organized folders too?** *(defaults to No)*
>
> ☐ **No — Extend (safe)** *(default)*: new and stray files get folded into what's already there, following the same pattern. A new year gets a new year folder; an artist already kept flat stays flat rather than gaining an "Unknown Album" subfolder it didn't have. Anything already inside a recognized folder is left completely alone.
>
> ☐ **Yes — Reorganize (destructive)**: files in your already-sorted folders become eligible to move again per the taxonomy. A file's *location* is sometimes the only place information lives — a track sitting in `Music/Fela Kuti/` with no ID3 tags and a filename that doesn't say "Fela Kuti" anywhere will fall into `Music/Unsorted` under Reorganize, because the folder name was the only record of who made it. Only choose this if you've reviewed the plan and confirmed no knowledge lives in folder placement alone.
>
> ⚠ **Only proceed on an explicit "yes, reorganize"** — not on a general "looks good" to the plan. A safe default can be pre-answered by config; a destructive one cannot.

Config notes:
- `config.yaml: structure_mode: extend` → skip the prompt silently. Safe to honor without asking.
- `config.yaml: structure_mode: reorganize` → **do not skip the prompt anyway.** A config value can pre-answer a safe default, but it can't pre-authorize a destructive action on the user's behalf across future runs they may not be watching for. Ask out loud, every time, and only proceed on that explicit yes.

If the user doesn't answer this and just says "organize my downloads" with no mention of Pictures/Music/Videos, default to Extend scoped to whatever they actually named — don't go looking for extra directories to reorganize without being asked.

## Step 1 — Guided or Autonomous (Custom path only)

- **A) Guided** — the user tells you the rules/preferences up front (which folders to include, what clusters they want, e.g. "Screenshots", "Work", "Receipts", "Memes", how to handle ambiguous photos, anything to exclude). Walk them through `assets/config.example.yaml` as a starting point rather than an open-ended "what do you want" — it's much faster for the user to edit a filled-in template than to write requirements from scratch.
- **B) Autonomous** — no upfront rules; use the default taxonomy in `references/taxonomy.md` and your own judgment, still with a dry-run and confirmation step before anything moves.

If the user picks Guided, don't proceed to scanning until you have at least: which directories to organize, and how they want unclear/ambiguous items handled (default: leave in `Downloads/Unsorted`).

## Step 2 — Build the plan

```bash
python3 scripts/scan_and_plan.py --targets ~/Downloads --output /tmp/organize-plan.json \
  [--include ~/Pictures ~/Videos ~/Music] [--config path/to/config.yaml] [--recursive] \
  [--structure-report /tmp/structure.json --structure-mode extend|reorganize|fresh-only] \
  [--quick]
```

If `--structure-report` is given and `--structure-mode` isn't set explicitly, it defaults to `extend`. Without a structure report at all, it defaults to `fresh-only`. `--quick` overrides both to fresh-only and ignores any structure report, per Step 0.

Full behavior detail — exactly what gets read, classified, and written, file by file — is in `references/behavior.md`; the summary here is enough to run it, that file is enough to audit it. Two things worth calling out up front rather than leaving buried in the output:

- **If Pillow or mutagen aren't installed**, the script still runs, but photo/audio classification falls back to filename-only heuristics — `plan.md` puts this warning at the very top, not in a trailing notes section, because it changes how much to trust everything below it.
- **If more ambiguous images turn up than `--ambiguous-cap`** (default 30), the excess isn't silently dropped into the default — `plan.md` states the exact shown/total counts at the top and says how many were left un-reviewed.

## Step 3 — Resolve ambiguous items and review low/medium-confidence guesses

For each ambiguous image (capped batch from Step 2), you can actually look at it with the `view` tool and make a call — but keep the categories honest and non-invasive:

- Photo clearly has people/a family scene in it → `Pictures/People`
- Photo is a screenshot of text, a receipt, or a document → `Documents/Receipts` (or `Documents/Screenshots` if it's not receipt-like)
- Nothing confident to go on → leave it, don't force a guess

Don't infer identity, relationships, or anything beyond "has people in it." If more images were flagged than the cap allows, tell the user how many were left un-reviewed and let them decide whether to raise the cap and rerun, or accept the default.

Also skim `plan.md`'s low/medium-confidence section — these already moved somewhere in the plan, but with a `candidate_destinations` list attached. Don't hand-edit `plan.json`'s text to fix these; use the helper module instead:

```python
from lib.plan_editing import load_plan, save_plan, add_move, set_dest_dir, drop_move

plan = load_plan("/tmp/organize-plan.json")
plan = add_move(plan, "/home/user/Downloads/vacation_pic.png", "Pictures/People", reason="visual review: has people")
plan = set_dest_dir(plan, "/home/user/Downloads/mystery-app.jar", "Downloads/Mods", reason="visually confirmed it's a mod")
plan = drop_move(plan, "/home/user/Downloads/track01.mp3")  # leave this one exactly where it is
save_plan(plan, "/tmp/organize-plan.json")
```

`add_move` also clears the matching `needs_review` entry, so resolving a review item and merging it into the plan is one call, not two.

## Step 4 — Confirm and apply

Show the user the `plan.md` summary. Wait for explicit go-ahead — "looks good", "do it", "proceed", etc. Then:

```bash
python3 scripts/apply_plan.py --plan /tmp/organize-plan.json
```

This executes the moves, handles collisions by suffixing, and writes the undo log described above.

## Step 5 — Recap

Report a short, concrete summary: how many files moved to each top-level destination, how many were left in `Downloads/Unsorted`, how many were skipped and why, and the undo log path. Don't pad this with generic "your files are now organized!" filler — the numbers are the useful part.

## Reference files

- `references/taxonomy.md` — the full default extension → bucket table and content-clustering heuristics.
- `references/behavior.md` — exactly what each script does to the filesystem, for auditing before you trust it on real files.
- `assets/config.example.yaml` — template for Guided mode; also where `structure_mode` can be pre-set (extend only — see Step 0.5).
- `scripts/detect_existing_structure.py` — Step 0.5's scanner; read-only.
- `scripts/scan_and_plan.py` — read-only, writes `plan.json`/`plan.md`.
- `lib/plan_editing.py` — edit a plan between scan and apply without hand-writing JSON.
- `scripts/apply_plan.py` — the only script that moves real files.
- `scripts/undo.py` — reverses a moves log; supports `--dry-run`.
