# What the scripts actually do

This is a plain description of behavior, not a rules doc — read this if you want to verify what will happen before running something against real files, rather than trusting the summary in SKILL.md.

## detect_existing_structure.py

Read-only. For each `--targets` directory: lists its immediate subfolders (hidden ones excluded), classifies the set of subfolder names as `flat` / `by-year` / `matches-default-taxonomy` / `custom`, and for each subfolder records whether it holds files directly (`flat` shape) or only further subfolders (`nested` shape, e.g. an album layer). Also counts loose files at the top level vs. files already nested inside subfolders. Writes `structure.json` (machine-readable) and `structure.md` (human-readable). Never opens, moves, or modifies any file it finds — it only calls `iterdir()`/`rglob()` for counting.

## scan_and_plan.py

Read-only except for the two output files it writes (`plan.json`, `plan.md`). Walks each `--targets`/`--include` directory (top-level only unless `--recursive`, or unless `--structure-mode` is `extend`/`reorganize`, which force recursion) and for every file:

1. Skips dotfiles and files matching an in-progress pattern (`.part`, `.crdownload`, `.tmp`, `.download`) — these go in the plan's `skipped` list, untouched.
2. If a `--structure-report` was supplied and the file's current location is inside a subfolder that report already recognized as organized, the file is skipped entirely (unless `--structure-mode reorganize`) — this is the "leave already-organized files alone" protection.
3. If the file's current absolute path matches a destination logged by a previous run of `apply_plan.py` (read from `--log-dir`, default `~/.file-organizer/logs/*.log`), it's skipped with a "placed here by a previous run" reason instead of being reclassified — a file the skill already sorted doesn't get flagged as fresh clutter on every rerun.
4. Otherwise classifies the file: extension → bucket, then filename/EXIF/ID3-tag heuristics refine the destination within that bucket (see `taxonomy.md`). `.jar` files get their own check for Minecraft mod-loader filename patterns (fabric/forge/quilt/etc.) before falling back to a generic low-confidence guess. Every classification carries a `confidence` (`high` / `medium` / `low`); low and medium entries also carry a `candidate_destinations` list of plausible alternates.
5. Photos with no confident signal are set aside as `needs_review` (capped at `--ambiguous-cap`, default 30) instead of guessed at. If more are found than the cap allows, `plan.json["review_truncated"]` records the exact shown/total counts and `plan.md` states it at the top, not buried in a footer.

Nothing is moved. The only filesystem writes are the two output files themselves.

## lib/plan_editing.py

Not a script — a small library of pure functions (`add_move`, `set_dest_dir`, `drop_move`) for editing a `plan.json` between the scan and apply steps: resolving a `needs_review` entry, swapping a low-confidence guess for one of its own candidates, or removing a proposed move you disagree with. Each function takes a plan dict and returns a plan dict; nothing here touches the actual files being organized, only the plan describing what *would* happen to them.

## apply_plan.py

The only script that touches real files, and only ever via `shutil.move` (rename/move at the filesystem level — no copy-then-delete, no read-and-rewrite of file contents). For each entry in `plan.json["moves"]`:

1. Re-checks the source file still exists (skips with a stderr warning if not — e.g. it was already moved by a previous run).
2. Creates the destination directory if needed (`mkdir(parents=True, exist_ok=True)`).
3. If the destination filename already exists, appends `" (1)"`, `" (2)"`, etc. until it finds a name that doesn't — never overwrites.
4. Moves the file, and appends a `source\tdestination` line to an append-only log at `~/.file-organizer/logs/moves-<timestamp>.log`.

Never deletes anything. A file that fails to move (permissions, etc.) is reported to stderr and left in place; the run continues rather than aborting.

## undo.py

Reads one moves log (in reverse order) and prints the full plan — every file it would move back, plus any conflicts (original location occupied again) or already-gone entries (destination no longer exists) — *before* moving anything, the same way `apply_plan.py`'s `plan.json` lets you see the forward direction before committing to it. Pass `--dry-run` to stop after printing that plan. Without it, it proceeds to actually move each file back via `shutil.move` — again never a delete. If the original source path is occupied again, that entry is left in place and reported as a conflict rather than overwritten; if the destination is already gone, that entry is skipped and reported, not treated as an error that stops the rest of the undo.

## What none of these scripts do

- None of them delete a file with content in it, under any mode or flag.
- None of them read or modify file *contents* — only location (and, for images/audio, metadata reads for classification, which don't alter the file).
- None of them recurse into a directory the structure report identified as already organized unless `--structure-mode reorganize` is explicitly passed.
