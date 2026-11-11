# arc

Archive folders to `tar.zst` in a local directory, with an append-only history and restore.
Python ≥ 3.14, no third-party dependencies.

## Install

```sh
uv tool install --reinstall --python ">=3.14" .   # --reinstall: otherwise uv may reuse a stale cached build of this folder
```

## Configure

```sh
mkdir -p /Volumes/Data/archive          # arc never creates ARCHIVE_DIR
mkdir -p ~/.config/arc
cat > ~/.config/arc/.env <<'EOF'
ARCHIVE_DIR=/Volumes/Data/archive
ZSTD_LEVEL=10
EOF
```

Precedence: `--archive-dir` flag > environment variables > `~/.config/arc/.env` > defaults.
A `.env` in the current directory is ignored.

## Usage

```sh
arc add ~/work/proj            # -> $ARCHIVE_DIR/proj-20261110T101530Z.tar.zst
arc add ~/work/proj --delete   # delete source only after the archive is verified and recorded
arc list [--limit N]
arc search clientx             # case-insensitive match on source path or id
arc restore proj-20261110T101530Z [--to DIR] [--force]
arc --version                  # version and install source, e.g. "arc 0.1.0 (arc-0.1.0-py3-none-any.whl)"
arc update [--force]           # install the latest release (needs gh and uv; --force for non-release installs)
```

History is stored in `$ARCHIVE_DIR/history.jsonl`, one JSON object per line.

Progress bars for `add` and `restore` are shown on stderr when it is a terminal (never in pipes or scripts).
Notes: symlinks are archived as links; `.DS_Store` files are skipped; extended attributes are not preserved.
Exit codes: `0` ok, `1` error, `2` usage/config error.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Releases

Releases are automated with [release-please](https://github.com/googleapis/release-please) from Conventional Commit messages.
It keeps a release PR open that bumps `version` in `pyproject.toml` and updates `CHANGELOG.md`;
merging that PR tags `vX.Y.Z`, creates the GitHub release, and attaches the sdist, wheel and `SHA256SUMS`.
Before 1.0: `fix:` → patch, `feat:` and breaking changes → minor. Don't edit the version or push tags by hand.
