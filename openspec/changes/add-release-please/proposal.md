## Why

Releasing currently means editing `version` in `pyproject.toml` by hand, picking the next number, tagging, and pushing the tag. Every commit already follows Conventional Commits, so the next version and the changelog can be worked out automatically.

## What Changes

- Add release-please, configured with `release-please-config.json` and `.release-please-manifest.json`.
- On every push to `main`, release-please keeps a single "release PR" open. It bumps `version` in `pyproject.toml` and updates `CHANGELOG.md` from commit messages.
- Merging the release PR creates the `vX.Y.Z` tag and GitHub release. The same workflow then runs the tests, builds the sdist and wheel, and uploads them with `SHA256SUMS`.
- Before 1.0: `fix:` → patch, `feat:` → minor, breaking changes → minor. Reaching 1.0.0 is a deliberate one-off decision.
- The first release will be `0.1.0` (the manifest starts at `0.0.0`; nothing has been released before).
- **BREAKING (process):** pushing a `v*` tag no longer triggers a release. Tags are created only by merging the release PR.

## Capabilities

### New Capabilities
- `release-process`: How versions are chosen, what a release contains, and when it happens.

### Modified Capabilities
<!-- none -->

## Impact

- `.github/workflows/release.yml` rewritten; new files `release-please-config.json`, `.release-please-manifest.json`, and (after the first release) `CHANGELOG.md`.
- GitHub setting "Allow GitHub Actions to create and approve pull requests" enabled for the byteability org and the `arc` repo (already done).
- No application code changes.
