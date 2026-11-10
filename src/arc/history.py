"""Append-only JSONL history stored in ARCHIVE_DIR."""

import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path

HISTORY_NAME = "history.jsonl"


def history_path(archive_dir: Path) -> Path:
    return archive_dir / HISTORY_NAME


def append(archive_dir: Path, record: dict) -> None:
    line = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(history_path(archive_dir), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        if os.write(fd, line) != len(line):
            raise OSError("short write to history file")
        os.fsync(fd)
    finally:
        os.close(fd)


def read(archive_dir: Path) -> Iterator[dict]:
    path = history_path(archive_dir)
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                record = None
            if not isinstance(record, dict):
                print(f"arc: warning: skipping malformed history line {lineno}", file=sys.stderr)
                continue
            yield record


def archives(archive_dir: Path) -> list[dict]:
    """Add records, newest first, with source_deleted corrected by delete_failed events."""
    adds: dict[str, dict] = {}
    for record in read(archive_dir):
        event, rid = record.get("event"), record.get("id")
        if event == "add" and rid:
            adds[rid] = dict(record)
        elif event == "delete_failed" and rid in adds:
            adds[rid]["source_deleted"] = False
    return list(reversed(adds.values()))


def list_archives(archive_dir: Path, limit: int | None = None) -> list[dict]:
    records = archives(archive_dir)
    return records[:limit] if limit is not None else records


def search(archive_dir: Path, term: str) -> list[dict]:
    term = term.casefold()
    return [
        r for r in archives(archive_dir)
        if term in str(r.get("source_path", "")).casefold() or term in str(r.get("id", "")).casefold()
    ]
