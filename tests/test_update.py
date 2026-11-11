import contextlib
import hashlib
import http.server
import io
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from arc import cli, update
from arc.install import Installed
from arc.update import UpdateError

WHEEL = "arc-0.2.0-py3-none-any.whl"
BASE = "https://github.com/byteability/arc/releases/download"


def asset(name, tag="v0.2.0"):
    return {"name": name, "browser_download_url": f"{BASE}/{tag}/{name}"}


class FakeUv:
    """Stands in for uv. Any other command (e.g. gh) fails the test."""

    def __init__(self, tools_dir):
        self.tools_dir = tools_dir
        self.calls = []
        self.installed_bytes = None

    def __call__(self, cmd):
        self.calls.append(cmd)
        if cmd[:3] == ["uv", "tool", "dir"]:
            return str(self.tools_dir)
        if cmd[:3] == ["uv", "tool", "install"]:
            self.installed_bytes = Path(cmd[-1]).read_bytes()
            return ""
        raise AssertionError(f"unexpected command {cmd}")


class FakeGitHub:
    """Stands in for the releases API and asset downloads."""

    def __init__(self, tag="v0.2.0", files=None, assets=None):
        data = b"wheel bytes"
        self.files = files if files is not None else {
            WHEEL: data,
            "SHA256SUMS": f"{hashlib.sha256(data).hexdigest()}  {WHEEL}\n".encode(),
        }
        self.release = {"tag_name": tag,
                        "assets": assets if assets is not None else [asset(n, tag) for n in self.files]}
        self.api_calls, self.downloads = [], []

    def get_json(self, url):
        self.api_calls.append(url)
        return self.release

    def download(self, url, dest):
        self.downloads.append(url)
        dest.write_bytes(self.files[url.rsplit("/", 1)[-1]])


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

    def run_update(self, inst, github=None, force=False):
        github = github or FakeGitHub()
        uv = FakeUv(self.tools_dir)
        self.patch(update, "installed", lambda: inst)
        self.patch(update, "_run", uv)
        self.patch(update, "_get_json", github.get_json)
        self.patch(update, "_download", github.download)
        self.uv, self.github = uv, github
        return update.update(force=force)

    def test_outdated_release_install_updates(self):
        msg = self.run_update(Installed("0.1.0", "archive", "arc-0.1.0-py3-none-any.whl"))
        self.assertEqual(msg, "updated arc 0.1.0 → 0.2.0")
        self.assertEqual(self.github.api_calls, [update.LATEST_RELEASE_URL])
        self.assertEqual(sorted(self.github.downloads), [f"{BASE}/v0.2.0/SHA256SUMS", f"{BASE}/v0.2.0/{WHEEL}"])
        self.assertEqual(self.uv.installed_bytes, b"wheel bytes")
        install_cmd = next(c for c in self.uv.calls if c[:3] == ["uv", "tool", "install"])
        self.assertIn("--force", install_cmd)
        self.assertEqual(install_cmd[install_cmd.index("--python") + 1], ">=3.14")
        self.assertFalse(any(c[0] == "gh" for c in self.uv.calls))

    def test_up_to_date_downloads_nothing(self):
        for version in ("0.2.0", "0.3.0"):
            with self.subTest(version=version):
                msg = self.run_update(Installed(version, "archive", "x.whl"))
                self.assertEqual(msg, f"arc {version} is already up to date")
                self.assertEqual(self.github.downloads, [])

    def test_numeric_compare(self):
        github = FakeGitHub(tag="v0.10.0", files={"arc-0.10.0-py3-none-any.whl": b"w",
                                                   "SHA256SUMS": f"{hashlib.sha256(b'w').hexdigest()}  arc-0.10.0-py3-none-any.whl\n".encode()})
        self.assertEqual(self.run_update(Installed("0.9.0", "archive", "x.whl"), github), "updated arc 0.9.0 → 0.10.0")

    def test_force_reinstalls_when_up_to_date(self):
        msg = self.run_update(Installed("0.2.0", "archive", "x.whl"), force=True)
        self.assertEqual(msg, "updated arc 0.2.0 → 0.2.0")
        self.assertIsNotNone(self.uv.installed_bytes)

    def test_non_release_install_needs_force(self):
        for kind in ("local", "editable", "git", None):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(UpdateError, r"--force"):
                    self.run_update(Installed("0.1.0", kind, "/src/arc"))
                self.assertEqual(self.github.downloads, [])

    def test_local_install_with_force(self):
        msg = self.run_update(Installed("0.1.0", "local", "/src/arc"), force=True)
        self.assertEqual(msg, "updated arc 0.1.0 → 0.2.0")
        self.assertIsNotNone(self.uv.installed_bytes)

    def test_checksum_mismatch_not_installed(self):
        github = FakeGitHub(files={WHEEL: b"tampered", "SHA256SUMS": f"{'0' * 64}  {WHEEL}\n".encode()})
        with self.assertRaisesRegex(UpdateError, "checksum mismatch"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), github)
        self.assertIsNone(self.uv.installed_bytes)

    def test_wheel_missing_from_sums(self):
        github = FakeGitHub(files={WHEEL: b"x", "SHA256SUMS": b"abc  other.whl\n"})
        with self.assertRaisesRegex(UpdateError, "not listed"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), github)
        self.assertIsNone(self.uv.installed_bytes)

    def test_no_sums_asset(self):
        github = FakeGitHub(files={WHEEL: b"x"})
        with self.assertRaisesRegex(UpdateError, "no SHA256SUMS"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), github)
        self.assertEqual(github.downloads, [])

    def test_wheel_count_must_be_one(self):
        for files in ({"SHA256SUMS": b""}, {"a-1-py3-none-any.whl": b"", "b-1-py3-none-any.whl": b"", "SHA256SUMS": b""}):
            with self.subTest(files=list(files)):
                with self.assertRaisesRegex(UpdateError, "expected one wheel"):
                    self.run_update(Installed("0.1.0", "archive", "x.whl"), FakeGitHub(files=files))

    def test_unsafe_asset_names_ignored(self):
        github = FakeGitHub(assets=[asset("../evil.whl"), asset("sub/x.whl"), asset("SHA256SUMS")])
        with self.assertRaisesRegex(UpdateError, "found 0"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), github)

    def test_release_without_tag(self):
        github = FakeGitHub()
        github.release = {"assets": []}
        with self.assertRaisesRegex(UpdateError, "no tag"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"), github)

    def test_not_installed(self):
        with self.assertRaisesRegex(UpdateError, "not installed"):
            self.run_update(None)

    def test_not_a_uv_tool_install(self):
        self.patch(update.sys, "prefix", "/opt/some/venv")
        with self.assertRaisesRegex(UpdateError, "not installed with `uv tool`"):
            self.run_update(Installed("0.1.0", "archive", "x.whl"))
        self.assertEqual(self.github.api_calls, [])


class _Handler(http.server.BaseHTTPRequestHandler):
    user_agents = []

    def do_GET(self):
        _Handler.user_agents.append(self.headers.get("User-Agent"))
        routes = {
            "/release": (200, b'{"tag_name": "v9.9.9", "assets": []}'),
            "/list": (200, b"[1, 2]"),
            "/notjson": (200, b"<html>"),
            "/file": (200, b"asset bytes"),
            "/missing": (404, b"not found"),
        }
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/file")
            self.end_headers()
            return
        status, body = routes.get(self.path, (500, b""))
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_json_and_user_agent(self):
        self.assertEqual(update._get_json(f"{self.base}/release")["tag_name"], "v9.9.9")
        self.assertEqual(_Handler.user_agents[-1], update.USER_AGENT)

    def test_download_follows_redirect(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "a"
            update._download(f"{self.base}/redirect", dest)
            self.assertEqual(dest.read_bytes(), b"asset bytes")

    def test_http_error_names_url_and_status(self):
        with self.assertRaisesRegex(UpdateError, r"/missing: HTTP 404"):
            update._get_json(f"{self.base}/missing")

    def test_invalid_or_unexpected_json(self):
        with self.assertRaisesRegex(UpdateError, "not valid JSON"):
            update._get_json(f"{self.base}/notjson")
        with self.assertRaisesRegex(UpdateError, "unexpected response"):
            update._get_json(f"{self.base}/list")

    def test_network_error_names_url(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        with self.assertRaisesRegex(UpdateError, rf"127\.0\.0\.1:{port}/x: "):
            update._get_json(f"http://127.0.0.1:{port}/x")


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
        code, out, err, _ = self.run_cli("update", side_effect=UpdateError("uv is not installed or not on PATH"))
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err, "arc: error: uv is not installed or not on PATH\n")
