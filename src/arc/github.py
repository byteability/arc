"""Find the GitHub repo of a folder and archive it on GitHub through the gh CLI."""

import json
import re
import shutil
import subprocess
from pathlib import Path

CHECK_TIMEOUT, ARCHIVE_TIMEOUT = 10, 30

_URL = re.compile(
    r"(?:git@github\.com:|ssh://git@github\.com/|https://(?:[^@/]+@)?github\.com/)"
    r"([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9._-]+?)(?:\.git)?/?",
    re.IGNORECASE,
)


class GitHubError(Exception):
    pass


def _origin_url(config: Path) -> str | None:
    section = None
    for line in config.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("["):
            section = line
        elif section == '[remote "origin"]':
            key, sep, value = line.partition("=")
            if sep and key.strip().lower() == "url":
                return value.strip()
    return None


def detect(src: Path) -> str | None:
    """Return "owner/repo" when src is the top folder of a github.com clone."""
    git_dir = src / ".git"
    if not git_dir.is_dir():
        return None
    try:
        url = _origin_url(git_dir / "config")
    except (OSError, UnicodeDecodeError):
        return None
    match = _URL.fullmatch(url or "")
    return f"{match[1]}/{match[2]}" if match else None


def _gh(*args: str, timeout: int) -> str:
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise GitHubError(f"gh timed out after {timeout} s") from e
    except OSError as e:
        raise GitHubError(str(e)) from e
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        raise GitHubError(lines[0] if lines else f"gh exited with status {result.returncode}")
    return result.stdout


def check(repo: str) -> str | None:
    """Return the reason why the repo cannot be archived now, or None when it can."""
    if shutil.which("gh") is None:
        return "gh is not installed"
    try:
        info = json.loads(_gh("repo", "view", repo, "--json", "isArchived,viewerCanAdminister", timeout=CHECK_TIMEOUT))
    except (GitHubError, ValueError) as e:
        return f"gh could not read it ({e})"
    if info.get("isArchived"):
        return "it is already archived"
    if not info.get("viewerCanAdminister"):
        return "you have no admin permission on it"
    return None


def archive(repo: str) -> None:
    _gh("repo", "archive", repo, "--yes", timeout=ARCHIVE_TIMEOUT)
