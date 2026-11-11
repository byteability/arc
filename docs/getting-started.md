# Getting started

## Install

arc is installed with [uv](https://docs.astral.sh/uv/getting-started/installation/), which also downloads Python 3.14 or newer if your system doesn't have it. No GitHub account or `gh` is needed.

Copy the wheel URL from the [latest release](https://github.com/byteability/arc/releases/latest) (the `arc-X.Y.Z-py3-none-any.whl` asset) and run:

```sh
uv tool install --python ">=3.14" https://github.com/byteability/arc/releases/download/vX.Y.Z/arc-X.Y.Z-py3-none-any.whl
arc --version        # arc X.Y.Z (arc-X.Y.Z-py3-none-any.whl)
```

If `arc` isn't found afterwards, run `uv tool update-shell` and open a new terminal.

## Configure

arc needs one setting, `ARCHIVE_DIR`: the directory where archives and the history are stored. **arc never creates this directory.** If it's on an external disk that isn't mounted, arc stops instead of writing to your internal disk. Create it once:

```sh
mkdir -p /Volumes/Data/archive
```

Then put the settings in `~/.config/arc/.env`, which works from any directory:

```sh
mkdir -p ~/.config/arc
cat > ~/.config/arc/.env <<'EOF'
ARCHIVE_DIR=/Volumes/Data/archive
ZSTD_LEVEL=10
EOF
```

| Setting | Default | Meaning |
|---|---|---|
| `ARCHIVE_DIR` | none (required) | archive directory; `~` is expanded |
| `ZSTD_LEVEL` | `10` | zstd compression level; higher is smaller and slower |

Each setting is taken from the first of these sources that sets it:

1. the `--archive-dir` flag (for `ARCHIVE_DIR` only)
2. environment variables, e.g. `ARCHIVE_DIR=/mnt/other arc list`
3. `~/.config/arc/.env`
4. the default

The file format is `KEY=value`, one per line. Blank lines and lines starting with `#` are ignored, and values may be wrapped in single or double quotes. An empty value counts as not set. A `.env` file in the current directory is **not** read, so a project's `.env` can't redirect your archives.

## First archive

```sh
arc add ~/work/proj                    # archive, keep the source
arc list                               # newest first
arc restore proj-20261111T101530Z --to /tmp/check   # restore a copy elsewhere to check it
```

When you're confident, use `arc add ~/work/proj --delete` to remove the source after archiving. The source is removed only after the archive has been verified and recorded; see [Safety](safety.md).

While `add` and `restore` run in a terminal, they show a progress bar on stderr. It never appears when output is piped or run from a script.

## Update

```sh
arc update
```

This installs the latest release if it's newer than yours, and checks the download against the release's checksums first. Installs of version 0.3.1 or older need one extra step; see [Troubleshooting](troubleshooting.md#updating-from-031-or-older).

## Uninstall

```sh
uv tool uninstall arc
```

Your archives, `history.jsonl` and `~/.config/arc/.env` are left untouched.
