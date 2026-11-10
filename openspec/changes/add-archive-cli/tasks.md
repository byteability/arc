## 1. Project setup

- [x] 1.1 Create `pyproject.toml` (name `arc`, `requires-python = ">=3.14"`, no dependencies, console script `arc = "arc.cli:main"`, src layout)
- [x] 1.2 Create `src/arc/__init__.py` and empty `cli.py`, `config.py`, `archiver.py`, `history.py`, `restore.py`
- [x] 1.3 Create `tests/` with a shared helper that builds temp `ARCHIVE_DIR`, source folders and a fake `HOME`
- [x] 1.4 Add `.gitignore` (venv, `__pycache__`, build artifacts) and a short README (install, config, usage)

## 2. Configuration (cli-config)

- [x] 2.1 Implement the `.env` parser (KEY=VALUE, `#` comments, blank lines, matching quotes, missing file OK)
- [x] 2.2 Implement resolution flags > env > `~/.config/arc/.env` > defaults, ignoring the cwd `.env`
- [x] 2.3 Validate: `ARCHIVE_DIR` required, must exist, must be a directory, `~`-expanded and absolute; `ZSTD_LEVEL` integer, default 10
- [x] 2.4 Tests for precedence, ignoring the cwd `.env`, parser edge cases, and every validation error

## 3. History (archive-history)

- [x] 3.1 Implement `append(record)`: one JSON line, single `os.write` on an `O_APPEND` fd, then fsync
- [x] 3.2 Implement `read()`: yields records, skips malformed lines with a stderr warning including the line number
- [x] 3.3 Implement the effective view: `add` records with `source_deleted` overridden by later `delete_failed` events
- [x] 3.4 Implement `list(limit)` and `search(term)` (case-insensitive on `source_path` and `id`), newest first
- [x] 3.5 Tests: file creation, line integrity, malformed-line skip, delete_failed override, limit, search matching

## 4. Archive creation (archive-create)

- [x] 4.1 Validate the source: exists, is a directory, is not `ARCHIVE_DIR`, neither contains nor is inside `ARCHIVE_DIR`
- [x] 4.2 Compute the name/id `<basename>-<YYYYMMDDTHHMMSSZ>`; fail on an existing final file
- [x] 4.3 Write the tar.zst to `ARCHIVE_DIR/.tmp/<id>.part` with a filter that excludes `.DS_Store` and counts entries and regular-file bytes; symlinks not dereferenced
- [x] 4.4 fsync the file, compute SHA-256, re-read every member, and compare the entry count
- [x] 4.5 `os.replace` to the final name, then fsync `ARCHIVE_DIR`; on any exception remove the `.part` and re-raise
- [x] 4.6 Append the `add` record (all spec fields); if that fails, error out with the archive path and do not delete
- [x] 4.7 With `--delete`: `shutil.rmtree` the source; on failure append `delete_failed` and exit non-zero
- [x] 4.8 Tests: happy path round trip, name collision, invalid sources, `.DS_Store` exclusion, symlink preserved, simulated failure leaves no final file or `.part`, `--delete` success, history-append failure keeps source, rmtree failure logs `delete_failed`

## 5. Restore (archive-restore)

- [x] 5.1 Look up the `add` record by id; errors for an unknown id or a missing archive file
- [x] 5.2 Verify SHA-256 against the record before touching the target
- [x] 5.3 Resolve the target (`dirname(source_path)` or `--to DIR`, created if needed); refuse if `<target>/<basename>` exists unless `--force`
- [x] 5.4 Extract with `extractall(filter="tar")`; append the `restore` event on success
- [x] 5.5 Tests: restore to original, `--to`, refusal without `--force`, `--force` overwrite, checksum mismatch writes nothing, traversal member rejected, absolute symlink restored

## 6. CLI wiring

- [x] 6.1 argparse with subcommands `add`, `list`, `search`, `restore` and a global `--archive-dir` flag
- [x] 6.2 Map errors to exit codes (0 ok, 1 operational, 2 usage/config), with stderr messages prefixed `arc: error:`
- [x] 6.3 Format `list`/`search` rows: id, timestamp, source path, human-readable size, deleted marker
- [x] 6.4 End-to-end tests invoking `main([...])` for each subcommand

## 7. Verify

- [x] 7.1 Run `PYTHONPATH=src python3 -m unittest discover -s tests` and get it green
- [x] 7.2 `uv tool install --python ">=3.14" .` then a manual smoke test: add → list → search → restore `--to` on a scratch folder
