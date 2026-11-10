## Why

Archiving finished folders today means running `tar`/`zstd` by hand, picking a destination and name, deciding whether it's safe to delete the original, and then forgetting where it went. A small CLI that does compress → verify → store → record in one step, and can find and restore archives later, removes the manual steps and the risk of losing data.

## What Changes

- New Python CLI `arc` (Python ≥ 3.14, stdlib only), installable with `uv tool install .`.
- `arc add <folder> [--delete]`: compresses a folder into `<basename>-<UTC timestamp>.tar.zst` inside a configured local `ARCHIVE_DIR`, verifies it, and records it. The source folder is deleted only when `--delete` is passed **and** the archive has been verified and recorded.
- `arc list [--limit N]`: shows archive history, newest first.
- `arc search <term>`: finds history entries by source path or archive name.
- `arc restore <id> [--to DIR] [--force]`: verifies the archive checksum, then extracts it to its original path (or to `--to DIR`). Refuses to overwrite an existing path unless `--force` is given.
- Configuration via flags, environment variables, and a global `~/.config/arc/.env` file, so the tool behaves the same from any working directory.
- An append-only `history.jsonl` stored in `ARCHIVE_DIR`, next to the archives, recording add and restore events.

Out of scope: remote/cloud destinations, pruning or deleting archives, scheduled/rule-based runs, encryption.

## Capabilities

### New Capabilities
- `cli-config`: How configuration is resolved (flags > env > global `.env` > defaults), and failing when required settings are missing.
- `archive-create`: Compressing a folder into a verified `tar.zst` with an atomic write, plus optional source deletion.
- `archive-history`: The JSONL history format, recording events, and the `list`/`search` commands.
- `archive-restore`: Restoring an archive by id, with checksum verification, safe extraction, and overwrite protection.

### Modified Capabilities
<!-- none: greenfield project -->

## Impact

- New code: Python package (`src/arc/`), `pyproject.toml` with a console entry point, and stdlib `unittest` tests.
- Runtime requirement: Python ≥ 3.14 (for `compression.zstd` / `tarfile` zstd support). No third-party dependencies.
- Filesystem: writes under `ARCHIVE_DIR` only, except `restore` (writes to the target path) and `add --delete` (removes the source folder).
