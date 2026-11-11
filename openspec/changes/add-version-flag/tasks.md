## 1. Implementation

- [x] 1.1 Add `version_string()` to `cli.py`: distribution version plus source from `direct_url.json` (archive file name, local path with editable marker, short git commit), falling back to the plain version or `arc (not installed)`
- [x] 1.2 Register `--version` with argparse `action="version"`

## 2. Tests

- [x] 2.1 Unit tests for wheel, local, editable, git, no record, malformed record, not installed
- [x] 2.2 CLI test: `arc --version` prints one line to stdout, exits 0, works with `ARCHIVE_DIR` unset

## 3. Verify

- [x] 3.1 `PYTHONPATH=src python3 -m unittest discover -s tests` passes
- [x] 3.2 Install the local folder with uv and check the output shows `local: <path>`
