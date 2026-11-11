"""Self-update to the latest GitHub release, downloaded with gh and installed with uv."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from arc.archiver import sha256_file
from arc.install import installed

REPO = "byteability/arc"
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


def _version_key(version: str) -> tuple[int, ...] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    return tuple(int(part) for part in match.groups()) if match else None


def _checksums(path: Path) -> dict[str, str]:
    if not path.exists():
        raise UpdateError("release has no SHA256SUMS file; not installing")
    sums = {}
    for line in path.read_text().splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            sums[parts[1].lstrip("*")] = parts[0].lower()
    return sums


def update(force: bool = False) -> str:
    inst = installed()
    if inst is None:
        raise UpdateError("arc is not installed (running from source); nothing to update")
    tools_dir = Path(_run(["uv", "tool", "dir"])).resolve()
    if Path(sys.prefix).resolve().parent != tools_dir:
        raise UpdateError(f"arc is not installed with `uv tool` (environment: {sys.prefix}); "
                          "update it the way you installed it")

    tag = _run(["gh", "release", "view", "-R", REPO, "--json", "tagName", "-q", ".tagName"])
    latest = tag.removeprefix("v")
    if not force:
        if inst.kind != "archive":
            raise UpdateError(f"arc {inst.version} was installed from {SOURCE_PHRASES.get(inst.kind, inst.kind)}, "
                              f"so its version can't be compared with releases; "
                              f"run `arc update --force` to install {tag}")
        current, new = _version_key(inst.version), _version_key(latest)
        if current and new and current >= new:
            return f"arc {inst.version} is already up to date"

    with tempfile.TemporaryDirectory() as tmp:
        download = Path(tmp)
        _run(["gh", "release", "download", tag, "-R", REPO, "-p", "*.whl", "-p", "SHA256SUMS", "-D", tmp])
        wheels = sorted(download.glob("*.whl"))
        if len(wheels) != 1:
            raise UpdateError(f"expected one wheel in release {tag}, found {len(wheels)}")
        wheel = wheels[0]
        expected = _checksums(download / "SHA256SUMS").get(wheel.name)
        if expected is None:
            raise UpdateError(f"{wheel.name} is not listed in SHA256SUMS; not installing")
        if sha256_file(wheel) != expected:
            raise UpdateError(f"checksum mismatch for {wheel.name}; not installing")
        _run(["uv", "tool", "install", "--force", "--python", ">=3.14", str(wheel)])
    return f"updated arc {inst.version} → {latest}"
