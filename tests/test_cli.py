import contextlib
import io
import os
import tarfile
from unittest import mock

from arc import cli, history
from arc.github import GitHubError
from helpers import TempEnvCase


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


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
        code, out, err = self.run_cli("add", str(src), "--delete")
        self.assertEqual((code, err), (0, ""))  # stderr is not a TTY here: no progress output
        self.assertEqual(out.count("\n"), 2)  # id + path, "deleted ..."
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

    def test_error_starts_on_own_line_after_progress(self):
        src = self.make_source()
        out, err = io.StringIO(), FakeTTY()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(tarfile.TarFile, "addfile", side_effect=OSError("disk full")):
            code = cli.main(["add", str(src)])
        self.assertEqual(code, 1)
        self.assertIn("compressing", err.getvalue())
        self.assertIn("\narc: error: disk full", err.getvalue())
        self.assertEqual(out.getvalue(), "")

    def make_clone(self, name="proj"):
        src = self.make_source(name)
        (src / ".git").mkdir()
        (src / ".git" / "config").write_text('[remote "origin"]\n\turl = git@github.com:acme/proj.git\n')
        return src

    def run_tty(self, *argv, answer="y\n", reason=None, archive_error=None, stdin_tty=True):
        """Run on fake terminals with gh mocked. Returns (code, stdout, stderr, check mock, archive mock)."""
        out, err = io.StringIO(), FakeTTY()
        stdin = FakeTTY(answer) if stdin_tty else io.StringIO(answer)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), mock.patch("sys.stdin", stdin), \
                mock.patch("arc.github.check", return_value=reason) as check, \
                mock.patch("arc.github.archive", side_effect=archive_error) as archive:
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue(), check, archive

    def events(self):
        return [(r["event"], r.get("repo")) for r in history.read(self.archive_dir)]

    def test_repo_yes(self):
        src = self.make_clone()
        code, out, err, _, archive = self.run_tty("add", str(src), "--delete", answer="YES\n")
        self.assertEqual(code, 0)
        self.assertTrue(err.startswith("Archive GitHub repo acme/proj as well? [y/N] "))
        archive.assert_called_once_with("acme/proj")
        lines = out.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[1].startswith("deleted "))
        self.assertEqual(lines[2], "archived GitHub repo acme/proj")
        self.assertEqual(self.events(), [("add", None), ("repo_archived", "acme/proj")])
        records = list(history.read(self.archive_dir))
        self.assertEqual(records[1]["id"], records[0]["id"])
        self.assertFalse(src.exists())

    def test_repo_no_answers(self):
        for i, answer in enumerate(("\n", "n\n", "maybe\n", "")):  # "" is end of input
            with self.subTest(answer=answer):
                src = self.make_clone(f"c{i}")
                code, out, err, _, archive = self.run_tty("add", str(src), "--delete", answer=answer)
                self.assertEqual(code, 0)
                self.assertIn("Archive GitHub repo acme/proj", err)
                archive.assert_not_called()
                self.assertNotIn("archived GitHub repo", out)
                self.assertNotIn("repo_archived", [e for e, _ in self.events()])

    def test_repo_not_interactive(self):
        src = self.make_clone()
        with mock.patch("arc.github.check") as check, mock.patch("arc.github.archive") as archive:
            code, out, err = self.run_cli("add", str(src))
        self.assertEqual((code, err, out.count("\n")), (0, "", 1))
        check.assert_not_called()
        archive.assert_not_called()

    def test_repo_stdin_not_tty(self):
        code, _, err, check, archive = self.run_tty("add", str(self.make_clone()), stdin_tty=False)
        self.assertEqual(code, 0)
        self.assertNotIn("GitHub", err)
        check.assert_not_called()
        archive.assert_not_called()

    def test_repo_skip_note(self):
        code, out, err, _, archive = self.run_tty("add", str(self.make_clone()), reason="it is already archived")
        self.assertEqual(code, 0)
        self.assertTrue(err.startswith(
            "arc: note: GitHub repo acme/proj found, but it is already archived; not archiving it\n"))
        self.assertNotIn("[y/N]", err)
        archive.assert_not_called()
        self.assertEqual(out.count("\n"), 1)

    def test_no_repo_no_prompt(self):
        code, _, err, check, _ = self.run_tty("add", str(self.make_source()))
        self.assertEqual(code, 0)
        self.assertNotIn("GitHub", err)
        check.assert_not_called()

    def test_invalid_source_no_prompt(self):
        link = self.work / "link"
        link.symlink_to(self.make_clone())
        code, _, err, check, _ = self.run_tty("add", str(link))
        self.assertEqual(code, 1)
        self.assertNotIn("GitHub", err)
        check.assert_not_called()

    def test_repo_not_archived_when_local_archive_fails(self):
        src = self.make_clone()
        with mock.patch.object(tarfile.TarFile, "addfile", side_effect=OSError("disk full")):
            code, _, _, _, archive = self.run_tty("add", str(src))
        self.assertEqual(code, 1)
        archive.assert_not_called()

    def test_repo_not_archived_when_delete_fails(self):
        src = self.make_clone()
        with mock.patch("arc.archiver.shutil.rmtree", side_effect=OSError("denied")):
            code, _, _, _, archive = self.run_tty("add", str(src), "--delete")
        self.assertEqual(code, 1)
        archive.assert_not_called()
        self.assertEqual([e for e, _ in self.events()], ["add", "delete_failed"])

    def test_repo_archive_fails(self):
        src = self.make_clone()
        code, out, err, _, _ = self.run_tty("add", str(src), archive_error=GitHubError("HTTP 403"))
        self.assertEqual(code, 1)
        archive_path = out.split()[1]
        self.assertTrue(os.path.exists(archive_path))
        self.assertIn(f"arc: error: archived to {archive_path} but archiving GitHub repo acme/proj failed: HTTP 403", err)
        self.assertEqual(self.events(), [("add", None)])

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
