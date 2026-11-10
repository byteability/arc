"""Create, verify and atomically store a tar.zst archive of a folder."""

import getpass
import hashlib
import os
import shutil
import socket
import stat
import tarfile
from collections.abc import Callable
from compression import zstd
from datetime import UTC, datetime
from pathlib import Path

from arc import history
from arc.config import Config
from arc.progress import CountingReader, Progress

EXCLUDED_NAMES = {".DS_Store"}


class ArchiveError(Exception):
    pass


def sha256_file(path: Path, progress: Progress | None = None) -> str:
    progress = progress or Progress(enabled=False)
    progress.phase("checksum", path.stat().st_size)
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
            progress.advance(len(chunk))
    progress.end()
    return h.hexdigest()


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_source(folder: str | Path, archive_dir: Path) -> Path:
    src = Path(os.path.abspath(Path(folder).expanduser()))
    if src.is_symlink():
        raise ArchiveError(f"source is a symlink, pass the real path: {src}")
    if not src.exists():
        raise ArchiveError(f"source does not exist: {src}")
    if not src.is_dir():
        raise ArchiveError(f"source is not a directory: {src}")
    if not src.name:
        raise ArchiveError(f"refusing to archive filesystem root: {src}")
    real_src, real_dir = src.resolve(), archive_dir.resolve()
    if real_src == real_dir or real_src.is_relative_to(real_dir) or real_dir.is_relative_to(real_src):
        raise ArchiveError(f"source overlaps ARCHIVE_DIR ({archive_dir}): {src}")
    return src


def _verify(path: Path, progress: Progress) -> int:
    """Decompress the whole archive and return its member count."""
    progress.phase("verifying", path.stat().st_size)
    with path.open("rb") as raw, zstd.ZstdFile(CountingReader(raw, progress)) as z:
        with tarfile.open(fileobj=z, mode="r|") as tar:
            count = sum(1 for _ in tar)
        while z.read(1 << 20):  # drain to end so the zstd frame checksum is checked
            pass
    progress.end()
    return count


def _scan_size(src: Path, progress: Progress) -> int:
    """Total bytes of regular files that will be archived (symlinks not followed)."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_NAMES]
        for name in filenames:
            if name in EXCLUDED_NAMES:
                continue
            st = os.lstat(os.path.join(dirpath, name))
            if stat.S_ISREG(st.st_mode):
                total += st.st_size
                progress.advance(st.st_size)
    return total


def _add_tree(tar: tarfile.TarFile, path: str, arcname: str,
              tar_filter: Callable[[tarfile.TarInfo], tarfile.TarInfo | None], progress: Progress) -> None:
    """Same entries and order as TarFile.add, but file reads are reported to progress."""
    info = tar.gettarinfo(path, arcname)
    if info is None:  # unsupported type (socket etc.), skipped like TarFile.add does
        return
    info = tar_filter(info)
    if info is None:
        return
    if info.isreg():
        with open(path, "rb") as f:
            tar.addfile(info, CountingReader(f, progress))
    else:
        tar.addfile(info)
    if info.isdir():
        for name in sorted(os.listdir(path)):
            _add_tree(tar, os.path.join(path, name), f"{arcname}/{name}", tar_filter, progress)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create(folder: str | Path, config: Config, delete: bool = False, now: datetime | None = None,
           progress: Progress | None = None) -> dict:
    progress = progress or Progress(enabled=False)
    archive_dir = config.archive_dir
    src = validate_source(folder, archive_dir)
    now = (now or datetime.now(UTC)).replace(microsecond=0)
    archive_id = f"{src.name}-{now:%Y%m%dT%H%M%SZ}"
    final = archive_dir / f"{archive_id}.tar.zst"
    if final.exists():
        raise ArchiveError(f"archive already exists: {final}")

    tmp_dir = archive_dir / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    part = tmp_dir / f"{archive_id}.part"
    stats = {"entries": 0, "files": 0, "bytes": 0}

    def tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        if Path(info.name).name in EXCLUDED_NAMES:
            return None
        stats["entries"] += 1
        if info.isfile():
            stats["files"] += 1
            stats["bytes"] += info.size
        return info

    total = None
    if progress.enabled:
        progress.phase("scanning")
        total = _scan_size(src, progress)

    try:
        progress.phase("compressing", total)
        with part.open("wb") as f:
            with tarfile.open(fileobj=f, mode="w:zst", level=config.zstd_level) as tar:
                _add_tree(tar, str(src), src.name, tar_filter, progress)
            f.flush()
            os.fsync(f.fileno())
        progress.end()
        digest = sha256_file(part, progress)
        count = _verify(part, progress)
        if count != stats["entries"]:
            raise ArchiveError(f"verification failed: wrote {stats['entries']} entries, read back {count}")
        if final.exists():
            raise ArchiveError(f"archive already exists: {final}")
        os.replace(part, final)
        _fsync_dir(archive_dir)
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    record = {
        "event": "add",
        "id": archive_id,
        "timestamp": iso(now),
        "host": socket.gethostname(),
        "user": getpass.getuser(),
        "source_path": str(src),
        "archive_path": final.name,
        "format": "tar.zst",
        "size_before": stats["bytes"],
        "size_after": final.stat().st_size,
        "file_count": stats["files"],
        "sha256": digest,
        "source_deleted": delete,
    }
    try:
        history.append(archive_dir, record)
    except OSError as e:
        raise ArchiveError(f"archive written to {final} but history append failed ({e}); source not deleted") from e

    if delete:
        try:
            shutil.rmtree(src)
        except OSError as e:
            history.append(archive_dir, {
                "event": "delete_failed",
                "id": archive_id,
                "timestamp": iso(datetime.now(UTC)),
                "error": str(e),
            })
            raise ArchiveError(f"archived to {final} but deleting source failed: {e}") from e
    return record
