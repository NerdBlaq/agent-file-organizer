# Default taxonomy and clustering heuristics

This is the starting-point rule set for Autonomous mode, and the default that Guided mode's config overrides selectively. Extension mapping is the first pass only — content signals refine it from there. Treat every rule here as a strong default, not a hard law; if a specific file clearly contradicts its extension-based bucket (e.g. a `.pdf` that's obviously a downloaded game manual, not a document), use judgment.

## Primary bucket by extension

| Category | Extensions |
|---|---|
| Pictures | jpg, jpeg, png, gif, bmp, webp, heic, heif, tiff, svg, raw, cr2, nef, avif |
| Videos | mp4, mkv, mov, avi, webm, flv, m4v, wmv |
| Music | mp3, flac, wav, ogg, oga, m4a, aac, wma, opus |
| Documents | pdf, docx, doc, odt, ods, odp, txt, md, rtf, xlsx, xls, csv, pptx, ppt, epub, mobi, azw, azw3 |
| Archives | zip, tar, gz, tgz, bz2, tbz2, xz, txz, 7z, rar, zst, tar.gz, tar.bz2, tar.xz |
| Installers | deb, rpm, appimage, run |
| DiskImages | iso, img, dmg |
| Fonts | ttf, otf, woff, woff2 |
| Code/Config | json, yaml, yml, toml, ini, conf (dotfiles filtered before this ever sees them) |
| Downloads (stay put) | anything that doesn't confidently match another bucket |

## Special case: .jar files

Not placed in a bucket by extension alone, because a `.jar` is as often a Minecraft mod as a Java application, and "unrecognized extension" was previously treating both cases identically — a useless label, since one has an obvious answer and the other doesn't. Filename is checked for mod-loader patterns (`fabric`, `forge`, `quilt`, `neoforge`, `-mc<version>`, `minecraft`); a match goes to `Downloads/Mods` at medium confidence. No match falls back to the ambiguous default at genuinely low confidence, with `Downloads/Mods` still offered as a candidate destination in case a visual/manual check confirms it anyway.

## Pictures clustering

- **Screenshots** — filename matches common screenshot patterns (`Screenshot`, `Screen Shot`, `scrot`, `Zrzut ekranu`, etc.) or dimensions matching a common screen resolution with no camera EXIF → `Pictures/Screenshots`
- **Camera/phone photos** — EXIF `DateTimeOriginal` and/or `Make`/`Model` present → `Pictures/Camera` (optionally subdivided by year if the user wants that in Guided mode, e.g. `Pictures/Camera/2026`)
- **People/family scenes** — this is a visual-content judgment call, not a metadata field. Only make this call by actually looking at the image (Step 3 of SKILL.md), and only up to the ambiguous-review cap. Never infer this from facial recognition, filenames alone, or guesswork at scale. Label the cluster `Pictures/People`, not "Family" — Claude has no reliable way to know who's related to whom, and mislabeling is worse than a neutral name the user can rename.
- **No confident signal** — leave in `Downloads/Unsorted` (or wherever the user's config says). Don't force a guess to avoid an "unsorted" pile; a wrong guess is more costly than an honest "I couldn't tell."

## Documents clustering

- **Receipts/invoices** — filename contains `receipt`, `invoice`, `order-confirmation`, etc., OR (for ambiguous images reviewed in Step 3) the image visually looks like a receipt/invoice layout → `Documents/Receipts`
- **Screenshots of text/documents** (not receipts) → `Documents/Screenshots`
- Everything else with a document extension → `Documents` top-level, unless the user's config defines finer clusters (e.g. by course code for a student, by client name for freelance work)

## Music clustering

- Read ID3/tag metadata (artist, album) if `mutagen` is available → `Music/<Artist>/<Album>`
- If tags are missing, fall back to parsing `Artist - Title.ext` from the filename → `Music/<Artist>/Unknown Album`
- If neither works, leave at `Music/Unsorted` rather than inventing an artist name

## Video clustering

- Filename cues for screen recordings (`Screen Recording`, `Zoom`, `OBS`, `Kazam`, app-export patterns) → `Videos/Screen Recordings`
- Everything else with a video extension → `Videos` (or `Videos/Clips` vs `Videos/Movies` only if the user's config defines a duration/size threshold — don't invent one, since there's no reliable duration read without `ffprobe`, which may not be installed)

## Extending an existing scheme vs. reorganizing it

`detect_existing_structure.py` (Step 0.5 in SKILL.md) figures out whether the user already has a scheme in a directory before any of the rules above get applied. When one is found, the rules above bend to match it rather than the other way around:

- A by-year Pictures library gets new photos filed into the matching (or newly created) year folder instead of a generic `Pictures/Camera`.
- An artist folder that's already flat (tracks loose, no album subfolder) stays flat for new tracks by that artist, instead of gaining a `Music/<Artist>/Unknown Album` folder the user never asked for.
- A custom-named folder (a trip, a project, an event) is left alone entirely in Extend mode — matching a photo to "Bali Trip" reliably requires actually knowing it's a Bali Trip photo, which metadata alone won't tell you, so these get surfaced during ambiguous review instead of guessed at.

Reorganize mode turns this protection off, which means files that are already inside an organized folder become eligible to move again under the plain taxonomy rules above — including cases where the folder was carrying information a tag or filename doesn't (e.g. an artist folder with no ID3 tags). Don't treat Reorganize as "the thorough version of Extend" — it's a different, higher-risk operation that can throw away information the user's own filing already captured, and it needs its own explicit confirmation, not a rollover from a general "looks good."

## What NOT to do

- Don't build clusters around inferred identity, relationships, health, or other sensitive attributes of people in photos — "People" is fine, speculative labels like specific names or relationships are not something Claude can know reliably from a photo alone.
- Don't recurse into and reorganize deeply nested folders the user already organized themselves (e.g. a `Downloads/Work Archive 2024/` folder with its own internal structure) unless they explicitly ask — respect existing manual organization.
- Don't rename files themselves as part of sorting unless the user asks for that separately; moving is the job, renaming is a different, riskier operation.
