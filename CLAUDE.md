# Claude instructions

## Project Definition

`arc`: a Python CLI that archives a folder to `tar.zst` in a local `ARCHIVE_DIR`, records it in an
append-only `history.jsonl` next to the archives, and supports `list`, `search` and `restore`.
The source folder is deleted only with `--delete`, after the archive is verified and recorded.

## Stack and constraints

- Python >= 3.14, stdlib only (zstd via `compression.zstd`/`tarfile`). Do not add runtime dependencies.
- Layout: `src/arc/` (`cli`, `config`, `archiver`, `history`, `restore`), tests in `tests/` (stdlib `unittest`).
- Config precedence: `--archive-dir` flag > env > `~/.config/arc/.env` > defaults. A cwd `.env` is ignored by design.

## Commands

- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests`
- Install: `uv tool install --python ">=3.14" .` (plain `uv tool install .` may pick an older Python)

## Invariants (do not break)

- Never delete the source unless the archive is finalized (atomic rename from `.tmp/*.part`), verified, and its history line is appended.
- History is append-only; never rewrite existing lines.
- Never create `ARCHIVE_DIR` (protects against writing to the internal disk when an external volume is unmounted).
- Restore verifies the sha256 before extracting and uses the `tar` filter (not `data`, which rejects absolute symlinks).

## Specs

Requirements and design live in `openspec/` (change `add-archive-cli`). Update the specs when behavior changes.
