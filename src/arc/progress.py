"""Progress bars on stderr, drawn only when it is an interactive terminal."""

import sys
import time
from typing import BinaryIO, TextIO

BAR_WIDTH = 20
LABEL_WIDTH = 12


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


class Progress:
    """One line per phase, redrawn in place. Every method is a no-op when disabled."""

    def __init__(self, stream: TextIO | None = None, interval: float = 0.1, enabled: bool | None = None):
        self.stream = stream if stream is not None else sys.stderr
        self.enabled = self.stream.isatty() if enabled is None else enabled
        self.interval = interval
        self._label: str | None = None
        self._total: int | None = None
        self._done = 0
        self._last_draw = 0.0

    def phase(self, label: str, total: int | None = None) -> None:
        """Start a phase; total=None shows a running byte count instead of a bar."""
        if not self.enabled:
            return
        self.end()
        self._label, self._total, self._done = label, total, 0
        self._draw(force=True)

    def advance(self, n: int) -> None:
        if not self.enabled or self._label is None:
            return
        self._done += n
        self._draw()

    def end(self) -> None:
        """Finish the current phase at 100% and keep its line visible."""
        if not self.enabled or self._label is None:
            return
        if self._total is not None:
            self._done = max(self._done, self._total)
        self._draw(force=True)
        self._newline()

    def close(self) -> None:
        """Terminate a phase line as it stands (e.g. before printing an error)."""
        if not self.enabled or self._label is None:
            return
        self._newline()

    def _newline(self) -> None:
        self.stream.write("\n")
        self.stream.flush()
        self._label = None

    def _line(self) -> str:
        label = f"{self._label:<{LABEL_WIDTH}}"
        if self._total is None:
            return f"{label} {human_size(self._done)}"
        pct = 100 if self._total == 0 else min(100, self._done * 100 // self._total)
        filled = pct * BAR_WIDTH // 100
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        return f"{label} [{bar}] {pct:3d}%  {human_size(min(self._done, self._total))}/{human_size(self._total)}"

    def _draw(self, force: bool = False) -> None:
        now = time.monotonic()
        complete = self._total is not None and self._done >= self._total
        if not (force or complete) and now - self._last_draw < self.interval:
            return
        self._last_draw = now
        self.stream.write("\r" + self._line() + "\x1b[K")
        self.stream.flush()


class CountingReader:
    """Wraps a binary file and reports every read to a Progress."""

    def __init__(self, f: BinaryIO, progress: Progress):
        self._f = f
        self._progress = progress

    def read(self, size: int = -1) -> bytes:
        data = self._f.read(size)
        self._progress.advance(len(data))
        return data
