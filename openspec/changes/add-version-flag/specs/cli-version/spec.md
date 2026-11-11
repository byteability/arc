## ADDED Requirements

### Requirement: Version flag
`arc --version` SHALL print one line to stdout of the form `arc <version>` or `arc <version> (<source>)` and exit with status 0, without loading configuration. `<version>` SHALL be the installed distribution's version.

#### Scenario: Works without configuration
- **WHEN** `ARCHIVE_DIR` is unset and the user runs `arc --version`
- **THEN** the version line is printed and the exit status is 0

### Requirement: Install source
When the installation recorded its source (PEP 610 `direct_url.json`), the system SHALL append it in parentheses: the file name for an installed archive (e.g. a wheel), `local: <path>` for a directory install (`local, editable: <path>` if editable), and `git: <first 7 characters of the commit>` for a git install. If no source is recorded, or the record can't be read, the system SHALL print only `arc <version>`.

#### Scenario: Release wheel
- **WHEN** `arc` was installed from `arc-0.1.0-py3-none-any.whl`
- **THEN** `arc --version` prints `arc 0.1.0 (arc-0.1.0-py3-none-any.whl)`

#### Scenario: Local folder
- **WHEN** `arc` was installed from the directory `/Users/me/src/arc`
- **THEN** `arc --version` prints `arc 0.1.0 (local: /Users/me/src/arc)`

#### Scenario: Git commit
- **WHEN** `arc` was installed from git at commit `1a2b3c4d…`
- **THEN** `arc --version` prints `arc 0.1.0 (git: 1a2b3c4)`

#### Scenario: Index install or unreadable record
- **WHEN** there is no `direct_url.json`, or it isn't valid JSON
- **THEN** `arc --version` prints `arc 0.1.0`

### Requirement: Not installed
When `arc` runs without being installed (e.g. from source with `PYTHONPATH=src`), `arc --version` SHALL print `arc (not installed)`.

#### Scenario: Source checkout
- **WHEN** no `arc` distribution metadata is found
- **THEN** `arc --version` prints `arc (not installed)` and exits 0
