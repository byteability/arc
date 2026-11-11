# arc

Archive folders to compressed `tar.zst` files in one directory, keep an append-only history of what was archived, and restore any archive by id.
The source folder is deleted only if you ask, and only after the archive is verified and recorded.
Python ≥ 3.14, no third-party dependencies.

## Install

Needs [uv](https://docs.astral.sh/uv/). No GitHub account or `gh` required.
Copy the wheel URL from the [latest release](https://github.com/byteability/arc/releases/latest):

```sh
uv tool install --python ">=3.14" https://github.com/byteability/arc/releases/download/vX.Y.Z/arc-X.Y.Z-py3-none-any.whl
```

Update later with `arc update`.

## Quick start

```sh
mkdir -p /Volumes/Data/archive && mkdir -p ~/.config/arc
echo 'ARCHIVE_DIR=/Volumes/Data/archive' > ~/.config/arc/.env

arc add ~/work/proj              # archive, keep the source
arc add ~/work/proj --delete     # archive, then delete the source
arc list                         # newest first
arc search proj
arc restore proj-20261111T101530Z [--to DIR]
```

## Documentation

- [Getting started](https://github.com/byteability/arc/blob/main/docs/getting-started.md): install, configure, update
- [Command reference](https://github.com/byteability/arc/blob/main/docs/commands.md)
- [Safety guarantees](https://github.com/byteability/arc/blob/main/docs/safety.md)
- [History file format](https://github.com/byteability/arc/blob/main/docs/history.md)
- [Troubleshooting](https://github.com/byteability/arc/blob/main/docs/troubleshooting.md)

Development, tests and releases: [CONTRIBUTING.md](https://github.com/byteability/arc/blob/main/CONTRIBUTING.md).

## License

[MIT](https://github.com/byteability/arc/blob/main/LICENSE) © Byteability
