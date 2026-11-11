# Contributing

arc uses Python ≥ 3.14 and the standard library only (zstd via `compression.zstd` and `tarfile`). Please don't add runtime dependencies.

## Development install

```sh
uv tool install --reinstall --python ">=3.14" .   # --reinstall: otherwise uv may reuse a stale cached build of this folder
```

`arc --version` then shows `local: <path>`. To go back to a release, use `arc update --force`.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

CI runs the same command on every pull request. `tests/test_docs.py` fails if a CLI command or long option is missing from [`docs/commands.md`](docs/commands.md). When you change behavior, update the [user docs](docs/README.md) too.

## Commits and pull requests

Pull requests are squash-merged, so the PR title becomes the commit on `main`. Titles must follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:` …).

## Releases

Releases are automated with [release-please](https://github.com/googleapis/release-please) from the commit messages on `main`.
It keeps a release PR open that bumps `version` in `pyproject.toml` and updates `CHANGELOG.md`.
Merging that PR tags `vX.Y.Z`, creates the GitHub release, and attaches the sdist, wheel and `SHA256SUMS`.

- Before 1.0: `fix:` and `docs:` → patch, `feat:` and breaking changes → minor. `chore:`, `ci:`, `test:`, `refactor:` don't release.
- Don't edit the version or push tags by hand.

## Repository rules

`main` is protected by rulesets: changes land only through squash-merged PRs that pass the `test` check, and `v*` tags are immutable.
CI on release PRs opened by release-please waits for approval ("Approve and run" on the PR) because a bot opened them.
Approve it and merge once `test` passes. Repository admins can also merge them through the check bypass.
