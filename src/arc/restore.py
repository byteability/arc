"""Restore an archive by id."""

import getpass
import os
import socket
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from arc import history
from arc.archiver import ArchiveError, iso, sha256_file
from arc.config import Config


def find(archive_dir: Path, archive_id: str) -> dict:
    for record in history.archives(archive_dir):
        if record["id"] == archive_id:
            return record
    raise ArchiveError(f"no archive with id {archive_id!r} in history")


def restore(config: Config, archive_id: str, to: str | Path | None = None, force: bool = False) -> Path:
    record = find(config.archive_dir, archive_id)
    archive = config.archive_dir / record["archive_path"]
    if not archive.is_file():
        raise ArchiveError(f"archive file missing: {archive}")
    if sha256_file(archive) != record["sha256"]:
        raise ArchiveError(f"checksum mismatch, archive may be corrupted: {archive}")

    source = Path(record["source_path"])
    target_dir = Path(os.path.abspath(Path(to).expanduser())) if to else source.parent
    dest = target_dir / source.name
    if (dest.exists() or dest.is_symlink()) and not force:
        raise ArchiveError(f"target exists, use --force to overwrite: {dest}")

    target_dir.mkdir(parents=True, exist_ok=True)
    root = target_dir.resolve()

    def extract_filter(member: tarfile.TarInfo, dest_path: str) -> tarfile.TarInfo | None:
        # With --force, an existing symlink at a symlink member's path would make the
        # tar filter resolve through it and reject the member; replace it instead.
        if force and member.issym():
            existing = Path(dest_path, member.name)
            if existing.is_symlink() and existing.parent.resolve().is_relative_to(root):
                existing.unlink()
        return tarfile.tar_filter(member, dest_path)

    with tarfile.open(archive, "r:zst") as tar:
        tar.extractall(target_dir, filter=extract_filter)

    history.append(config.archive_dir, {
        "event": "restore",
        "id": archive_id,
        "timestamp": iso(datetime.now(UTC)),
        "host": socket.gethostname(),
        "user": getpass.getuser(),
        "target_path": str(dest),
    })
    return dest
