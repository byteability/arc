import io
import shutil
import tarfile
from datetime import UTC, datetime

from arc import archiver, history, restore
from arc.archiver import ArchiveError
from helpers import TempEnvCase

NOW = datetime(2026, 11, 10, 10, 15, 30, tzinfo=UTC)
AID = "proj-20261110T101530Z"


class RestoreTests(TempEnvCase):
    def archive(self, delete=True):
        src = self.make_source()
        (src / "link").symlink_to("/etc/hosts")
        archiver.create(src, self.config, delete=delete, now=NOW)
        return src

    def test_restore_to_original(self):
        src = self.archive()
        dest = restore.restore(self.config, AID)
        self.assertEqual(dest, src)
        self.assertEqual((src / "sub" / "b.txt").read_text(), "world" * 100)
        self.assertEqual((src / "link").readlink().as_posix(), "/etc/hosts")
        events = list(history.read(self.archive_dir))
        self.assertEqual(events[-1]["event"], "restore")
        self.assertEqual(events[-1]["id"], AID)
        self.assertEqual(events[-1]["target_path"], str(src))

    def test_restore_to_other_dir(self):
        src = self.archive()
        dest = restore.restore(self.config, AID, to=self.root / "r" / "deep")
        self.assertEqual(dest, self.root / "r" / "deep" / "proj")
        self.assertEqual((dest / "a.txt").read_text(), "hello")
        self.assertFalse(src.exists())

    def test_unknown_id(self):
        with self.assertRaisesRegex(ArchiveError, "no archive"):
            restore.restore(self.config, "nope")

    def test_missing_archive_file(self):
        self.archive()
        (self.archive_dir / f"{AID}.tar.zst").unlink()
        with self.assertRaisesRegex(ArchiveError, f"{AID}.tar.zst"):
            restore.restore(self.config, AID)

    def test_refuses_existing_target(self):
        src = self.archive(delete=False)
        (src / "a.txt").write_text("changed")
        with self.assertRaisesRegex(ArchiveError, "--force"):
            restore.restore(self.config, AID)
        self.assertEqual((src / "a.txt").read_text(), "changed")

    def test_force_overwrites_and_keeps_extras(self):
        src = self.archive(delete=False)
        (src / "a.txt").write_text("changed")
        (src / "extra.txt").write_text("keep")
        restore.restore(self.config, AID, force=True)
        self.assertEqual((src / "a.txt").read_text(), "hello")
        self.assertEqual((src / "extra.txt").read_text(), "keep")

    def test_force_does_not_write_through_outside_symlink(self):
        src = self.archive(delete=False)
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "b.txt").write_text("precious")
        shutil.rmtree(src / "sub")
        (src / "sub").symlink_to(outside)
        with self.assertRaises(tarfile.FilterError):
            restore.restore(self.config, AID, force=True)
        self.assertEqual((outside / "b.txt").read_text(), "precious")

    def test_checksum_mismatch_writes_nothing(self):
        src = self.archive()
        archive = self.archive_dir / f"{AID}.tar.zst"
        data = bytearray(archive.read_bytes())
        data[-1] ^= 0xFF
        archive.write_bytes(bytes(data))
        with self.assertRaisesRegex(ArchiveError, "checksum"):
            restore.restore(self.config, AID)
        self.assertFalse(src.exists())

    def test_traversal_member_rejected(self):
        archive = self.archive_dir / "evil.tar.zst"
        with tarfile.open(archive, "w:zst") as tar:
            info = tarfile.TarInfo("../../evil")
            info.size = 3
            tar.addfile(info, io.BytesIO(b"bad"))
        history.append(self.archive_dir, {
            "event": "add", "id": "evil", "archive_path": archive.name,
            "source_path": str(self.work / "evil"), "sha256": archiver.sha256_file(archive),
        })
        with self.assertRaises(tarfile.FilterError):
            restore.restore(self.config, "evil", to=self.root / "x" / "y")
        self.assertFalse((self.root / "evil").exists())
