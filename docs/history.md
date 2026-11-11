# History file

Every archive and restore is recorded in `history.jsonl` in `ARCHIVE_DIR`, next to the archives. The format is [JSON Lines](https://jsonlines.org/): one JSON object per line, UTF-8.

The file is **append-only**: arc adds a line for each event and never rewrites or removes existing lines. Each line is written in a single write and flushed to disk. Back it up together with the archives; without it, `list`, `search` and `restore` can't find anything.

Timestamps are UTC, formatted as `2026-11-11T10:15:30Z`. Paths are absolute. `archive_path` is relative to `ARCHIVE_DIR`, so the whole directory can be moved to another disk.

## Events

### `add`: a folder was archived

```json
{"event": "add", "id": "proj-20261111T101530Z", "timestamp": "2026-11-11T10:15:30Z", "host": "mac.local", "user": "me", "source_path": "/Users/me/work/proj", "archive_path": "proj-20261111T101530Z.tar.zst", "format": "tar.zst", "size_before": 1288490188, "size_after": 402653184, "file_count": 5210, "sha256": "6f3b1fea…", "source_deleted": true}
```

| Field | Meaning |
|---|---|
| `id` | archive id: the folder name plus the UTC time of the archive |
| `timestamp` | when the archive was made |
| `host`, `user` | the machine and user that ran `arc add` |
| `source_path` | absolute path of the archived folder |
| `archive_path` | archive file name, relative to `ARCHIVE_DIR` |
| `format` | always `tar.zst` |
| `size_before` | total size of the regular files archived, in bytes |
| `size_after` | size of the archive file, in bytes |
| `file_count` | number of regular files archived |
| `sha256` | checksum of the archive file; checked before every restore |
| `source_deleted` | `true` if `--delete` was given; a later `delete_failed` event overrides it |

This line is written only after the archive has been verified and moved into place.

### `delete_failed`: `--delete` couldn't remove the source

```json
{"event": "delete_failed", "id": "proj-20261111T101530Z", "timestamp": "2026-11-11T10:15:42Z", "error": "[Errno 13] Permission denied: '/Users/me/work/proj/locked'"}
```

| Field | Meaning |
|---|---|
| `id` | the archive whose source deletion failed |
| `timestamp` | when the deletion failed |
| `error` | the error message |

The archive itself is complete and usable. The source may be partly deleted.

### `restore`: an archive was restored

```json
{"event": "restore", "id": "proj-20261111T101530Z", "timestamp": "2026-11-12T08:00:00Z", "host": "mac.local", "user": "me", "target_path": "/tmp/check/proj"}
```

| Field | Meaning |
|---|---|
| `id` | the restored archive |
| `timestamp` | when the restore finished |
| `host`, `user` | the machine and user that ran `arc restore` |
| `target_path` | absolute path of the restored folder |

## How `list` and `search` read it

- Each `add` event is one archive. `list` shows them newest first, and `search` filters them by id or source path, ignoring case.
- A `delete_failed` event for an archive sets its `source_deleted` to `false`, so `[deleted]` isn't shown for it.
- `restore` events are kept as a log and don't change the list.
- Lines that aren't valid JSON objects are skipped with `arc: warning: skipping malformed history line N` on stderr. The rest of the file is still used.

## Using it from other tools

Any JSON Lines reader works. For example, with [jq](https://jqlang.org/):

```sh
jq -r 'select(.event == "add") | [.id, .source_path] | @tsv' /Volumes/Data/archive/history.jsonl
```

Don't edit the file by hand while arc may be running. If you must fix it, append new lines rather than changing existing ones.
