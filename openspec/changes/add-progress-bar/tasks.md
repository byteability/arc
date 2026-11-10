## 1. Progress module

- [x] 1.1 Create `src/arc/progress.py` with `Progress` (`phase`, `advance`, `close`), TTY detection, throttling, 0–100% clamping, zero-total handling, and a byte-counting reader wrapper
- [x] 1.2 Move `human_size` from `cli.py` to `progress.py` and import it in `cli.py`
- [x] 1.3 Tests: disabled when not a TTY (no output), line format, newline at phase end, zero total, `close()` mid-phase, throttling

## 2. Archive creation progress

- [x] 2.1 Add `progress` parameter to `archiver.create`; pre-scan regular-file bytes (skip `.DS_Store`, don't follow symlinks) when enabled
- [x] 2.2 Replace `tar.add` with a recursive walk using `gettarinfo`/filter/`addfile` and a counting reader for regular files
- [x] 2.3 Report `checksum` progress in `sha256_file` and `verifying` progress via a counted reader under `ZstdFile`
- [x] 2.4 Tests: member list identical to `tar.add` output; phases appear in order on a fake TTY; all existing archiver tests still pass

## 3. Restore progress

- [x] 3.1 Add `progress` parameter to `restore.restore`; report `checksum` and `extracting` phases
- [x] 3.2 Switch extraction to stream mode over a counted `ZstdFile`, keeping the `tar` filter and the `--force` symlink handling
- [x] 3.3 Tests: phases on a fake TTY; all existing restore tests still pass

## 4. CLI

- [x] 4.1 Create a `Progress` for stderr in `run` and pass it to `create`/`restore`; call `close()` before printing errors
- [x] 4.2 Tests: stdout unchanged and stderr empty when not a TTY; error message starts on its own line

## 5. Verify

- [x] 5.1 `PYTHONPATH=src python3 -m unittest discover -s tests` passes
- [x] 5.2 Manual check in a real terminal: `arc add` and `arc restore --to` on a folder of a few hundred MB
