"""Command-line entry point."""

import argparse
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from arc import archiver, config, github, history, restore, update
from arc.archiver import ArchiveError
from arc.config import ConfigError
from arc.github import GitHubError
from arc.install import version_string
from arc.progress import Progress, human_size
from arc.update import UpdateError

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2


def format_row(r: dict) -> str:
    deleted = "[deleted]" if r.get("source_deleted") else ""
    return f"{r.get('id', '?')}  {r.get('timestamp', '?')}  {human_size(r.get('size_after', 0)):>9}  {deleted:9}  {r.get('source_path', '?')}"


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--archive-dir", help="override ARCHIVE_DIR")

    parser = argparse.ArgumentParser(prog="arc", description="Archive folders to tar.zst with history and restore.")
    parser.add_argument("--version", action="version", version=version_string())
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", parents=[common], help="archive a folder")
    p.add_argument("folder")
    p.add_argument("--delete", action="store_true", help="delete the source after a verified, recorded archive")

    p = sub.add_parser("list", parents=[common], help="list archives, newest first")
    p.add_argument("--limit", type=int)

    p = sub.add_parser("search", parents=[common], help="search archives by source path or id")
    p.add_argument("term")

    p = sub.add_parser("restore", parents=[common], help="restore an archive by id")
    p.add_argument("id")
    p.add_argument("--to", help="restore into this directory instead of the original location")
    p.add_argument("--force", action="store_true", help="overwrite an existing target")

    p = sub.add_parser("update", help="install the latest release")
    p.add_argument("--force", action="store_true", help="reinstall the latest release even if it can't be compared")
    return parser


def confirm_repo(folder: str, archive_dir: Path) -> str | None:
    """Ask if the GitHub repo of the folder must be archived too. Return "owner/repo" on a Yes answer."""
    src = archiver.validate_source(folder, archive_dir)
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        return None
    repo = github.detect(src)
    if repo is None:
        return None
    reason = github.check(repo)
    if reason:
        print(f"arc: note: GitHub repo {repo} found, but {reason}; not archiving it", file=sys.stderr)
        return None
    print(f"Archive GitHub repo {repo} as well? [y/N] ", end="", file=sys.stderr, flush=True)
    return repo if sys.stdin.readline().strip().lower() in ("y", "yes") else None


def archive_repo(repo: str, rec: dict, archive_dir: Path) -> None:
    try:
        github.archive(repo)
    except GitHubError as e:
        raise GitHubError(
            f"archived to {archive_dir / rec['archive_path']} but archiving GitHub repo {repo} failed: {e}") from e
    try:
        history.append(archive_dir, {
            "event": "repo_archived",
            "id": rec["id"],
            "timestamp": archiver.iso(datetime.now(UTC)),
            "repo": repo,
        })
    except OSError as e:
        raise GitHubError(f"GitHub repo {repo} is archived but the history append failed: {e}") from e
    print(f"archived GitHub repo {repo}")


def run(args: argparse.Namespace, progress: Progress) -> None:
    if args.command == "update":
        print(update.update(force=args.force))
        return
    cfg = config.load({"ARCHIVE_DIR": args.archive_dir})
    if args.command == "add":
        repo = confirm_repo(args.folder, cfg.archive_dir)
        rec = archiver.create(args.folder, cfg, delete=args.delete, progress=progress)
        print(f"{rec['id']}  {cfg.archive_dir / rec['archive_path']}")
        if rec["source_deleted"]:
            print(f"deleted {rec['source_path']}")
        if repo:
            archive_repo(repo, rec, cfg.archive_dir)
    elif args.command in ("list", "search"):
        rows = (history.list_archives(cfg.archive_dir, args.limit) if args.command == "list"
                else history.search(cfg.archive_dir, args.term))
        for r in rows:
            print(format_row(r))
    elif args.command == "restore":
        dest = restore.restore(cfg, args.id, to=args.to, force=args.force, progress=progress)
        print(f"restored to {dest}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    progress = Progress()
    try:
        run(args, progress)
    except (ConfigError, ArchiveError, GitHubError, UpdateError, OSError, tarfile.TarError) as e:
        progress.close()
        print(f"arc: error: {e}", file=sys.stderr)
        return EXIT_USAGE if isinstance(e, ConfigError) else EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
