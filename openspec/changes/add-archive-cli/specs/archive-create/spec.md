## ADDED Requirements

### Requirement: Archive a folder
`arc add <folder>` SHALL create a zstd-compressed tar archive of the folder in `ARCHIVE_DIR`, named `<basename>-<YYYYMMDDTHHMMSSZ>.tar.zst` using the UTC time, with the folder's basename as the single top-level entry in the tar.

#### Scenario: Successful archive
- **WHEN** the user runs `arc add ~/work/proj` at 2026-11-10 10:15:30 UTC
- **THEN** `ARCHIVE_DIR/proj-20261110T101530Z.tar.zst` exists, extracting it yields a `proj/` directory with the original contents, and the command prints the archive id and path

#### Scenario: Name collision
- **WHEN** an archive with the computed name already exists
- **THEN** the command fails with a non-zero exit status, writes nothing, and leaves the existing archive untouched

### Requirement: Reject invalid sources
The system SHALL refuse to archive when the path does not exist, is not a directory, is itself a symlink, is `ARCHIVE_DIR` itself, or contains or is contained in `ARCHIVE_DIR`.

#### Scenario: Source is a symlink
- **WHEN** `./link` is a symlink to a directory and the user runs `arc add ./link`
- **THEN** the command exits non-zero, asks for the real path, and writes nothing

#### Scenario: Source is a file
- **WHEN** the user runs `arc add notes.txt`
- **THEN** the command exits non-zero with an error, and nothing is written

#### Scenario: Source contains the archive dir
- **WHEN** `ARCHIVE_DIR` is `~/data/archive` and the user runs `arc add ~/data`
- **THEN** the command exits non-zero with an error, and nothing is written

### Requirement: Atomic write
The system SHALL write the archive to a temporary `.part` file under `ARCHIVE_DIR/.tmp/`, fsync it, and only then rename it to its final name. On any failure the `.part` file SHALL be removed and no final-named file SHALL exist.

#### Scenario: Interrupted compression
- **WHEN** compression fails partway (e.g. a read error or disk full)
- **THEN** no file with the final archive name exists, the `.part` file is removed, the source is untouched, and the command exits non-zero

### Requirement: Verify before finalizing
Before renaming, the system SHALL compute the SHA-256 of the archive file and read the archive back in full, confirming that the number of entries matches what was written. A verification failure SHALL be handled like any other failure under the atomic-write requirement.

#### Scenario: Verification passes
- **WHEN** the archive reads back with the expected entry count
- **THEN** the archive is renamed to its final name, and its SHA-256 is recorded in history

### Requirement: Archive contents rules
The system SHALL store symlinks as symlinks without following them, SHALL exclude files named `.DS_Store`, and is NOT REQUIRED to preserve extended attributes.

#### Scenario: Symlink inside folder
- **WHEN** the folder contains a symlink `link -> /etc/hosts`
- **THEN** the archive contains a symlink entry `link` pointing to `/etc/hosts`, not the file contents

#### Scenario: .DS_Store excluded
- **WHEN** the folder contains `.DS_Store` files at any depth
- **THEN** none appear in the archive

### Requirement: Optional source deletion
The source folder SHALL be deleted only when `--delete` is passed, and only after the archive has been finalized and its history record has been successfully appended. If deletion fails, the system SHALL append a `delete_failed` history event, report the error, exit non-zero, and leave the archive and its original record in place.

#### Scenario: Default keeps source
- **WHEN** the user runs `arc add ./proj` without `--delete`
- **THEN** `./proj` still exists after success

#### Scenario: Delete after success
- **WHEN** the user runs `arc add ./proj --delete` and archiving, verification and history append all succeed
- **THEN** `./proj` is removed, and the history record has `source_deleted: true`

#### Scenario: Deletion fails
- **WHEN** archiving succeeds with `--delete` but removing `./proj` fails (e.g. permission denied)
- **THEN** the command exits non-zero, a `delete_failed` event with the archive id is appended, and the archive remains

#### Scenario: Archive failure never deletes
- **WHEN** the user runs `arc add ./proj --delete` and compression or verification fails
- **THEN** `./proj` is untouched

#### Scenario: History append failure never deletes
- **WHEN** the archive is finalized but appending to `history.jsonl` fails
- **THEN** `./proj` is untouched, the command exits non-zero, and the error names the archive path
