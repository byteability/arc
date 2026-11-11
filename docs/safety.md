# Safety guarantees

arc is built so that a failure at any point leaves your data in at least one complete, findable place.

## What `arc add` does, in order

1. **Checks the source.** It must be an existing directory: not a symlink, not `/`, and not inside or containing `ARCHIVE_DIR`. An archive with the same id must not already exist.
2. **Writes to a temporary file.** The archive is written to `ARCHIVE_DIR/.tmp/<id>.part` and flushed to disk. A crash at this point leaves only a `.part` file, which never appears in the history.
3. **Verifies it.** arc computes the archive's sha256, then decompresses and reads the whole archive back. It checks that the number of entries matches what was written. If verification fails, the `.part` file is removed and nothing else changes.
4. **Moves it into place.** The `.part` file is renamed to `ARCHIVE_DIR/<id>.tar.zst` in one atomic step. An existing archive is never overwritten.
5. **Records it.** The `add` line, including the sha256, is appended to `history.jsonl` and flushed. If this fails, arc reports it and does **not** delete the source.
6. **Deletes the source**, only with `--delete` and only after steps 1–5 succeeded.

Without `--delete`, the source is never touched.

If deleting the source fails partway (for example, a file you aren't allowed to remove), arc appends a `delete_failed` event and exits with status 1. The archive is complete and usable; check the source folder for what is left. `arc list` won't mark that archive as `[deleted]`.

## `ARCHIVE_DIR` is never created

If `ARCHIVE_DIR` doesn't exist, every command except `update` stops with exit code 2. This is deliberate. If your archive disk isn't mounted, its mount point usually doesn't exist (or is a plain folder on the internal disk), and creating it would silently fill your internal disk. arc only creates its own `.tmp` folder inside an existing `ARCHIVE_DIR`.

## What `arc restore` checks

- **Checksum first.** The archive's sha256 is compared with the value in the history before anything is extracted. On a mismatch, nothing is written.
- **No silent overwrite.** If the target folder already exists, restore stops unless you pass `--force`. With `--force`, files from the archive replace files at the same path; other existing files are left alone.
- **Paths stay inside the target.** Extraction uses Python's `tar` extraction filter. It rejects absolute member paths and members that would be written outside the target directory, and clears setuid, setgid, sticky and group/other write bits. Symlinks, including absolute ones, are restored as links and not followed.

## What is and isn't preserved

| Item | Behavior |
|---|---|
| file contents, directory structure, modification times | preserved |
| permissions | preserved, except setuid, setgid, sticky and group/other write bits, which restore clears |
| symlinks | archived as links, not followed; targets outside the folder aren't included |
| `.DS_Store` files | skipped |
| extended attributes, ACLs, macOS resource forks, Finder tags | **not** preserved |
| owner and group | recorded in the archive; restoring them requires running as root |

## Integrity over time

The sha256 in the history lets you check an archive at any time, without restoring it:

```sh
shasum -a 256 /Volumes/Data/archive/proj-20261111T101530Z.tar.zst
jq -r 'select(.id == "proj-20261111T101530Z" and .event == "add") | .sha256' /Volumes/Data/archive/history.jsonl
```

arc keeps one copy of each archive. Back up `ARCHIVE_DIR`, including `history.jsonl`, like any other important data.
