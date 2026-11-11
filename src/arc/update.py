"""Self-update to the latest GitHub release: public API + HTTPS download, installed with uv."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

from arc.archiver import sha256_file
from arc.install import installed

REPO = "byteability/arc"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
USER_AGENT = "arc-updater"
TIMEOUT = 30
SOURCE_PHRASES = {"local": "a local folder", "editable": "a local folder", "git": "git", None: "an unrecorded source"}


class UpdateError(Exception):
    pass


def _run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise UpdateError(f"{cmd[0]} is not installed or not on PATH") from None
    if result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip()
        raise UpdateError(f"`{' '.join(cmd)}` failed: {output}")
    return result.stdout.strip()


def _open(url: str, accept: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        return urllib.request.urlopen(request, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        raise UpdateError(f"{url}: HTTP {e.code} {e.reason}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise UpdateError(f"{url}: {getattr(e, 'reason', e)}") from None


def _get_json(url: str) -> dict:
    with _open(url, "application/vnd.github+json") as response:
        try:
            data = json.load(response)
        except json.JSONDecodeError:
            raise UpdateError(f"{url}: response is not valid JSON") from None
    if not isinstance(data, dict):
        raise UpdateError(f"{url}: unexpected response")
    return data


def _download(url: str, dest: Path) -> None:
    with _open(url, "application/octet-stream") as response, dest.open("wb") as f:
        shutil.copyfileobj(response, f)


def _version_key(version: str) -> tuple[int, ...] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    return tuple(int(part) for part in match.groups()) if match else None


def _checksums(path: Path) -> dict[str, str]:
    sums = {}
    for line in path.read_text().splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            sums[parts[1].lstrip("*")] = parts[0].lower()
    return sums


def _release_assets(release: dict) -> dict[str, str]:
    """Asset name -> download URL, ignoring names that aren't plain file names."""
    assets = {}
    for asset in release.get("assets") or []:
        name, url = asset.get("name"), asset.get("browser_download_url")
        if isinstance(name, str) and isinstance(url, str) and name == PurePosixPath(name).name and name not in ("", ".", ".."):
            assets[name] = url
    return assets


def update(force: bool = False) -> str:
    inst = installed()
    if inst is None:
        raise UpdateError("arc is not installed (running from source); nothing to update")
    tools_dir = Path(_run(["uv", "tool", "dir"])).resolve()
    if Path(sys.prefix).resolve().parent != tools_dir:
        raise UpdateError(f"arc is not installed with `uv tool` (environment: {sys.prefix}); "
                          "update it the way you installed it")

    release = _get_json(LATEST_RELEASE_URL)
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not tag:
        raise UpdateError(f"{LATEST_RELEASE_URL}: latest release has no tag")
    latest = tag.removeprefix("v")
    if not force:
        if inst.kind != "archive":
            raise UpdateError(f"arc {inst.version} was installed from {SOURCE_PHRASES.get(inst.kind, inst.kind)}, "
                              f"so its version can't be compared with releases; "
                              f"run `arc update --force` to install {tag}")
        current, new = _version_key(inst.version), _version_key(latest)
        if current and new and current >= new:
            return f"arc {inst.version} is already up to date"

    assets = _release_assets(release)
    wheels = sorted(name for name in assets if name.endswith(".whl"))
    if len(wheels) != 1:
        raise UpdateError(f"expected one wheel in release {tag}, found {len(wheels)}")
    if "SHA256SUMS" not in assets:
        raise UpdateError("release has no SHA256SUMS file; not installing")

    with tempfile.TemporaryDirectory() as tmp:
        wheel, sums = Path(tmp) / wheels[0], Path(tmp) / "SHA256SUMS"
        _download(assets[wheel.name], wheel)
        _download(assets["SHA256SUMS"], sums)
        expected = _checksums(sums).get(wheel.name)
        if expected is None:
            raise UpdateError(f"{wheel.name} is not listed in SHA256SUMS; not installing")
        if sha256_file(wheel) != expected:
            raise UpdateError(f"checksum mismatch for {wheel.name}; not installing")
        _run(["uv", "tool", "install", "--force", "--python", ">=3.14", str(wheel)])
    return f"updated arc {inst.version} → {latest}"
