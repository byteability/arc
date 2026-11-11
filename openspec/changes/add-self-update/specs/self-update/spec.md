## ADDED Requirements

### Requirement: Update to the latest release
`arc update` SHALL look up the latest release of `byteability/arc`. If the installed version came from a release file and is older, it SHALL download that release's wheel and `SHA256SUMS`, verify the wheel, install it with `uv tool install --force`, and print `updated arc <old> → <new>`. The command SHALL NOT require `ARCHIVE_DIR`.

#### Scenario: Newer release available
- **WHEN** arc 0.1.0 is installed from `arc-0.1.0-py3-none-any.whl` and the latest release is v0.2.0
- **THEN** arc 0.2.0 is installed and `updated arc 0.1.0 → 0.2.0` is printed, with exit status 0

#### Scenario: No configuration
- **WHEN** `ARCHIVE_DIR` is unset and the user runs `arc update`
- **THEN** the command runs normally

### Requirement: Skip when up to date
If the installed version came from a release file and is equal to or newer than the latest release, `arc update` SHALL print `arc <version> is already up to date`, download nothing, and exit 0. Versions SHALL be compared numerically (0.10.0 is newer than 0.9.0).

#### Scenario: Already latest
- **WHEN** arc 0.2.0 is installed from its release wheel and the latest release is v0.2.0
- **THEN** nothing is downloaded and the up-to-date message is printed

### Requirement: Non-release installs need --force
If `arc` was installed from a local folder, git, or an unrecorded source, `arc update` without `--force` SHALL explain that the version can't be compared, suggest `arc update --force`, download nothing, and exit with status 1. With `--force`, it SHALL install the latest release whatever is installed.

#### Scenario: Local folder install
- **WHEN** arc was installed from the working folder and the user runs `arc update`
- **THEN** the command exits 1 with a message that mentions `--force`, and nothing is installed

#### Scenario: Forced
- **WHEN** the user runs `arc update --force`
- **THEN** the latest release is downloaded, verified and installed

### Requirement: Verify before installing
The system SHALL install only a wheel whose SHA-256 matches its entry in the release's `SHA256SUMS`. It SHALL refuse with exit status 1, installing nothing, if the release has no single wheel, has no `SHA256SUMS`, doesn't list the wheel, or the checksum doesn't match.

#### Scenario: Checksum mismatch
- **WHEN** the downloaded wheel's SHA-256 differs from `SHA256SUMS`
- **THEN** the command exits 1 with a checksum error, and `uv tool install` is not run

### Requirement: Preconditions
`arc update` SHALL fail with exit status 1 and a clear message, changing nothing, when: `arc` is not installed (running from source); `arc` is not installed with `uv tool`; `gh` or `uv` is not on PATH; or a `gh`/`uv` command fails (the message SHALL include its error output).

#### Scenario: Not a uv tool install
- **WHEN** `arc` runs from an environment outside `uv tool dir`
- **THEN** the command exits 1 telling the user to update it the way they installed it

#### Scenario: gh missing
- **WHEN** `gh` is not on PATH
- **THEN** the command exits 1 saying `gh` is not installed or not on PATH
