import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arc.config import Config


class TempEnvCase(unittest.TestCase):
    """Provides an isolated HOME, ARCHIVE_DIR and workspace per test."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.home = self.root / "home"
        self.archive_dir = self.root / "archive"
        self.work = self.root / "work"
        for d in (self.home, self.archive_dir, self.work):
            d.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ("ARCHIVE_DIR", "ZSTD_LEVEL")}
        env["HOME"] = str(self.home)
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.config = Config(archive_dir=self.archive_dir, zstd_level=3)

    def make_source(self, name="proj") -> Path:
        src = self.work / name
        (src / "sub").mkdir(parents=True)
        (src / "a.txt").write_text("hello")
        (src / "sub" / "b.txt").write_text("world" * 100)
        return src
