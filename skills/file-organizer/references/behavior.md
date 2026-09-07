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
6. **Integrity Guard (v1.1.2, extended v1.1.3):** before descending into any directory (in any structure mode, including `reorganize`) other than the top-level scanned target itself, checks two independent signals: whether the directory's own name matches a known curated-content pattern (`games`, `my games`, `shaderpacks`, `mc extras`, etc. — extensible via config's `protected_folder_names`), or whether any file anywhere in its subtree (checked recursively) has a `.exe`/`.dll`/`.so`/`.dylib`/`.bin`/`.msi` extension. Either signal alone is sufficient. If either fires, the whole directory is left alone — none of its files, at any depth, are classified or yielded — and it's recorded in `plan.json["protected_dirs"]`. This check runs before and overrides the "recognized existing scheme" check, and unlike that check it is never bypassed by `reorganize` mode. The name-based signal was added after real incident logs showed the content-based check alone missing compressed game archives, save-data folders, and resource/shader packs — none of which contain a binary file anywhere.

Nothing is moved. The only filesystem writes are the two output files themselves.

## lib/plan_editing.py

Not a script — a small library of pure functions (`add_move`, `set_dest_dir`, `drop_move`, `split_by_top_level_dest`) for editing a `plan.json` between the scan and apply steps: resolving a `needs_review` entry, swapping a low-confidence guess for one of its own candidates, removing a proposed move you disagree with, or splitting a plan into per-destination-category batches for staged application (v1.1.2). Each function takes a plan dict and returns a plan dict; nothing here touches the actual files being organized, only the plan describing what *would* happen to them.

## apply_plan.py

The only script that touches real files, and only ever via `shutil.move` (rename/move at the filesystem level — no copy-then-delete, no read-and-rewrite of file contents).

**v1.1.2 pre-flight, before any file is touched:** `--base` is resolved — either the explicit `--base` argument, or (default) the common ancestor of `plan["targets"]`, the directories `scan_and_plan.py` actually scanned. This replaced an unconditional default of `~`, which was the direct cause of a real incident: a scan of an external drive, applied with no `--base`, moved files onto the OS home directory. Then every move's source filesystem (`os.stat().st_dev`, walking up to the nearest existing ancestor) is compared against the base's filesystem; if any would cross that boundary, the entire run aborts with a list of the offending files and zero files moved — unless `--allow-cross-filesystem` was passed.

For each entry in `plan.json["moves"]` that survives pre-flight:

1. Skipped outright if `m.get("protected")` is set (v1.1.2 — Integrity Guard entries from `scan_and_plan.py`; belt-and-suspenders in case something upstream left one in the moves list).
2. Re-checks the source file still exists (skips with a stderr warning if not — e.g. it was already moved by a previous run).
3. Creates the destination directory if needed (`mkdir(parents=True, exist_ok=True)`).
4. If the destination filename already exists, appends `" (1)"`, `" (2)"`, etc. until it finds a name that doesn't — never overwrites.
5. **Self-nesting guard (v1.1.3)**: if the destination folder's name matches the name of the folder the file is already directly inside (but the two paths aren't the same folder), the move is skipped as a no-op rather than creating a redundant same-named subfolder — e.g. a file already inside a folder named "Documents" doesn't get filed into "Documents/Documents". This check runs before the destination directory is even created, so no empty nested folder is left behind either. Confirmed as a real, repeated failure in two separate incident logs before this fix.
5. Moves the file, and appends a `source\tdestination` line to an append-only log at `~/.file-organizer/logs/moves-<timestamp>-<pid>.log`.

Never deletes anything. A file that fails to move (permissions, etc.) is reported to stderr and left in place; the run continues rather than aborting (this is separate from the pre-flight abort, which happens before any move and stops the whole run).

## undo.py

Reads one moves log (in reverse order) and prints the full plan — every file it would move back, plus any conflicts (original location occupied again) or already-gone entries (destination no longer exists) — *before* moving anything, the same way `apply_plan.py`'s `plan.json` lets you see the forward direction before committing to it. Pass `--dry-run` to stop after printing that plan. Without it, it proceeds to actually move each file back via `shutil.move` — again never a delete. If the original source path is occupied again, that entry is left in place and reported as a conflict rather than overwritten; if the destination is already gone, that entry is skipped and reported, not treated as an error that stops the rest of the undo.

## verify_recovery.py (v1.1.2)

Read-only, moves nothing. Added directly in response to an incident where an agent declared a recovery complete based on a single failed `find` command rather than checking the actual log. For every line in a moves log, checks the real current filesystem: is the file back at its original `src` (reverted), still at `dest` (not reverted), or at neither (moved/renamed/deleted by something else since — flagged, not assumed). Exits non-zero and prints "recovery is INCOMPLETE" unless every logged file is confirmed back at its original location. This is the check that should run before anyone — human or agent — says a recovery is done.

## session_log.py (v1.1.3)

Not a mover, not even a filesystem-safety check — a structured record of *why* a run happened, separate from the moves log's record of *what* happened. Appends one JSON object per line to `~/.file-organizer/logs/sessions.jsonl`: a timestamp, an `event` label (`run_started`, `mode_chosen`, `confirmed`, `applied`, `recovery`, etc.), and whatever of `user_request`, `mode`, `structure_mode`, `targets`, `confirmation`, `notes` are relevant to that event — fields not supplied are omitted, not stored as null. Has no access to the conversation itself; the calling agent supplies the context by calling this at the points that matter, especially recording exactly what the user said to confirm a `reorganize` run. `--show` (or `read_sessions()` in the package) prints the log back. Added because every incident review of this project so far had to be reconstructed by hand from chat transcripts and screenshots rather than read off a record.

## What none of these scripts do

- None of them delete a file with content in it, under any mode or flag.
- None of them read or modify file *contents* — only location (and, for images/audio, metadata reads for classification, which don't alter the file).
- None of them recurse into a directory the structure report identified as already organized unless `--structure-mode reorganize` is explicitly passed.
- None of them reach inside a directory flagged by the Integrity Guard, in ANY mode, no exceptions.
- None of them move a file across a filesystem/mount boundary without `--allow-cross-filesystem` being explicitly passed.
