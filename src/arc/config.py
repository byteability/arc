"""Configuration: flags > environment > ~/.config/arc/.env > defaults."""

import os
from dataclasses import dataclass
from pathlib import Path

GLOBAL_ENV = "~/.config/arc/.env"
DEFAULT_ZSTD_LEVEL = 10


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    archive_dir: Path
    zstd_level: int


def parse_env_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load(flags: dict[str, str | None]) -> Config:
    file_values = parse_env_file(Path(GLOBAL_ENV).expanduser())

    def get(key: str) -> str | None:
        for source in (flags, os.environ, file_values):
            value = source.get(key)
            if value:
                return value
        return None

    raw_dir = get("ARCHIVE_DIR")
    if raw_dir is None:
        raise ConfigError(f"ARCHIVE_DIR is not set (use --archive-dir, the environment, or {GLOBAL_ENV})")
    archive_dir = Path(os.path.abspath(Path(raw_dir).expanduser()))
    if not archive_dir.exists():
        raise ConfigError(f"ARCHIVE_DIR does not exist: {archive_dir}")
    if not archive_dir.is_dir():
        raise ConfigError(f"ARCHIVE_DIR is not a directory: {archive_dir}")

    raw_level = get("ZSTD_LEVEL")
    try:
        level = int(raw_level) if raw_level is not None else DEFAULT_ZSTD_LEVEL
    except ValueError:
        raise ConfigError(f"ZSTD_LEVEL must be an integer, got {raw_level!r}") from None

    return Config(archive_dir=archive_dir, zstd_level=level)
