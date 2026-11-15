"""The local copy of every click (app/feedback.py, D45)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "app"))

import feedback  # noqa: E402


class TestAppendFeedback(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_creates_the_folder_and_appends_one_line_per_call(self):
        path = self.dir / "app_data" / "feedback.jsonl"
        self.assertTrue(feedback.append_feedback("sess", "trace-1", "answered", "Wie viel Strom?", 1, path=path))
        self.assertTrue(feedback.append_feedback("sess", None, "no_rows", "q2", 0, path=path))
        lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(list(lines[0]), ["timestamp", "session_id", "trace_id", "status", "question", "value"])
        self.assertEqual([(x["trace_id"], x["status"], x["value"]) for x in lines],
                         [("trace-1", "answered", 1), (None, "no_rows", 0)])
        self.assertEqual(lines[0]["question"], "Wie viel Strom?")
        self.assertTrue(lines[0]["timestamp"].endswith("+00:00"))  # UTC

    def test_a_failing_write_does_not_raise(self):
        blocker = self.dir / "blocker"
        blocker.write_text("a file, not a folder")
        with self.assertLogs("app.feedback", "WARNING") as logs:
            ok = feedback.append_feedback("s", None, "answered", "q", 1, path=blocker / "feedback.jsonl")
        self.assertFalse(ok)
        self.assertEqual(len(logs.output), 1)
        with self.assertLogs("app.feedback", "WARNING"):
            self.assertFalse(feedback.append_feedback("s", None, "answered", "q", 1, path=self.dir))  # a folder

    def test_app_data_is_in_gitignore(self):
        lines = [x.strip() for x in (PROJECT_ROOT / ".gitignore").read_text().splitlines()]
        self.assertIn("app_data/", lines)

    def test_default_path_is_app_data_feedback_jsonl(self):
        self.assertEqual(feedback.FEEDBACK_PATH, PROJECT_ROOT / "app_data" / "feedback.jsonl")


if __name__ == "__main__":
    unittest.main(verbosity=2)
