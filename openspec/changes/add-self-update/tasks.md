## 1. Shared install info

- [x] 1.1 Create `src/arc/install.py` with `installed()` (version, source kind, detail) and `version_string()`; `cli.py` imports `version_string` from it
- [x] 1.2 Point the existing `--version` tests at `install`; output unchanged

## 2. Update

- [x] 2.1 Create `src/arc/update.py`: `UpdateError`, `_run` (missing binary / non-zero exit → `UpdateError` with stderr), numeric version compare
- [x] 2.2 `update(force)`: not installed / not a uv tool install checks, latest tag via `gh release view`, skip or refuse rules, download to a temp dir, verify against `SHA256SUMS`, `uv tool install --force --python ">=3.14" <wheel>`
- [x] 2.3 `arc update [--force]` subcommand, handled before config is loaded; `UpdateError` → exit 1

## 3. Tests

- [x] 3.1 Unit tests with a fake runner: outdated → installs; up to date / newer → skip; local without/with `--force`; checksum mismatch; wheel not in sums; no sums; not installed; not a uv tool install; version compare
- [x] 3.2 `_run` tests: missing binary, non-zero exit with stderr; CLI test without `ARCHIVE_DIR`

## 4. Docs and verify

- [x] 4.1 README usage and CLAUDE.md layout updated
- [x] 4.2 `PYTHONPATH=src python3 -m unittest discover -s tests` passes
- [x] 4.3 Real end-to-end with `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` in a temp dir: local install refuses without `--force`, `--force` installs the latest release, checksum verified
