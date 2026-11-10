## Context

Greenfield, single-user CLI for macOS, run manually against one folder at a time. Python 3.15 is installed locally, and `uv` is available for installing. The archive destination is a local directory (possibly an external disk mounted under `/Volumes`). The one irreversible operation is the optional source deletion, so the design is built around never reaching it unless everything before it has succeeded.

## Goals / Non-Goals

**Goals:**
- Compress → verify → atomically store → record → optionally delete, in that order.
- Behave the same from any working directory.
- Zero third-party dependencies.
- History that is human-readable, greppable, and travels with the archives.
- Restore that cannot silently overwrite data or extract outside its target.

**Non-Goals:**
- Remote destinations, pruning, scheduling, encryption, multi-user use or concurrent runs.
- Preserving macOS extended attributes or resource forks.
- Incremental or deduplicated backups (use restic/borg for that).

## Decisions

**Language/runtime: Python ≥ 3.14, stdlib only.** `tarfile` supports `w:zst`/`r:zst` via `compression.zstd` from 3.14. *Alternatives:* the `zstandard` package (adds a dependency) or shelling out to `tar --zstd`/`zstd` (bsdtar flags are platform-specific, and errors are harder to handle). Trade-off: hosts running Python < 3.14 can't run the tool; `requires-python = ">=3.14"` makes that explicit.

**Layout:**
```
pyproject.toml            console script: arc = "arc.cli:main"
src/arc/
  cli.py      argparse, subcommands, exit codes
  config.py   precedence resolution + .env parser
  archiver.py create + verify + atomic finalize
  history.py  append/read JSONL, list/search
  restore.py  lookup, checksum, safe extract
tests/        unittest, temp dirs only
```
Flat modules, no classes beyond small dataclasses (`Config`, `Record`).

**Config: flags > env > `~/.config/arc/.env` > defaults; no cwd `.env`.** A cwd file would make behavior depend on location. The parser is about 15 lines (`KEY=VALUE`, comments, quotes) rather than a `python-dotenv` dependency. `ARCHIVE_DIR` has no default, so the tool fails loudly. `XDG_CONFIG_HOME` is not honoured (YAGNI on macOS).

**Command name: `arc`.** Short, and no clash on the current PATH. `archive` was considered too generic. Renaming later is a one-line change in `pyproject.toml`.

**Archive name/id: `<basename>-<YYYYMMDDTHHMMSSZ>`.** It is readable, sorts by time, and doubles as the history id, so no separate ULID is needed. If the name collides (same folder twice in one second), the command fails rather than adding suffix logic.

**Atomic write in `ARCHIVE_DIR/.tmp/`.** Using the same filesystem as the final location guarantees `os.replace` is atomic. Sequence: open `.part` → `tarfile.open(fileobj, "w:zst", level=…)` → add the folder with a filter that drops `.DS_Store` and counts entries → close → `fsync(file)` → verify → `os.replace` → `fsync(dir)`. Any exception removes the `.part` file. Symlinks are stored as links (`tarfile` default with `dereference=False`).

**Verification: SHA-256 plus a full read-back of the tar.** Iterating every member forces full decompression, which catches truncation or corruption. The entry count is compared against what the add filter counted. The SHA-256 is computed over the final `.part` bytes, which are identical after rename. *Alternative:* extracting to a temp dir and diffing is more thorough, but doubles I/O and disk use; rejected for v1.

**Order: finalize → append history → delete.** If the history append fails after finalize, the archive is orphaned but the source is intact, and the error message prints the archive path. If the delete fails after the append, the record says `source_deleted: false` and the source remains. Both failure modes are harmless. *Alternative:* a `pending` record followed by an `ok` record needs a two-phase reconciliation; rejected as overbuilt.

Because the `add` record is written before deletion, it records `source_deleted` as the `--delete` intent. If `shutil.rmtree` then fails, the tool appends a `delete_failed` event and exits non-zero, and readers let that event override the flag. This keeps the log append-only and the common case down to a single record. *Alternative:* always write `false` and append a `deleted` event on success; that's equivalent but makes every `--delete` run write two lines.

**History: JSONL in `ARCHIVE_DIR`, one `os.write` on an `O_APPEND` fd plus fsync.** Writes of a few hundred bytes are effectively atomic on local filesystems, so no locking is needed given manual, single-user use. Readers skip malformed lines with a warning. `archive_path` is stored relative to `ARCHIVE_DIR`, so the whole directory can be moved or remounted.

**Restore: sha256 check → target check → `extractall(filter="tar")`.** The `tar` filter blocks absolute member names, `..`, and writes that resolve outside the destination (including through extracted links), and strips setuid/setgid bits. *Alternative rejected:* the `data` filter also refuses absolute or escaping symlinks, which makes folders containing e.g. Python venvs unrestorable. The archives are self-created, so the `tar` filter's trust level fits. The target is `dirname(source_path)` by default, or `--to DIR`, and the archive's single top-level folder lands as `<target>/<basename>`. Without `--force`, the tool refuses if `<target>/<basename>` exists. With `--force`, it extracts over the top (files at the same paths are overwritten, extras are kept).

**Output/exit codes:** `0` success, `1` operational error, `2` usage/config error (argparse's convention). Errors go to stderr, prefixed `arc: error:`.

## Risks / Trade-offs

- [`ARCHIVE_DIR` on an unmounted external disk could silently become a local dir under `/Volumes`] → The tool never creates `ARCHIVE_DIR`; it must already exist (one-time `mkdir` by the user).
- [Large folders need double disk space during the `.part` write] → Accepted; free space is not pre-checked (the source size estimate is unreliable after compression).
- [xattrs, ACLs and resource forks are lost] → Documented non-goal; macOS Finder tags and quarantine flags won't survive a round trip.
- [Verification doesn't prove file-level fidelity] → It proves the archive is complete and readable and matches the entry count. A content diff is out of scope.
- [Concurrent runs could interleave history lines] → Single-line O_APPEND writes make interleaving unlikely; documented as unsupported.
- [The `delete_failed` event adds a third event type] → Small cost in exchange for never lying in the log.

## Migration Plan

None (new tool). Install with `uv tool install --python ">=3.14" .` from the repo (uv may otherwise pick an older default interpreter); uninstall with `uv tool uninstall arc`. Create the archive directory, then `~/.config/arc/.env` with `ARCHIVE_DIR=…`.

## Open Questions

- None blocking. Revisit the command name if `arc` clashes with something installed later.
