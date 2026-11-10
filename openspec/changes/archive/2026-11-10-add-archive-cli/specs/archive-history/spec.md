## ADDED Requirements

### Requirement: History file location and format
The system SHALL keep history in `ARCHIVE_DIR/history.jsonl`, with one JSON object per line, appended only. Existing lines SHALL never be rewritten.

#### Scenario: First archive creates history
- **WHEN** `history.jsonl` does not exist and an archive is created
- **THEN** `history.jsonl` is created and contains exactly one line

### Requirement: Add event record
After each successful `add`, the system SHALL append a record with: `event: "add"`, `id` (the archive filename without `.tar.zst`), `timestamp` (UTC ISO 8601), `host`, `user`, `source_path` (absolute), `archive_path` (relative to `ARCHIVE_DIR`), `format: "tar.zst"`, `size_before` (bytes of regular files archived), `size_after` (archive bytes), `file_count`, `sha256`, and `source_deleted` (boolean).

#### Scenario: Record fields
- **WHEN** `arc add ~/work/proj` succeeds
- **THEN** the appended line parses as JSON, contains all listed fields, and `source_path` is the absolute path of `~/work/proj`

#### Scenario: Delete reflected
- **WHEN** `--delete` was not passed
- **THEN** `source_deleted` is `false`

### Requirement: Restore event record
After each successful `restore`, the system SHALL append a record with `event: "restore"`, `id` of the restored archive, `timestamp`, `host`, `user`, and `target_path` (absolute).

#### Scenario: Restore logged
- **WHEN** `arc restore proj-20261110T101530Z` succeeds
- **THEN** a line with `event: "restore"` and that `id` is appended

### Requirement: Delete-failed event record
When `--delete` was requested but the source removal failed, the system SHALL append a record with `event: "delete_failed"`, `id`, `timestamp`, and `error` (message). `list` and `search` SHALL show such archives as source not deleted.

#### Scenario: Failed delete shown correctly
- **WHEN** an `add` record has `source_deleted: true`, and a later `delete_failed` record has the same id
- **THEN** `arc list` shows that archive without the deleted marker

### Requirement: Single-write append
Each record SHALL be serialized to a single line and written with one append-mode write followed by fsync.

#### Scenario: Line integrity
- **WHEN** any record is appended
- **THEN** the file ends with a newline, and every line parses as JSON

### Requirement: Tolerate malformed lines when reading
When reading history, the system SHALL skip lines that fail to parse as JSON and emit a warning to stderr naming the line number.

#### Scenario: Corrupt line
- **WHEN** line 3 of `history.jsonl` is not valid JSON
- **THEN** `arc list` shows the other entries and warns about line 3 on stderr

### Requirement: List archives
`arc list [--limit N]` SHALL print `add` events newest first, one per line, showing id, timestamp, source path, archive size, and a marker when the source was deleted. `--limit` SHALL cap the number of rows. An empty or missing history SHALL print nothing and exit 0.

#### Scenario: Limit
- **WHEN** there are 10 archives and the user runs `arc list --limit 3`
- **THEN** the 3 newest archives are printed

### Requirement: Search archives
`arc search <term>` SHALL print `add` events whose `source_path` or `id` contains `term`, case-insensitively, in the same format as `list`. No matches SHALL exit 0 with no output.

#### Scenario: Match on path
- **WHEN** an archive has `source_path` `/Users/me/Work/ClientX` and the user runs `arc search clientx`
- **THEN** that entry is printed
