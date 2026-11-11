# Command reference

```
arc [--version] <command> [options]
```

Every command except `arc update` reads its configuration (see [Getting started](getting-started.md#configure)).
Errors go to stderr as `arc: error: <message>`. See [Troubleshooting](troubleshooting.md) for each message.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | the operation failed (archive, restore, update or file system error) |
| `2` | usage or configuration error (unknown command or flag, `ARCHIVE_DIR` not set or missing, invalid `ZSTD_LEVEL`) |

## Global options

| Option | Effect |
|---|---|
| `--version` | print the version and where it was installed from, then exit |
| `--help`, `-h` | print help; also works after a command, e.g. `arc restore --help` |

`arc --version` shows the install source in parentheses:

```
arc 0.4.1 (arc-0.4.1-py3-none-any.whl)     # installed from a release wheel
arc 0.4.1 (local: /Users/me/src/arc)        # installed from a local folder
arc 0.4.1 (local, editable: /Users/me/src/arc)
arc 0.4.1 (git: 3f11b38)
```

The `add`, `list`, `search` and `restore` commands also accept `--archive-dir DIR`. It overrides `ARCHIVE_DIR` from the environment and the config file for that one run.

## arc add

```
arc add FOLDER [--delete] [--archive-dir DIR]
```

Archives `FOLDER` into `ARCHIVE_DIR` as `<folder name>-<UTC timestamp>.tar.zst`, verifies it, and records it in the history.

| Option | Effect |
|---|---|
| `--delete` | delete `FOLDER` after the archive is verified and recorded (see [Safety](safety.md)) |
| `--archive-dir DIR` | use `DIR` as the archive directory |

Output: the archive id and the archive path, plus `deleted <path>` when `--delete` removed the source.

```
$ arc add ~/work/proj --delete
proj-20261111T101530Z  /Volumes/Data/archive/proj-20261111T101530Z.tar.zst
deleted /Users/me/work/proj
```

The archive id is the folder name plus the UTC time in seconds, so archiving the same folder twice within one second fails with `archive already exists`.
`FOLDER` must be a real directory: not a symlink, not `/`, and not inside or containing `ARCHIVE_DIR`.

## arc list

```
arc list [--limit N] [--archive-dir DIR]
```

Lists archives, newest first. Each line shows the id, the archive time (UTC), the archive size, `[deleted]` if the source was deleted, and the source path.

| Option | Effect |
|---|---|
| `--limit N` | show only the `N` newest archives |
| `--archive-dir DIR` | read the history in `DIR` |

```
$ arc list --limit 2
proj-20261111T101530Z  2026-11-11T10:15:30Z     1.2 GB  [deleted]  /Users/me/work/proj
notes-20261110T090000Z  2026-11-10T09:00:00Z   48.0 KB             /Users/me/notes
```

Prints nothing if there are no archives yet.

## arc search

```
arc search TERM [--archive-dir DIR]
```

Lists the archives whose source path or id contains `TERM`. Case is ignored. The output format is the same as `arc list`.

| Option | Effect |
|---|---|
| `--archive-dir DIR` | search the history in `DIR` |

```
$ arc search clientx
clientx-site-20261001T120000Z  2026-10-01T12:00:00Z   310.4 MB             /Users/me/work/clientx-site
```

## arc restore

```
arc restore ID [--to DIR] [--force] [--archive-dir DIR]
```

Restores the archive `ID` (as shown by `list`/`search`). By default it goes back to its original location: the folder's original parent directory, under its original name. arc checks the archive's sha256 against the history before extracting anything.

| Option | Effect |
|---|---|
| `--to DIR` | restore into `DIR` instead; the folder is created as `DIR/<original folder name>`, and `DIR` is created if needed |
| `--force` | restore even if the target folder already exists; files from the archive overwrite existing files with the same path, other existing files are kept |
| `--archive-dir DIR` | read archives and history from `DIR` |

Output: the restored path.

```
$ arc restore proj-20261111T101530Z --to /tmp/check
restored to /tmp/check/proj
```

Every restore is recorded in the history as a `restore` event.

## arc update

```
arc update [--force]
```

Installs the latest GitHub release if it's newer than the installed version. It needs [uv](https://docs.astral.sh/uv/), but no GitHub account, `gh`, or `ARCHIVE_DIR`.
The wheel is checked against the release's `SHA256SUMS` before installing.

| Option | Effect |
|---|---|
| `--force` | install the latest release even if it isn't newer, or if arc was installed from a local folder or git, whose version can't be compared with releases |

```
$ arc update
updated arc 0.4.0 → 0.4.1
$ arc update
arc 0.4.1 is already up to date
```

`arc update` only works when arc was installed with `uv tool install`. Otherwise, update it the way you installed it.
