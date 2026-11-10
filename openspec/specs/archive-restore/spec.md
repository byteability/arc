# archive-restore Specification

## Purpose
TBD - created by archiving change add-archive-cli. Update Purpose after archive.
## Requirements
### Requirement: Restore by id
`arc restore <id>` SHALL look up the `add` record with that id in history and extract its archive. By default the archived top-level folder SHALL be restored to the original `source_path`.

#### Scenario: Restore to original location
- **WHEN** `~/work/proj` was archived with `--delete` and the user runs `arc restore proj-20261110T101530Z`
- **THEN** `~/work/proj` exists again with the archived contents

#### Scenario: Unknown id
- **WHEN** no `add` record has the given id
- **THEN** the command exits non-zero with an error, and nothing is written

#### Scenario: Archive file missing
- **WHEN** the record exists but its archive file is not in `ARCHIVE_DIR`
- **THEN** the command exits non-zero with an error naming the expected path

### Requirement: Alternate target
With `--to DIR`, the system SHALL restore the top-level folder into `DIR` (producing `DIR/<basename>`), creating `DIR` if needed.

#### Scenario: Restore elsewhere
- **WHEN** the user runs `arc restore proj-20261110T101530Z --to /tmp/r`
- **THEN** `/tmp/r/proj` contains the archived contents, and the original location is not touched

### Requirement: Overwrite protection
If the restore target path already exists, the system SHALL refuse and exit non-zero unless `--force` is passed. With `--force`, extracted files SHALL overwrite existing files at the same paths; other existing files SHALL be left in place.

#### Scenario: Target exists
- **WHEN** `~/work/proj` exists and the user runs `arc restore <id>` without `--force`
- **THEN** the command exits non-zero, and nothing is modified

#### Scenario: Forced
- **WHEN** `~/work/proj` exists and the user passes `--force`
- **THEN** archived files are written over the existing ones at the same paths

### Requirement: Verify checksum before extract
The system SHALL compute the archive's SHA-256 and compare it with the recorded `sha256` before extracting anything. On mismatch it SHALL exit non-zero without writing any files.

#### Scenario: Corrupted archive
- **WHEN** the archive file's bytes have changed since it was recorded
- **THEN** the command reports a checksum mismatch, exits non-zero, and extracts nothing

### Requirement: Safe extraction
The system SHALL extract using `tarfile`'s `tar` filter, rejecting absolute member paths, `..` traversal, and any write that would resolve outside the destination, and stripping setuid/setgid bits. Symlinks SHALL be restored with their original targets, including absolute targets and targets outside the destination.

#### Scenario: Malicious member
- **WHEN** an archive contains a member named `../../evil`
- **THEN** extraction fails with an error, and no file is written outside the destination

#### Scenario: Absolute symlink restored
- **WHEN** the archived folder contained `link -> /etc/hosts`
- **THEN** after restore, `link` is a symlink to `/etc/hosts`

