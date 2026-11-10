## Context

`arc` is a stdlib-only CLI. Long operations are compressing, hashing and verifying in `archiver.create`, and hashing and extracting in `restore.restore`. Both currently use high-level `tarfile` calls (`tar.add`, `extractall`) that don't report progress.

## Goals / Non-Goals

**Goals:**
- Real percentages for every long phase, with no new dependencies.
- Zero change in behavior when not on a terminal (scripts, tests, CI).
- No change to archive contents or format.

**Non-Goals:**
- ETA or throughput display, colors, `--quiet`/`--progress` flags.
- Progress for `list`/`search`.

## Decisions

**A small `Progress` class in `src/arc/progress.py`** with `phase(label, total)`, `advance(n)` and `close()`. It's enabled only when `stream.isatty()`; when disabled, every method returns immediately. `human_size` moves here from `cli.py` so both can use it. Core functions take `progress: Progress | None = None`, and `None` becomes a disabled instance, so library callers and existing tests are unaffected. *Alternative:* a callback function; rejected because phases need labels and totals, which a class carries more cleanly.

**Measuring compression: add entries ourselves instead of `tar.add`.** `tar.add` opens and copies files internally, so bytes can't be observed. A ~15-line recursive walk reproduces it: `gettarinfo` → filter → `addfile` (regular files get a byte-counting reader) → recurse into directories in sorted order. Symlinks and hardlinks are stored as links, exactly as with `tar.add`. *Alternatives:* per-file progress via the existing filter (a single big file would jump 0→100%); counting compressed output (not proportional to work done).

**Pre-scan for the total.** `os.walk` (not following symlinks) plus `lstat`, summing regular-file sizes and skipping `.DS_Store`, gives the `compressing` total. The cost is one metadata pass, small next to compression. The scan runs only when progress is enabled, so non-interactive runs pay nothing.

**Verify and restore count compressed bytes.** A byte-counting wrapper sits under `zstd.ZstdFile`, so progress is measured in archive bytes against the archive size, which is known exactly. Restore switches from `tarfile.open(path, "r:zst")` to stream mode (`mode="r|"` over the counted `ZstdFile`). A spike confirmed that stream-mode `extractall` with the `tar` filter works, including absolute symlinks. The `--force` symlink-replacement filter is unchanged.

**Rendering.** `\r` + line + clear-to-end-of-line (`\x1b[K`), throttled to one redraw per 0.1 s (configurable for tests), always drawn at 100%, and a newline when a phase ends or `close()` is called. The CLI calls `close()` in its error path before printing `arc: error:`.

## Risks / Trade-offs

- [The custom walk could diverge from `tar.add`] → Existing archive tests (symlinks, `.DS_Store`, round trip) must keep passing unchanged, and a test compares member lists against `tar.add` output.
- [Files changing during archiving make the percentage drift past 100% or stop short] → The display clamps to 0–100%. Correctness is unaffected because verification uses the entry count, not bytes.
- [Stream-mode extraction can't seek] → `extractall` doesn't need to seek; the spike confirmed this.
- [Terminals without ANSI support show `\x1b[K` literally] → All macOS terminals support it; accepted.
