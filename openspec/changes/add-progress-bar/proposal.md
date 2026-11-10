## Why

`arc add` and `arc restore` can run for minutes on large folders, and right now they print nothing until they finish. It's impossible to tell whether the tool is working, stuck, or how long is left.

## What Changes

- `arc add` shows a progress bar for each phase on stderr: scanning the folder, compressing, computing the checksum, and verifying.
- `arc restore` shows a progress bar for checking the checksum and for extracting.
- Each bar shows the phase, a 20-character bar, the percentage, and processed/total size. Scanning shows a running total because its size isn't known up front.
- Progress appears only when stderr is an interactive terminal. In pipes, redirects, cron and CI there's no extra output, and stdout stays exactly as it is now.
- `list` and `search` are unchanged.

## Capabilities

### New Capabilities
- `cli-progress`: When and where progress is shown, its phases, its format, and how it behaves on errors.

### Modified Capabilities
<!-- none: existing requirements are unchanged; progress is additive and stderr-only -->

## Impact

- New module `src/arc/progress.py`. `archiver.create` and `restore.restore` take an optional progress argument; the CLI passes one in.
- `archiver` adds folder entries itself (same order and filtering as `tar.add`) so it can count bytes as they're read, and adds a quick pre-scan to get the total size.
- `restore` reads the archive as a stream so extraction progress can be measured.
- Still stdlib only; no new dependencies.
