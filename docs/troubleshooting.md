# Troubleshooting

Errors are printed as `arc: error: <message>`. Find the message below.

## Configuration (exit code 2)

**`ARCHIVE_DIR is not set (use --archive-dir, the environment, or ~/.config/arc/.env)`**
No source sets `ARCHIVE_DIR`. Add it to `~/.config/arc/.env` (see [Getting started](getting-started.md#configure)). A `.env` in the current directory is ignored on purpose, and an empty value counts as not set.

**`ARCHIVE_DIR does not exist: /Volumes/Data/archive`**
Usually the disk holding the archives isn't mounted. arc never creates `ARCHIVE_DIR` ([why](safety.md#archive_dir-is-never-created)): mount the disk, or fix the path. For a brand-new setup, create the directory once with `mkdir -p`.

**`ARCHIVE_DIR is not a directory: …`**
The path points to a file. Fix the path.

**`ZSTD_LEVEL must be an integer, got 'max'`**
Set `ZSTD_LEVEL` to a number such as `10`, or remove it to use the default.

**`argument command: invalid choice: …`** or **`unrecognized arguments: …`**
A typo in the command or a flag. See `arc --help` or the [command reference](commands.md).

## `arc add`

**`source does not exist: …`** / **`source is not a directory: …`**
Check the path. arc archives directories only; to archive a single file, put it in a folder.

**`source is a symlink, pass the real path: …`**
Pass the folder the link points to, so the history records the real location.

**`refusing to archive filesystem root: /`**
Archive a specific folder instead.

**`source overlaps ARCHIVE_DIR (…): …`**
The folder is inside `ARCHIVE_DIR`, or contains it. arc would end up archiving its own archives. Choose another folder or another `ARCHIVE_DIR`.

**`archive already exists: …`**
Archive ids have one-second precision, so the same folder was archived twice within one second. Wait a second and run it again. Existing archives are never overwritten.

**`verification failed: wrote N entries, read back M`**
The archive didn't read back correctly, often because the disk is failing or full. The temporary file is removed and the source is untouched. Check the disk (free space, `diskutil verifyVolume` on macOS) and try again.

**`archive written to … but history append failed (…); source not deleted`**
The archive file is complete, but it couldn't be recorded, for example because `history.jsonl` isn't writable or the disk is full. The source was kept even with `--delete`. Fix the cause and run `arc add` again. The unrecorded archive file can then be deleted, because `list` and `restore` don't know about it.

**`archived to … but deleting source failed: …`**
The archive is complete and recorded, and a `delete_failed` event was added to the history. Some files in the source couldn't be removed (permissions, files in use). Remove what's left by hand once you've checked it.

**Leftover files in `ARCHIVE_DIR/.tmp/`**
If arc was killed while archiving, a `.part` file may remain. It isn't referenced by the history and can be deleted when no `arc add` is running.

## `arc restore`

**`no archive with id 'proj-2026…' in history`**
Copy the id exactly from `arc list` or `arc search`. If you use several archive directories, pass the right one with `--archive-dir`.

**`archive file missing: …`**
The history knows the archive, but the file isn't in `ARCHIVE_DIR`. It was moved or deleted, or `ARCHIVE_DIR` points to another disk. Put the file back, or point `ARCHIVE_DIR` at the directory that holds it.

**`checksum mismatch, archive may be corrupted: …`**
The file's sha256 differs from the one recorded when it was made. Nothing was extracted. Restore the file from your backup of `ARCHIVE_DIR`. See [Safety](safety.md#integrity-over-time) for checking archives yourself.

**`target exists, use --force to overwrite: …`**
The folder is already there. Restore elsewhere with `--to DIR`, or pass `--force` to extract over it (existing files with the same path are replaced, others are kept).

## `arc update` (exit code 1)

**``arc is not installed with `uv tool` (environment: …); update it the way you installed it``**
arc was installed with pip, pipx or another tool. Update it with that tool, or switch to uv (see [Getting started](getting-started.md#install)).

**``arc X was installed from a local folder, so its version can't be compared with releases; run `arc update --force` to install vX.Y.Z``**
This happens with development installs from a checkout or from git. Run `arc update --force` to replace it with the latest release.

**`arc is not installed (running from source); nothing to update`**
You're running arc from a source checkout (e.g. `python -m arc.cli`). Use `git pull` instead.

**`uv is not installed or not on PATH`**
Install [uv](https://docs.astral.sh/uv/getting-started/installation/), or make sure it's on `PATH`.

**`https://api.github.com/…: HTTP 403 …`** (or `HTTP 429`), or **`…: <network error>`**
GitHub couldn't be reached, or the unauthenticated API rate limit (60 requests per hour per IP address) was hit. Try again later.

**`checksum mismatch for arc-…whl; not installing`** / **`… is not listed in SHA256SUMS; not installing`** / **`release has no SHA256SUMS file; not installing`** / **`expected one wheel in release …`**
The download didn't match the release's checksums, or the release is incomplete. Nothing was installed. Try again later; if it persists, [open an issue](https://github.com/byteability/arc/issues).

### Updating from 0.3.1 or older

`arc update` in versions up to 0.3.1 used the GitHub CLI (`gh`). Either update once with `gh` installed and logged in, or reinstall directly; both keep your configuration and archives:

```sh
uv tool install --force --python ">=3.14" https://github.com/byteability/arc/releases/download/vX.Y.Z/arc-X.Y.Z-py3-none-any.whl
```

From then on, `arc update` needs neither `gh` nor a GitHub account.
