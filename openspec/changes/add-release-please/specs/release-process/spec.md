## ADDED Requirements

### Requirement: Version derived from commits
The next version SHALL be derived from Conventional Commit messages merged to `main` since the last release. While the version is below 1.0.0: `fix:` and other non-feature types SHALL bump the patch version, `feat:` SHALL bump the minor version, and breaking changes (`!` or `BREAKING CHANGE:`) SHALL bump the minor version.

#### Scenario: Feature pre-1.0
- **WHEN** the last release is 0.1.0 and a `feat:` commit is merged to `main`
- **THEN** the release PR proposes 0.2.0

#### Scenario: Fix only
- **WHEN** the last release is 0.2.0 and only `fix:` commits are merged
- **THEN** the release PR proposes 0.2.1

#### Scenario: Breaking change pre-1.0
- **WHEN** the last release is 0.2.1 and a `feat!:` commit is merged
- **THEN** the release PR proposes 0.3.0

### Requirement: Release PR
On every push to `main` with releasable commits, the system SHALL open or update a single release PR that sets `version` in `pyproject.toml` and updates `CHANGELOG.md`. Nothing SHALL be tagged or released until that PR is merged.

#### Scenario: PR kept up to date
- **WHEN** two more `fix:` commits are merged while a release PR is open
- **THEN** the same PR is updated to include them in its changelog and version

### Requirement: Release on merge
Merging the release PR SHALL create the tag `v<version>` and a GitHub release with the changelog section as notes. The workflow SHALL then run the test suite, build the sdist and wheel, and attach them together with a `SHA256SUMS` file to that release.

#### Scenario: Merged release PR
- **WHEN** a release PR for 0.2.0 is merged
- **THEN** tag `v0.2.0` exists, its GitHub release lists the 0.2.0 changes, and it has `arc-0.2.0.tar.gz`, `arc-0.2.0-py3-none-any.whl` and `SHA256SUMS` attached

#### Scenario: Tests fail at release time
- **WHEN** the test suite fails in the release workflow
- **THEN** no build artifacts are uploaded to the release, and the workflow run fails

### Requirement: First release
The first release SHALL be version 0.1.0.

#### Scenario: Bootstrap
- **WHEN** release-please runs for the first time with the manifest at `0.0.0` and `feat:` commits in history
- **THEN** the release PR proposes 0.1.0
