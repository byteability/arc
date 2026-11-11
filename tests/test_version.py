import contextlib
import io
import os
import unittest
from importlib import metadata
from unittest import mock

from arc import cli


class FakeDist:
    def __init__(self, version="0.1.0", direct_url=None):
        self.version = version
        self._direct_url = direct_url

    def read_text(self, name):
        return self._direct_url if name == "direct_url.json" else None


def version_with(direct_url=None):
    with mock.patch.object(cli.metadata, "distribution", return_value=FakeDist(direct_url=direct_url)):
        return cli.version_string()


class VersionStringTests(unittest.TestCase):
    def test_wheel(self):
        record = '{"url": "file:///Users/me/Downloads/arc-0.1.0-py3-none-any.whl", "archive_info": {"hashes": {}}}'
        self.assertEqual(version_with(record), "arc 0.1.0 (arc-0.1.0-py3-none-any.whl)")

    def test_local_folder(self):
        record = '{"url": "file:///Users/me/src/my%20arc", "dir_info": {}}'
        self.assertEqual(version_with(record), "arc 0.1.0 (local: /Users/me/src/my arc)")

    def test_editable(self):
        record = '{"url": "file:///Users/me/src/arc", "dir_info": {"editable": true}}'
        self.assertEqual(version_with(record), "arc 0.1.0 (local, editable: /Users/me/src/arc)")

    def test_git(self):
        record = ('{"url": "ssh://git@github.com/byteability/arc", '
                  '"vcs_info": {"vcs": "git", "commit_id": "1a2b3c4d5e6f", "requested_revision": "v0.1.0"}}')
        self.assertEqual(version_with(record), "arc 0.1.0 (git: 1a2b3c4)")

    def test_no_record(self):
        self.assertEqual(version_with(None), "arc 0.1.0")

    def test_malformed_or_unknown_record(self):
        for record in ("{not json", "[]", '{"url": "https://x"}'):
            with self.subTest(record=record):
                self.assertEqual(version_with(record), "arc 0.1.0")

    def test_not_installed(self):
        with mock.patch.object(cli.metadata, "distribution", side_effect=metadata.PackageNotFoundError("arc")):
            self.assertEqual(cli.version_string(), "arc (not installed)")


class VersionFlagTests(unittest.TestCase):
    def test_flag_prints_one_line_and_exits_0_without_config(self):
        out, err = io.StringIO(), io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != "ARCHIVE_DIR"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(cli.metadata, "distribution", return_value=FakeDist()), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                self.assertRaises(SystemExit) as exit_info:
            cli.main(["--version"])
        self.assertEqual(exit_info.exception.code, 0)
        self.assertEqual(out.getvalue(), "arc 0.1.0\n")
        self.assertEqual(err.getvalue(), "")
