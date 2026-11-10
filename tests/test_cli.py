import contextlib
import io
import os

from arc import cli
from helpers import TempEnvCase


class CliTests(TempEnvCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(list(argv))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def setUp(self):
        super().setUp()
        os.environ["ARCHIVE_DIR"] = str(self.archive_dir)

    def test_end_to_end(self):
        src = self.make_source("ClientX")
        code, out, _ = self.run_cli("add", str(src), "--delete")
        self.assertEqual(code, 0)
        archive_id = out.split()[0]
        self.assertTrue(archive_id.startswith("ClientX-"))
        self.assertFalse(src.exists())

        code, out, _ = self.run_cli("list", "--limit", "5")
        self.assertEqual(code, 0)
        self.assertIn(archive_id, out)
        self.assertIn("[deleted]", out)

        code, out, _ = self.run_cli("search", "clientx")
        self.assertEqual((code, out.count("\n")), (0, 1))
        code, out, _ = self.run_cli("search", "nomatch")
        self.assertEqual((code, out), (0, ""))

        code, out, _ = self.run_cli("restore", archive_id)
        self.assertEqual(code, 0)
        self.assertTrue((src / "a.txt").exists())

        code, _, err = self.run_cli("restore", archive_id)
        self.assertEqual(code, 1)
        self.assertIn("arc: error:", err)
        self.assertIn("--force", err)

    def test_empty_list(self):
        self.assertEqual(self.run_cli("list"), (0, "", ""))

    def test_config_error_exit_2(self):
        del os.environ["ARCHIVE_DIR"]
        code, _, err = self.run_cli("list")
        self.assertEqual(code, 2)
        self.assertIn("ARCHIVE_DIR", err)

    def test_archive_dir_flag(self):
        other = self.root / "other"
        other.mkdir()
        src = self.make_source()
        code, out, _ = self.run_cli("add", str(src), "--archive-dir", str(other))
        self.assertEqual(code, 0)
        self.assertIn(str(other), out)

    def test_operational_error_exit_1(self):
        code, _, err = self.run_cli("add", str(self.work / "missing"))
        self.assertEqual(code, 1)
        self.assertIn("does not exist", err)

    def test_usage_error_exit_2(self):
        self.assertEqual(self.run_cli("bogus")[0], 2)

    def test_human_size(self):
        self.assertEqual(cli.human_size(500), "500 B")
        self.assertEqual(cli.human_size(1536), "1.5 KB")
        self.assertEqual(cli.human_size(5 * 1024**3), "5.0 GB")
