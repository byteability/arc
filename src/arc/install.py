"""How arc was installed: version plus the PEP 610 install source (direct_url.json)."""

import json
from dataclasses import dataclass
from importlib import metadata
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

SOURCE_LABELS = {"archive": "{}", "local": "local: {}", "editable": "local, editable: {}", "git": "git: {}"}


@dataclass(frozen=True)
class Installed:
    version: str
    kind: str | None  # "archive", "local", "editable", "git", or None if not recorded
    detail: str | None  # archive file name, local path, or short commit


def _source(info: dict) -> tuple[str | None, str | None]:
    path = unquote(urlparse(info.get("url", "")).path)
    if isinstance(info.get("vcs_info"), dict):
        return "git", info["vcs_info"].get("commit_id", "")[:7]
    if isinstance(info.get("dir_info"), dict):
        return ("editable" if info["dir_info"].get("editable") else "local"), path
    if "archive_info" in info:
        return "archive", PurePosixPath(path).name
    return None, None


def installed() -> Installed | None:
    try:
        dist = metadata.distribution("arc")
    except metadata.PackageNotFoundError:
        return None
    try:
        info = json.loads(dist.read_text("direct_url.json") or "null")
    except json.JSONDecodeError:
        info = None
    kind, detail = _source(info) if isinstance(info, dict) else (None, None)
    return Installed(dist.version, kind, detail)


def version_string() -> str:
    inst = installed()
    if inst is None:
        return "arc (not installed)"
    text = f"arc {inst.version}"
    return f"{text} ({SOURCE_LABELS[inst.kind].format(inst.detail)})" if inst.kind else text
