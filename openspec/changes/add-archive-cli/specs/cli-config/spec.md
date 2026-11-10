## ADDED Requirements

### Requirement: Configuration precedence
The system SHALL resolve each setting from, in order of precedence: command-line flags, process environment variables, the global config file `~/.config/arc/.env`, then built-in defaults. The system SHALL NOT read a `.env` file from the current working directory.

#### Scenario: Flag overrides environment and file
- **WHEN** `ARCHIVE_DIR` is set in `~/.config/arc/.env` to `/a`, in the environment to `/b`, and `--archive-dir /c` is passed
- **THEN** the system uses `/c`

#### Scenario: Environment overrides file
- **WHEN** `ARCHIVE_DIR` is `/a` in the global file and `/b` in the environment, and no flag is passed
- **THEN** the system uses `/b`

#### Scenario: Working directory .env is ignored
- **WHEN** the current working directory contains a `.env` with `ARCHIVE_DIR=/x` and no other source sets it
- **THEN** the system does not use `/x`

### Requirement: Global config file format
The system SHALL parse the global config file as `KEY=VALUE` lines. It SHALL ignore blank lines and lines starting with `#`, and SHALL strip one pair of matching surrounding single or double quotes from values. A missing config file SHALL NOT be an error.

#### Scenario: Comments and quotes
- **WHEN** the file contains `# comment`, a blank line, and `ARCHIVE_DIR="/Volumes/Data/archive"`
- **THEN** `ARCHIVE_DIR` resolves to `/Volumes/Data/archive`

#### Scenario: Missing file
- **WHEN** `~/.config/arc/.env` does not exist and `ARCHIVE_DIR` is set in the environment
- **THEN** the command runs normally

### Requirement: Supported settings
The system SHALL support `ARCHIVE_DIR` (required, no default) and `ZSTD_LEVEL` (integer, default `10`). `ARCHIVE_DIR` SHALL be expanded (`~`) and resolved to an absolute path.

#### Scenario: Default compression level
- **WHEN** `ZSTD_LEVEL` is not set anywhere
- **THEN** archives are compressed at level 10

### Requirement: Fail on missing or invalid configuration
The system SHALL exit with a non-zero status and a clear error message, without performing any filesystem changes, when `ARCHIVE_DIR` is unset, does not exist, or is not a directory, or when `ZSTD_LEVEL` is not a valid integer. The system SHALL NOT create `ARCHIVE_DIR`; this prevents silently writing to the internal disk when an external volume is unmounted.

#### Scenario: ARCHIVE_DIR unset
- **WHEN** no source provides `ARCHIVE_DIR` and the user runs `arc add ./proj`
- **THEN** the command exits non-zero with a message naming `ARCHIVE_DIR` and `~/.config/arc/.env`, and nothing is written

#### Scenario: ARCHIVE_DIR missing
- **WHEN** `ARCHIVE_DIR` is `/Volumes/Backup/archive` and that volume is not mounted
- **THEN** the command exits non-zero with an error naming the path, and no directory is created
