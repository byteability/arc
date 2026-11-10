import os
from pathlib import Path

from arc import config
from arc.config import ConfigError, parse_env_file
from helpers import TempEnvCase


class ConfigTests(TempEnvCase):
    def write_global(self, text):
        p = self.home / ".config" / "arc" / ".env"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def dirs(self, *names):
        out = []
        for n in names:
            d = self.root / n
            d.mkdir()
            out.append(d)
        return out

    def test_flag_beats_env_beats_file(self):
        a, b, c = self.dirs("a", "b", "c")
        self.write_global(f"ARCHIVE_DIR={a}\n")
        os.environ["ARCHIVE_DIR"] = str(b)
        self.assertEqual(config.load({"ARCHIVE_DIR": str(c)}).archive_dir, c)
        self.assertEqual(config.load({}).archive_dir, b)
        del os.environ["ARCHIVE_DIR"]
        self.assertEqual(config.load({}).archive_dir, a)

    def test_cwd_env_ignored(self):
        (x,) = self.dirs("x")
        (self.work / ".env").write_text(f"ARCHIVE_DIR={x}\n")
        cwd = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, cwd)
        with self.assertRaisesRegex(ConfigError, "not set"):
            config.load({})

    def test_parser_comments_blank_quotes(self):
        p = self.root / "e.env"
        p.write_text('# comment\n\nARCHIVE_DIR="/Volumes/Data/archive"\nB=\'q\'\nC = plain \nnoequals\n')
        self.assertEqual(
            parse_env_file(p),
            {"ARCHIVE_DIR": "/Volumes/Data/archive", "B": "q", "C": "plain"},
        )

    def test_missing_file_ok(self):
        self.assertEqual(parse_env_file(self.root / "nope"), {})
        os.environ["ARCHIVE_DIR"] = str(self.archive_dir)
        self.assertEqual(config.load({}).archive_dir, self.archive_dir)

    def test_tilde_expanded_and_default_level(self):
        (self.home / "arch").mkdir()
        cfg = config.load({"ARCHIVE_DIR": "~/arch"})
        self.assertEqual(cfg.archive_dir, self.home / "arch")
        self.assertEqual(cfg.zstd_level, 10)

    def test_unset(self):
        with self.assertRaisesRegex(ConfigError, r"ARCHIVE_DIR.*\.config/arc/\.env"):
            config.load({})

    def test_missing_dir_not_created(self):
        missing = self.root / "Volumes" / "Backup" / "archive"
        with self.assertRaisesRegex(ConfigError, "does not exist"):
            config.load({"ARCHIVE_DIR": str(missing)})
        self.assertFalse(missing.exists())

    def test_not_a_directory(self):
        f = self.root / "file"
        f.write_text("")
        with self.assertRaisesRegex(ConfigError, "not a directory"):
            config.load({"ARCHIVE_DIR": str(f)})

    def test_bad_level(self):
        os.environ["ZSTD_LEVEL"] = "high"
        with self.assertRaisesRegex(ConfigError, "ZSTD_LEVEL"):
            config.load({"ARCHIVE_DIR": str(self.archive_dir)})
