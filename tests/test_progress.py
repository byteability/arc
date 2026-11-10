import io
import os
import tarfile
from datetime import UTC, datetime

from arc import archiver, restore
from arc.progress import Progress
from helpers import TempEnvCase

GB = 1024**3


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


def phase_lines(output: str) -> list[str]:
    """Final rendering of each finished phase line."""
    return [segment.split("\r")[-1].replace("\x1b[K", "") for segment in output.split("\n") if segment]


class ProgressTests(TempEnvCase):
    def test_disabled_when_not_a_tty(self):
        out = io.StringIO()
        p = Progress(stream=out, interval=0)
        self.assertFalse(p.enabled)
        p.phase("compressing", 100)
        p.advance(50)
        p.end()
        p.close()
        self.assertEqual(out.getvalue(), "")

    def test_line_format(self):
        out = FakeTTY()
        p = Progress(stream=out, interval=0)
        p.phase("compressing", int(2.3 * GB))
        p.advance(int(1.2 * GB))
        last = out.getvalue().split("\r")[-1].replace("\x1b[K", "")
        self.assertEqual(last, "compressing  [██████████░░░░░░░░░░]  52%  1.2 GB/2.3 GB")

    def test_end_shows_100_and_newline(self):
        out = FakeTTY()
        p = Progress(stream=out, interval=0)
        p.phase("checksum", 1000)
        p.advance(400)  # e.g. file shrank: end still reports completion
        p.end()
        self.assertTrue(out.getvalue().endswith("\n"))
        self.assertIn("100%", phase_lines(out.getvalue())[-1])

    def test_zero_total(self):
        out = FakeTTY()
        p = Progress(stream=out, interval=0)
        p.phase("compressing", 0)
        p.end()
        self.assertIn("100%", phase_lines(out.getvalue())[-1])

    def test_unknown_total_shows_running_size(self):
        out = FakeTTY()
        p = Progress(stream=out, interval=0)
        p.phase("scanning")
        p.advance(1536)
        p.end()
        line = phase_lines(out.getvalue())[-1]
        self.assertEqual(line.split(), ["scanning", "1.5", "KB"])

    def test_clamped_over_100(self):
        out = FakeTTY()
        p = Progress(stream=out, interval=0)
        p.phase("compressing", 100)
        p.advance(250)
        self.assertIn("100%  100 B/100 B", out.getvalue().split("\r")[-1])

    def test_close_mid_phase(self):
        out = FakeTTY()
        p = Progress(stream=out, interval=0)
        p.phase("compressing", 100)
        p.advance(30)
        p.close()
        self.assertTrue(out.getvalue().endswith("\n"))
        self.assertIn(" 30%", phase_lines(out.getvalue())[-1])
        p.close()  # idempotent
        self.assertEqual(out.getvalue().count("\n"), 1)

    def test_throttled(self):
        out = FakeTTY()
        p = Progress(stream=out, interval=60)
        p.phase("compressing", 100)
        for _ in range(50):
            p.advance(1)
        self.assertEqual(out.getvalue().count("\r"), 1)  # only the initial draw
        p.advance(50)  # reaching 100% always draws
        self.assertEqual(out.getvalue().count("\r"), 2)


class ProgressIntegrationTests(TempEnvCase):
    NOW = datetime(2026, 11, 10, 10, 15, 30, tzinfo=UTC)

    def test_add_phases_in_order(self):
        src = self.make_source()
        out = FakeTTY()
        archiver.create(src, self.config, now=self.NOW, progress=Progress(stream=out, interval=0))
        lines = phase_lines(out.getvalue())
        self.assertEqual([l.split()[0] for l in lines], ["scanning", "compressing", "checksum", "verifying"])
        for line in lines[1:]:
            self.assertIn("100%", line)
        self.assertIn("505 B/505 B", lines[1])  # a.txt (5) + sub/b.txt (500)

    def test_walk_matches_tar_add(self):
        src = self.make_source()
        (src / "empty").mkdir()
        (src / ".DS_Store").write_text("x")
        (src / "abs").symlink_to("/etc/hosts")
        (src / "rel").symlink_to("a.txt")
        os.link(src / "a.txt", src / "hard")
        rec = archiver.create(src, self.config, now=self.NOW, progress=Progress(stream=FakeTTY(), interval=0))

        reference = self.root / "ref.tar"
        with tarfile.open(reference, "w") as tar:
            tar.add(src, arcname=src.name, filter=lambda i: None if i.name.endswith(".DS_Store") else i)

        def entries(path, mode):
            with tarfile.open(path, mode) as tar:
                return [(m.name, m.type, m.linkname, m.size) for m in tar]

        self.assertEqual(entries(self.archive_dir / rec["archive_path"], "r:zst"), entries(reference, "r"))

    def test_restore_phases_in_order(self):
        src = self.make_source()
        archiver.create(src, self.config, delete=True, now=self.NOW)
        out = FakeTTY()
        restore.restore(self.config, "proj-20261110T101530Z", progress=Progress(stream=out, interval=0))
        lines = phase_lines(out.getvalue())
        self.assertEqual([l.split()[0] for l in lines], ["checksum", "extracting"])
        for line in lines:
            self.assertIn("100%", line)
        self.assertEqual((src / "sub" / "b.txt").read_text(), "world" * 100)
