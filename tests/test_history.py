import contextlib
import io
import json

from arc import history
from helpers import TempEnvCase


def add(rid, path, deleted=False):
    return {"event": "add", "id": rid, "source_path": path, "source_deleted": deleted}


class HistoryTests(TempEnvCase):
    def test_first_append_creates_file(self):
        p = history.history_path(self.archive_dir)
        self.assertFalse(p.exists())
        history.append(self.archive_dir, add("a", "/x"))
        self.assertEqual(len(p.read_text().splitlines()), 1)

    def test_line_integrity(self):
        history.append(self.archive_dir, add("a", "/x/ünï\ncode"))
        history.append(self.archive_dir, {"event": "restore", "id": "a"})
        text = history.history_path(self.archive_dir).read_text()
        self.assertTrue(text.endswith("\n"))
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            json.loads(line)

    def test_missing_history_empty(self):
        self.assertEqual(history.list_archives(self.archive_dir), [])

    def test_malformed_line_skipped_with_warning(self):
        p = history.history_path(self.archive_dir)
        p.write_text(
            json.dumps(add("a", "/a")) + "\n" + json.dumps(add("b", "/b")) + "\n{broken\n"
            + json.dumps(add("c", "/c")) + "\n"
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ids = [r["id"] for r in history.list_archives(self.archive_dir)]
        self.assertEqual(ids, ["c", "b", "a"])
        self.assertIn("line 3", err.getvalue())

    def test_delete_failed_overrides(self):
        history.append(self.archive_dir, add("a", "/a", deleted=True))
        history.append(self.archive_dir, {"event": "delete_failed", "id": "a", "error": "x"})
        (rec,) = history.list_archives(self.archive_dir)
        self.assertFalse(rec["source_deleted"])

    def test_restore_events_not_listed(self):
        history.append(self.archive_dir, add("a", "/a"))
        history.append(self.archive_dir, {"event": "restore", "id": "a"})
        self.assertEqual(len(history.list_archives(self.archive_dir)), 1)

    def test_limit(self):
        for i in range(10):
            history.append(self.archive_dir, add(f"r{i}", f"/p{i}"))
        ids = [r["id"] for r in history.list_archives(self.archive_dir, limit=3)]
        self.assertEqual(ids, ["r9", "r8", "r7"])

    def test_search_case_insensitive_on_path_and_id(self):
        history.append(self.archive_dir, add("ClientX-20261110T101530Z", "/Users/me/Work/ClientX"))
        history.append(self.archive_dir, add("other-1", "/Users/me/other"))
        self.assertEqual([r["id"] for r in history.search(self.archive_dir, "clientx")],
                         ["ClientX-20261110T101530Z"])
        self.assertEqual([r["id"] for r in history.search(self.archive_dir, "OTHER-1")], ["other-1"])
        self.assertEqual(history.search(self.archive_dir, "zzz"), [])
