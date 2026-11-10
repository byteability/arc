"""Command-line entry point."""

import argparse
import sys
import tarfile

from arc import archiver, config, history, restore
from arc.archiver import ArchiveError
from arc.config import ConfigError

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


def format_row(r: dict) -> str:
    deleted = "[deleted]" if r.get("source_deleted") else ""
    return f"{r.get('id', '?')}  {r.get('timestamp', '?')}  {human_size(r.get('size_after', 0)):>9}  {deleted:9}  {r.get('source_path', '?')}"


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--archive-dir", help="override ARCHIVE_DIR")

    parser = argparse.ArgumentParser(prog="arc", description="Archive folders to tar.zst with history and restore.")
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
    return parser


def run(args: argparse.Namespace) -> None:
    cfg = config.load({"ARCHIVE_DIR": args.archive_dir})
    if args.command == "add":
        rec = archiver.create(args.folder, cfg, delete=args.delete)
        print(f"{rec['id']}  {cfg.archive_dir / rec['archive_path']}")
        if rec["source_deleted"]:
            print(f"deleted {rec['source_path']}")
    elif args.command in ("list", "search"):
        rows = (history.list_archives(cfg.archive_dir, args.limit) if args.command == "list"
                else history.search(cfg.archive_dir, args.term))
        for r in rows:
            print(format_row(r))
    elif args.command == "restore":
        print(f"restored to {restore.restore(cfg, args.id, to=args.to, force=args.force)}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except ConfigError as e:
        print(f"arc: error: {e}", file=sys.stderr)
        return EXIT_USAGE
    except (ArchiveError, OSError, tarfile.TarError) as e:
        print(f"arc: error: {e}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
