import subprocess
from unittest import mock

from arc import github
from arc.github import GitHubError
from helpers import TempEnvCase


def done(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["gh"], returncode, stdout, stderr)


class DetectTests(TempEnvCase):
    def clone(self, url, remote="origin", name="proj"):
        src = self.make_source(name)
        (src / ".git").mkdir()
        (src / ".git" / "config").write_text(
            f'[core]\n\tbare = false\n[remote "{remote}"]\n\turl = {url}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
            '[branch "main"]\n\tremote = origin\n')
        return src

    def test_url_forms(self):
        for i, url in enumerate(("git@github.com:acme/proj.git", "ssh://git@github.com/acme/proj.git",
                                 "https://github.com/acme/proj", "https://me@GitHub.com/acme/proj.git/")):
            with self.subTest(url=url):
                self.assertEqual(github.detect(self.clone(url, name=f"c{i}")), "acme/proj")

    def test_no_repo(self):
        for i, url in enumerate(("git@gitlab.com:acme/proj.git", "github-work:acme/proj.git", "https://github.com/acme",
                                 "git@github.com:-x/proj.git", "https://github.com/acme/proj/extra")):
            with self.subTest(url=url):
                self.assertIsNone(github.detect(self.clone(url, name=f"c{i}")))

    def test_no_origin_remote(self):
        self.assertIsNone(github.detect(self.clone("git@github.com:acme/proj.git", remote="upstream")))

    def test_no_git_dir(self):
        self.assertIsNone(github.detect(self.make_source()))

    def test_git_is_a_file(self):
        src = self.make_source()
        (src / ".git").write_text("gitdir: ../elsewhere\n")
        self.assertIsNone(github.detect(src))

    def test_subfolder_of_clone(self):
        self.assertIsNone(github.detect(self.clone("git@github.com:acme/proj.git") / "sub"))

    def test_unreadable_config(self):
        src = self.make_source()
        (src / ".git").mkdir()
        self.assertIsNone(github.detect(src))  # config missing
        (src / ".git" / "config").write_bytes(b"\xff\xfe")
        self.assertIsNone(github.detect(src))


class GhTests(TempEnvCase):
    def check(self, result=None, which="/usr/bin/gh", side_effect=None):
        with mock.patch("arc.github.shutil.which", return_value=which), \
                mock.patch("arc.github.subprocess.run", return_value=result, side_effect=side_effect) as run:
            return github.check("acme/proj"), run

    def test_check_ok(self):
        reason, run = self.check(done(stdout='{"isArchived": false, "viewerCanAdminister": true}'))
        self.assertIsNone(reason)
        self.assertEqual(run.call_args.args[0],
                         ["gh", "repo", "view", "acme/proj", "--json", "isArchived,viewerCanAdminister"])
        self.assertEqual(run.call_args.kwargs["timeout"], 10)

    def test_check_gh_missing(self):
        reason, run = self.check(which=None)
        self.assertIn("not installed", reason)
        run.assert_not_called()

    def test_check_gh_fails(self):
        reason, _ = self.check(done(1, stderr="To get started with GitHub CLI, please run:  gh auth login\nmore\n"))
        self.assertIn("gh auth login", reason)
        self.assertNotIn("more", reason)

    def test_check_timeout(self):
        reason, _ = self.check(side_effect=subprocess.TimeoutExpired("gh", 10))
        self.assertIn("timed out", reason)

    def test_check_bad_json(self):
        self.assertIsNotNone(self.check(done(stdout="not json"))[0])

    def test_check_already_archived(self):
        reason, _ = self.check(done(stdout='{"isArchived": true, "viewerCanAdminister": true}'))
        self.assertIn("already archived", reason)

    def test_check_no_admin(self):
        reason, _ = self.check(done(stdout='{"isArchived": false, "viewerCanAdminister": false}'))
        self.assertIn("no admin permission", reason)

    def test_archive_ok(self):
        with mock.patch("arc.github.subprocess.run", return_value=done()) as run:
            github.archive("acme/proj")
        self.assertEqual(run.call_args.args[0], ["gh", "repo", "archive", "acme/proj", "--yes"])
        self.assertEqual(run.call_args.kwargs["timeout"], 30)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_archive_failures(self):
        for kwargs, text in (({"return_value": done(1, stderr="HTTP 403: Must have admin rights\n")}, "HTTP 403"),
                             ({"return_value": done(2)}, "status 2"),
                             ({"side_effect": subprocess.TimeoutExpired("gh", 30)}, "timed out"),
                             ({"side_effect": FileNotFoundError("gh")}, "gh")):
            with self.subTest(text=text), mock.patch("arc.github.subprocess.run", **kwargs):
                with self.assertRaisesRegex(GitHubError, text):
                    github.archive("acme/proj")
