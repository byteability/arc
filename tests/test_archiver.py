import os
import tarfile
from datetime import UTC, datetime
from unittest import mock

from arc import archiver, history
from arc.archiver import ArchiveError
from helpers import TempEnvCase

NOW = datetime(2026, 11, 10, 10, 15, 30, tzinfo=UTC)


class ArchiverTests(TempEnvCase):
    def members(self, path):
        with tarfile.open(path, "r:zst") as tar:
            return {m.name: m for m in tar}

    def assert_nothing_written(self):
        self.assertEqual([p for p in self.archive_dir.iterdir() if p.name != ".tmp"], [])
        tmp = self.archive_dir / ".tmp"
        self.assertEqual(list(tmp.iterdir()) if tmp.exists() else [], [])

    def test_round_trip_and_record(self):
        src = self.make_source()
        rec = archiver.create(src, self.config, now=NOW)
        final = self.archive_dir / "proj-20261110T101530Z.tar.zst"
        self.assertTrue(final.is_file())
        self.assertEqual(set(self.members(final)), {"proj", "proj/a.txt", "proj/sub", "proj/sub/b.txt"})
        out = self.root / "out"
        with tarfile.open(final, "r:zst") as tar:
            tar.extractall(out, filter="tar")
        self.assertEqual((out / "proj" / "sub" / "b.txt").read_text(), "world" * 100)

        self.assertEqual(rec["id"], "proj-20261110T101530Z")
        self.assertEqual(rec["timestamp"], "2026-11-10T10:15:30Z")
        self.assertEqual(rec["source_path"], str(src))
        self.assertEqual(rec["archive_path"], final.name)
        self.assertEqual(rec["file_count"], 2)
        self.assertEqual(rec["size_before"], 5 + 500)
        self.assertEqual(rec["size_after"], final.stat().st_size)
        self.assertEqual(rec["sha256"], archiver.sha256_file(final))
        self.assertFalse(rec["source_deleted"])
        for key in ("host", "user", "format"):
            self.assertIn(key, rec)
        self.assertEqual(history.list_archives(self.archive_dir), [rec])
        self.assertTrue(src.exists())
        self.assertEqual(list((self.archive_dir / ".tmp").iterdir()), [])

    def test_name_collision(self):
        src = self.make_source()
        final = self.archive_dir / "proj-20261110T101530Z.tar.zst"
        final.write_bytes(b"existing")
        with self.assertRaisesRegex(ArchiveError, "already exists"):
            archiver.create(src, self.config, now=NOW)
        self.assertEqual(final.read_bytes(), b"existing")
        self.assertFalse(history.history_path(self.archive_dir).exists())

    def test_invalid_sources(self):
        f = self.work / "notes.txt"
        f.write_text("x")
        real = self.make_source()
        link = self.work / "link"
        link.symlink_to(real)
        inner = self.archive_dir / "inner"
        inner.mkdir()
        cases = [self.work / "missing", f, link, self.archive_dir, inner, self.root]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ArchiveError):
                archiver.create(case, self.config, now=NOW)
        inner.rmdir()
        self.assert_nothing_written()

    def test_ds_store_excluded_and_symlink_kept(self):
        src = self.make_source()
        (src / ".DS_Store").write_text("x")
        (src / "sub" / ".DS_Store").write_text("x")
        (src / "link").symlink_to("/etc/hosts")
        rec = archiver.create(src, self.config, now=NOW)
        members = self.members(self.archive_dir / rec["archive_path"])
        self.assertFalse(any(n.endswith(".DS_Store") for n in members))
        self.assertTrue(members["proj/link"].issym())
        self.assertEqual(members["proj/link"].linkname, "/etc/hosts")

    def test_compression_failure_leaves_nothing(self):
        src = self.make_source()
        with mock.patch.object(tarfile.TarFile, "addfile", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                archiver.create(src, self.config, delete=True, now=NOW)
        self.assert_nothing_written()
        self.assertTrue(src.exists())

    def test_verification_failure_leaves_nothing(self):
        src = self.make_source()
        with mock.patch.object(archiver, "_verify", return_value=1):
            with self.assertRaisesRegex(ArchiveError, "verification failed"):
                archiver.create(src, self.config, delete=True, now=NOW)
        self.assert_nothing_written()
        self.assertTrue(src.exists())

    def test_delete_success(self):
        src = self.make_source()
        rec = archiver.create(src, self.config, delete=True, now=NOW)
        self.assertFalse(src.exists())
        self.assertTrue(rec["source_deleted"])
        self.assertTrue(history.list_archives(self.archive_dir)[0]["source_deleted"])

    def test_history_failure_keeps_source(self):
        src = self.make_source()
        with mock.patch.object(history, "append", side_effect=OSError("ro fs")):
            with self.assertRaisesRegex(ArchiveError, "proj-20261110T101530Z.tar.zst"):
                archiver.create(src, self.config, delete=True, now=NOW)
        self.assertTrue(src.exists())
        self.assertTrue((self.archive_dir / "proj-20261110T101530Z.tar.zst").exists())

    def test_rmtree_failure_logs_delete_failed(self):
        src = self.make_source()
        with mock.patch.object(archiver.shutil, "rmtree", side_effect=PermissionError("denied")):
            with self.assertRaisesRegex(ArchiveError, "deleting source failed"):
                archiver.create(src, self.config, delete=True, now=NOW)
        events = [r["event"] for r in history.read(self.archive_dir)]
        self.assertEqual(events, ["add", "delete_failed"])
        self.assertFalse(history.list_archives(self.archive_dir)[0]["source_deleted"])
        self.assertTrue(src.exists())
        self.assertTrue((self.archive_dir / "proj-20261110T101530Z.tar.zst").exists())

    def test_relative_path_resolved(self):
        self.make_source()
        cwd = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, cwd)
        rec = archiver.create("proj/", self.config, now=NOW)
        self.assertEqual(rec["source_path"], str(self.work / "proj"))
