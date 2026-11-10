## Context

Single Python package at the repo root, private repo on a free plan (no branch protection), commits already follow Conventional Commits. The existing release workflow runs on `v*` tags and expects `pyproject.toml` to already match the tag.

## Goals / Non-Goals

**Goals:** automatic version and changelog from commits; a human approval step (merging the release PR); release artifacts unchanged (sdist, wheel, `SHA256SUMS`).

**Non-Goals:** publishing to PyPI, `arc --version`, signed artifacts, CI on the release PR.

## Decisions

**release-please over python-semantic-release.** release-please waits for a merged PR before releasing, so nothing ships automatically, and it has a maintained GitHub Action. python-semantic-release releases on every merge unless you configure otherwise, and needs push access to `main`.

**Manifest config, `release-type: python`.** The python strategy updates `project.version` in `pyproject.toml` (and `__version__` files, which `arc` doesn't have) and writes `CHANGELOG.md`. `include-component-in-tag: false` keeps tags as `vX.Y.Z` instead of `arc-vX.Y.Z`. `bump-minor-pre-major: true` makes breaking changes bump minor before 1.0; `feat:` → minor is release-please's default.

**Manifest starts at `0.0.0`.** release-please treats the manifest as the last released version, so the first `feat:` gives 0.1.0, which matches `pyproject.toml` and the fact that nothing was released yet. *Alternative:* `release-as: 0.1.0` would need removing again after the first release.

**Build in the same workflow, gated on `release_created`.** Tags and releases created with the built-in `GITHUB_TOKEN` don't trigger other workflows, so a separate tag-triggered build would never run. The build job runs only when the release-please step reports `release_created == 'true'`, and uploads with `gh release upload`. The old tag/version consistency check is dropped because release-please writes both.

**Built-in token, not a PAT.** The setting "Allow GitHub Actions to create and approve pull requests" was enabled for the org and repo instead. Trade-off: PRs opened by `GITHUB_TOKEN` don't trigger the CI workflow, so the release PR has no test run. Acceptable because it only changes the version and changelog, and the release job runs the tests before uploading.

**Pinning.** `googleapis/release-please-action` is pinned by SHA to v5.0.0 (node24); the other actions keep the versions from the CI workflow.

## Risks / Trade-offs

- [The GitHub release exists before artifacts are uploaded; if tests or the build fail, it has no files] → The run fails visibly; fix and re-run the build job, or delete the release and tag. Draft releases would avoid this but add a publish step.
- [Commits that don't follow Conventional Commits are left out of the changelog] → Your global git rules already require them; squash-merge titles must follow them too.
- [Release PR has no CI run] → See the token decision above.
- [Someone pushes a `v*` tag by hand] → It no longer triggers anything; harmless.

## Migration Plan

Merge this PR. release-please then opens a release PR for 0.1.0 on the next push to `main` (the merge itself). Merging that PR produces the first release. Rollback: revert this PR; the old tag-based workflow returns.
