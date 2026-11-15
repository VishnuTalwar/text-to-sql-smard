"""
Validation of grader/answer_columns_heldout.yaml (D47). No API call. Messages name item ids only, never text.

Static checks (no database): the file covers exactly the held-out items that have gold SQL, the format is the
same as answer_columns.yaml, and no column is marked label_only without being a string literal of the gold SQL.
Database checks: every required column exists in the gold result, and the gold SQL graded against itself passes
30 of 30 under the strict comparator and under the answer comparator.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from answer_comparator import answer_compare, literal_label_columns, load_answer_columns
from comparator import compare
from executor import run_query_with_columns
from loader import load_questions
from _db import needs_db  # noqa: E402  (D46: skipped only when SKIP_DB_TESTS=1)

GRADER = Path(__file__).resolve().parent.parent
HELDOUT = GRADER.parent / "heldout_smard.yaml"
COLUMNS_HELDOUT = GRADER / "answer_columns_heldout.yaml"

QUESTIONS = load_questions(path=HELDOUT)
ENTRIES = load_answer_columns(COLUMNS_HELDOUT)


class TestAnswerColumnsHeldoutStatic(unittest.TestCase):
    def test_thirty_items_and_27_with_sql(self):
        self.assertEqual(len(QUESTIONS), 30)
        self.assertEqual(sum(1 for q in QUESTIONS if q.gold_sql), 27)
        self.assertEqual(sum(1 for q in QUESTIONS if q.is_tier0), 3)

    def test_exactly_the_items_with_gold_sql_have_an_entry(self):
        with_sql = {q.id for q in QUESTIONS if q.gold_sql}
        self.assertEqual(set(ENTRIES), with_sql)
        self.assertEqual(len(ENTRIES), 27)

    def test_format_is_the_same_as_the_exam_file(self):
        exam = load_answer_columns()
        exam_keys = set().union(*[set(e) for e in exam.values()])
        for qid, e in ENTRIES.items():
            with self.subTest(item=qid):
                self.assertTrue(e["required"] and all(isinstance(c, str) for c in e["required"]))
                self.assertIsInstance(e["alternatives"], list)
                self.assertFalse(set(e) - exam_keys, "a key the exam file does not use")
                self.assertEqual(len(set(e["required"])), len(e["required"]))

    def test_no_label_only_column_that_is_not_a_literal_of_the_gold_sql(self):
        for q in QUESTIONS:
            if not q.gold_sql:
                continue
            with self.subTest(item=q.id):
                allowed = set(literal_label_columns(q.gold_sql))
                self.assertLessEqual(set(ENTRIES[q.id].get("label_only") or []), allowed)

    def test_counts(self):
        """The counts reported in the step 6 prep: items with alternatives, label_only items, keyword lists."""
        self.assertEqual(sum(1 for e in ENTRIES.values() if e["alternatives"]), 0)
        self.assertEqual(sum(1 for e in ENTRIES.values() if e.get("label_only")), 0)
        self.assertEqual(sum(len(e.get("label_meanings") or {}) for e in ENTRIES.values()), 0)

    def test_the_exam_file_is_not_touched(self):
        self.assertEqual(len(load_answer_columns()), 76)  # D42: one entry per exam item with SQL


@needs_db
class TestAnswerColumnsHeldoutAgainstTheDatabase(unittest.TestCase):
    def test_every_required_column_exists_in_the_gold_result(self):
        for q in QUESTIONS:
            if not q.gold_sql:
                continue
            with self.subTest(item=q.id):
                cols, rows = run_query_with_columns(q.gold_sql)
                entry = ENTRIES[q.id]
                for name in entry["required"] + [c for alt in entry["alternatives"] for c in alt]:
                    self.assertIn(name, cols)
                    self.assertGreaterEqual(cols.index(name), 0)  # the index exists
                self.assertTrue(rows, "the gold result has no rows")

    def test_gold_graded_against_itself_passes_30_of_30_under_both_comparators(self):
        strict = answer = 0
        failed = []
        for q in QUESTIONS:
            sql = q.gold_sql  # None for tier 0: the answer is a decline
            s = compare(q, sql)
            a = answer_compare(q, sql, ENTRIES.get(q.id))
            strict += s.passed
            answer += a.passed
            if not (s.passed and a.passed):
                failed.append(q.id)
        self.assertEqual(failed, [])
        self.assertEqual((strict, answer), (30, 30))


if __name__ == "__main__":
    unittest.main(verbosity=2)
