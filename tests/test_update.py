import contextlib
import hashlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arc import cli, update
from arc.install import Installed
from arc.update import UpdateError

WHEEL = "arc-0.2.0-py3-none-any.whl"


class FakeRunner:
    """Stands in for gh/uv: records commands and simulates a release download."""

    def __init__(self, tools_dir, tag="v0.2.0", files=None):
        self.tools_dir = tools_dir
        self.tag = tag
        data = b"wheel bytes"
        self.files = files if files is not None else {
            WHEEL: data,
            "SHA256SUMS": f"{hashlib.sha256(data).hexdigest()}  {WHEEL}\n".encode(),
        }
        self.calls = []
        self.installed_bytes = None

    def __call__(self, cmd):
        self.calls.append(cmd)
        if cmd[:3] == ["uv", "tool", "dir"]:
            return str(self.tools_dir)
        if cmd[:3] == ["gh", "release", "view"]:
            return self.tag
        if cmd[:3] == ["gh", "release", "download"]:
            dest = Path(cmd[cmd.index("-D") + 1])
            for name, content in self.files.items():
                (dest / name).write_bytes(content)
            return ""
        if cmd[:3] == ["uv", "tool", "install"]:
            self.installed_bytes = Path(cmd[-1]).read_bytes()
            return ""
        raise AssertionError(f"unexpected command {cmd}")

    def ran(self, *prefix):
        return any(c[:len(prefix)] == list(prefix) for c in self.calls)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tools_dir = Path(tmp.name).resolve() / "tools"
        (self.tools_dir / "arc").mkdir(parents=True)
        self.patch(update.sys, "prefix", str(self.tools_dir / "arc"))

    def patch(self, target, attr, value):
        patcher = mock.patch.object(target, attr, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_update(self, inst, runner=None, force=False):
        runner = runner or FakeRunner(self.tools_dir)
        self.patch(update, "installed", lambda: inst)
        self.patch(update, "_run", runner)
        return update.update(force=force), runner

    def test_outdated_release_install_updates(self):
        msg, runner = self.run_update(Installed("0.1.0", "archive", "arc-0.1.0-py3-none-any.whl"))
        self.assertEqual(msg, "updated arc 0.1.0 → 0.2.0")
        self.assertEqual(runner.installed_bytes, b"wheel bytes")
        install_cmd = next(c for c in runner.calls if c[:3] == ["uv", "tool", "install"])
        self.assertIn("--force", install_cmd)
        self.assertEqual(install_cmd[install_cmd.index("--python") + 1], ">=3.14")

    def test_up_to_date_downloads_nothing(self):
        for version in ("0.2.0", "0.3.0"):
            with self.subTest(version=version):
                msg, runner = self.run_update(Installed(version, "archive", "x.whl"))
                self.assertEqual(msg, f"arc {version} is already up to date")
                self.assertFalse(runner.ran("gh", "release", "download"))

    def test_numeric_compare(self):
        msg, _ = self.run_update(Installed("0.9.0", "archive", "x.whl"), FakeRunner(self.tools_dir, tag="v0.10.0"))
        self.assertEqual(msg, "updated arc 0.9.0 → 0.10.0")

    def test_force_reinstalls_when_up_to_date(self):
        msg, runner = self.run_update(Installed("0.2.0", "archive", "x.whl"), force=True)
        self.assertEqual(msg, "updated arc 0.2.0 → 0.2.0")
        self.assertIsNotNone(runner.installed_bytes)

    def test_non_release_install_needs_force(self):
        for kind in ("local", "editable", "git", None):
            with self.subTest(kind=kind):
                runner = FakeRunner(self.tools_dir)
                with self.assertRaisesRegex(UpdateError, r"--force"):
                    self.run_update(Installed("0.1.0", kind, "/src/arc"), runner)
                self.assertFalse(runner.ran("gh", "release", "download"))

    def test_local_install_with_force(self):
        msg, runner = self.run_update(Installed("0.1.0", "local", "/src/arc"), force=True)
        self.assertEqual(msg, "updated arc 0.1.0 → 0.2.0")
        self.assertIsNotNone(runner.installed_bytes)

    def test_checksum_mismatch_not_installed(self):
        files = {WHEEL: b"tampered", "SHA256SUMS": f"{'0' * 64}  {WHEEL}\n".encode()}
        runner = FakeRunner(self.tools_dir, files=files)
        with self.assertRaisesRegex(UpdateError, "checksum mismatch"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), runner)
        self.assertIsNone(runner.installed_bytes)

    def test_wheel_missing_from_sums(self):
        runner = FakeRunner(self.tools_dir, files={WHEEL: b"x", "SHA256SUMS": b"abc  other.whl\n"})
        with self.assertRaisesRegex(UpdateError, "not listed"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), runner)
        self.assertIsNone(runner.installed_bytes)

    def test_no_sums_file(self):
        runner = FakeRunner(self.tools_dir, files={WHEEL: b"x"})
        with self.assertRaisesRegex(UpdateError, "no SHA256SUMS"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), runner)

    def test_no_wheel(self):
        runner = FakeRunner(self.tools_dir, files={"SHA256SUMS": b""})
        with self.assertRaisesRegex(UpdateError, "found 0"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), runner)

    def test_not_installed(self):
        with self.assertRaisesRegex(UpdateError, "not installed"):
            self.run_update(None)

    def test_not_a_uv_tool_install(self):
        self.patch(update.sys, "prefix", "/opt/some/venv")
        runner = FakeRunner(self.tools_dir)
        with self.assertRaisesRegex(UpdateError, "not installed with `uv tool`"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), runner)
        self.assertFalse(runner.ran("gh"))


class RunTests(unittest.TestCase):
    def test_missing_binary(self):
        with self.assertRaisesRegex(UpdateError, "definitely-not-a-real-cmd is not installed or not on PATH"):
            update._run(["definitely-not-a-real-cmd"])

    def test_failure_includes_stderr(self):
        with self.assertRaisesRegex(UpdateError, "failed: boom"):
            update._run([sys.executable, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"])

    def test_returns_stdout(self):
        self.assertEqual(update._run([sys.executable, "-c", "print('v0.2.0')"]), "v0.2.0")


class CliUpdateTests(unittest.TestCase):
    def run_cli(self, *argv, **patch_kwargs):
        out, err = io.StringIO(), io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != "ARCHIVE_DIR"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(update, "update", **patch_kwargs) as m, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue(), m

    def test_update_without_config(self):
        code, out, err, m = self.run_cli("update", return_value="updated arc 0.1.0 → 0.2.0")
        self.assertEqual((code, out, err), (0, "updated arc 0.1.0 → 0.2.0\n", ""))
        m.assert_called_once_with(force=False)

    def test_force_passed(self):
        _, _, _, m = self.run_cli("update", "--force", return_value="x")
        m.assert_called_once_with(force=True)

    def test_update_error_exit_1(self):
        code, out, err, _ = self.run_cli("update", side_effect=UpdateError("gh is not installed or not on PATH"))
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err, "arc: error: gh is not installed or not on PATH\n")
