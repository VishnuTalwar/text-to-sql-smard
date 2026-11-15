"""
Tests for grader/final_run.py (D47). No API call and no real held-out run: the model is a fake or is never called.
The report must hold totals and counts only; these tests check that no question text and no SQL gets into it.
Nothing here prints or asserts on held-out question text except to check that it is ABSENT from an output.
"""

import contextlib
import io
import logging
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import final_run  # noqa: E402
import run as grader_run  # noqa: E402
from loader import Question, load_questions  # noqa: E402
from _db import needs_db  # noqa: E402  (D46: skipped only when SKIP_DB_TESTS=1)

GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]


def git(cwd, *args):
    return subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def make_repo(tmp: Path, files=None) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "a.txt").write_text("one\n")
    for rel, src in (files or {}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, repo / rel)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "first")
    return repo


class TestGitChecks(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = make_repo(self.tmp)

    def test_no_tag_is_a_problem(self):
        self.assertEqual(final_run.check_tag_at_head(self.repo), ["the tag final-v1 does not exist"])

    def test_tag_at_head_is_fine(self):
        git(self.repo, "tag", "final-v1")
        self.assertEqual(final_run.check_tag_at_head(self.repo), [])

    def test_head_after_the_tag_is_a_problem(self):
        git(self.repo, "tag", "final-v1")
        (self.repo / "b.txt").write_text("two\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "second")
        self.assertEqual(final_run.check_tag_at_head(self.repo), ["HEAD is not the commit tagged final-v1"])

    def test_dirty_tracked_file_is_not_clean_but_an_untracked_file_is(self):
        self.assertEqual(final_run.check_clean(self.repo), [])
        (self.repo / "new_untracked.txt").write_text("x")
        self.assertEqual(final_run.check_clean(self.repo), [])  # untracked files only
        (self.repo / "a.txt").write_text("changed\n")
        problems = final_run.check_clean(self.repo)
        self.assertEqual(len(problems), 1)
        self.assertIn("not clean", problems[0])

    def test_not_a_repository(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assertEqual(final_run.check_clean(plain), ["not a git repository"])
        self.assertEqual(final_run.check_tag_at_head(plain), ["not a git repository"])


class TestOtherChecks(unittest.TestCase):
    def test_prediction_must_exist_and_not_be_a_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_heldout_prediction.md"
            self.assertEqual(final_run.check_prediction(path), ["final_heldout_prediction.md is missing"])
            path.write_text("**DRAFT, to be approved by Vishnu before the run**\n1. ...\n")
            self.assertEqual(len(final_run.check_prediction(path)), 1)
            path.write_text("Approved 16 Nov 2026.\n1. ...\n")
            self.assertEqual(final_run.check_prediction(path), [])

    def test_the_prediction_file_exists(self):
        self.assertTrue(final_run.PREDICTION.is_file())  # (its DRAFT mark is removed by Vishnu before the run)

    def test_existing_output_files_of_today_block_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(final_run.check_no_outputs_yet("2026-11-20", Path(tmp)), [])
            (Path(tmp) / "r3b_safe_heldout_smard_run1_2026-11-20.log").write_text("x")
            self.assertEqual(len(final_run.check_no_outputs_yet("2026-11-20", Path(tmp))), 1)
            self.assertEqual(final_run.check_no_outputs_yet("2026-11-21", Path(tmp)), [])

    def test_answer_columns_cover_the_heldout_items(self):
        self.assertEqual(final_run.check_answer_columns(), [])


class TestRefusal(unittest.TestCase):
    def test_final_run_refuses_without_the_tag_and_calls_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            repo = make_repo(tmp, {"heldout_smard.yaml": final_run.HELDOUT,
                                   "grader/answer_columns_heldout.yaml": final_run.COLUMNS_HELDOUT})
            lines = []
            with mock.patch.object(grader_run, "run_config", side_effect=AssertionError("must not run")) as rc, \
                    mock.patch.object(grader_run, "call_openai", side_effect=AssertionError("no API call")):
                code = final_run.run_final(results_dir=tmp / "results", out=lines.append, root=repo)
            self.assertEqual(code, 3)
            rc.assert_not_called()
            text = "\n".join(lines)
            self.assertIn("REFUSING", text)
            self.assertIn("HEAD is the commit tagged final-v1", text)
            self.assertIn("the tag final-v1 does not exist", text)
            self.assertIn("freeze file missing", text)
            self.assertIn("prediction approved", text)
            self.assertFalse((tmp / "results").exists())  # nothing was written

    def test_each_unmet_check_alone_refuses(self):
        for name in ("freeze check", "git working tree clean", "prediction approved"):
            checks = [("freeze check", []), ("git working tree clean", []), ("prediction approved", [])]
            checks = [(n, ["problem"] if n == name else []) for n, _ in checks]
            with mock.patch.object(grader_run, "run_config", side_effect=AssertionError("must not run")):
                self.assertEqual(final_run.run_final(checks=checks, out=lambda *_: None), 3, name)


class TestDryRun(unittest.TestCase):
    def test_builds_all_prompts_without_api_calls_and_without_question_text(self):
        seen = []

        class Catch(logging.Handler):
            def emit(self, record):
                seen.append(record.getMessage())

        handler = Catch(level=logging.DEBUG)
        logger = logging.getLogger("catalog_retriever")
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        lines = []
        checks = [("freeze check", ["freeze file missing: x"]), ("something ok", [])]
        with mock.patch.object(grader_run, "call_openai", side_effect=AssertionError("no API call")):
            code = final_run.dry_run(out=lines.append, checks=checks)
        self.assertEqual(code, 0)
        text = "\n".join(lines)
        self.assertIn("r3b_safe: 30 prompts built (all non-empty)", text)
        self.assertIn("v2b: 30 prompts built (all non-empty)", text)
        self.assertIn("[NOT MET] freeze check", text)
        self.assertIn("REFUSE to start", text)
        self.assertIn("no API call was made", text)
        for q in load_questions(path=final_run.HELDOUT):
            self.assertNotIn(q.frage, text)
            self.assertFalse([m for m in seen if q.frage in m], "a question was logged")


def fake_question(qid, tier, gold_sql="SELECT 1"):
    return Question(id=qid, tier=tier, frage="TEXT", gold_sql=gold_sql, gold_zeilen=None,
                    reihenfolge_relevant=False, toleranz=0.005)


class TestGradingAndReport(unittest.TestCase):
    def test_failure_types(self):
        ft = final_run.failure_type
        self.assertEqual(ft("agent SQL blocked (wall 1): x"), "blocked")
        self.assertEqual(ft("agent SQL error: x"), "SQL error")
        self.assertEqual(ft("declined (no SQL)"), "false decline")
        self.assertEqual(ft("tier 0: agent returned SQL when it should have declined"), "missed decline")
        self.assertEqual(ft("row count mismatch: gold=1 agent=2"), "wrong shape")
        self.assertEqual(ft("column count mismatch at row 0: gold=2 agent=1"), "wrong shape")
        self.assertEqual(ft("cell mismatch row 0 col 0: numeric mismatch"), "wrong values")
        self.assertEqual(ft("agent returned no SQL"), "other")

    def records(self):
        return [
            {"id": "q1", "tier": 1, "passed": True, "comparator_reason": "ok", "extracted_sql": "SELECT 1",
             "cost_usd": 0.01, "model": "m", "system_fingerprint": "fp1",
             "attempts": [{"blocked": False, "model": "m", "system_fingerprint": "fp1"}]},
            {"id": "q2", "tier": 3, "passed": False, "comparator_reason": "agent SQL blocked (wall 2): too costly",
             "extracted_sql": "SELECT secret_sql", "cost_usd": 0.02, "model": "m", "system_fingerprint": "fp1",
             "attempts": [{"blocked": True, "wall": 2, "model": "m", "system_fingerprint": "fp1"}]},
            {"id": "q3", "tier": 0, "passed": True, "comparator_reason": "ok (declined, as expected)",
             "extracted_sql": None, "system_declined": True, "cost_usd": 0.0, "model": "m",
             "attempts": [{"blocked": False}]},
        ]

    def test_grade_records_gives_totals_only_and_handles_blocked_and_tier0(self):
        questions = {"q1": fake_question("q1", 1), "q2": fake_question("q2", 3), "q3": fake_question("q3", 0, None)}
        entries = {"q1": {"required": ["a"], "alternatives": []}, "q2": {"required": ["a"], "alternatives": []}}
        run = lambda sql: (["a"], [(1,)])  # every query returns the same one cell
        rows = final_run.grade_records(self.records(), questions, entries, run=run)
        self.assertEqual([(r["tier"], r["strict"], r["answer"]) for r in rows],
                         [(1, True, True), (3, False, False), (0, True, True)])
        self.assertEqual(rows[1]["failure"], "blocked")
        self.assertEqual(rows[1]["blocked_walls"], [2])
        self.assertTrue(rows[2]["system_declined"])
        for r in rows:  # no text of any kind in a graded row
            self.assertFalse([v for v in r.values() if isinstance(v, str) and ("SELECT" in v or "TEXT" in v)])
            self.assertNotIn("id", r)

    def test_report_has_totals_and_counts_and_no_ids_text_or_sql(self):
        questions = {"q1": fake_question("q1", 1), "q2": fake_question("q2", 3), "q3": fake_question("q3", 0, None)}
        entries = {"q1": {"required": ["a"], "alternatives": []}, "q2": {"required": ["a"], "alternatives": []}}
        rows = final_run.grade_records(self.records(), questions, entries, run=lambda sql: (["a"], [(1,)]))
        graded = {"r3b_safe": [rows, rows, rows], "v2b": [rows, rows, rows]}
        report = final_run.build_final_report(graded, {"date": "2026-11-20", "commit": "abc1234"})
        for needle in ("## Per-run totals", "## Mean over the runs", "## Failure types", "## System decline fired",
                       "## Blocked queries per wall", "## Cost, model, fingerprints", "| r3b_safe | 1 | 2 | 2 |",
                       "| r3b_safe, strict |", "| r3b_safe | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 |", "| r3b_safe | 0 | 3 | 0 | 3 |",
                       "fp1", "Total cost: $0.1800", "Same day: yes"):
            self.assertIn(needle, report)
        for forbidden in ("q1", "q2", "q3", "SELECT", "secret_sql", "TEXT", "heldout"):
            self.assertNotIn(forbidden, report)

    def test_report_says_when_the_runs_crossed_midnight(self):
        rows = [{"tier": 1, "strict": True, "answer": True, "failure": None, "system_declined": False,
                 "blocked_walls": [], "cost_usd": 0.0, "models": ["m"], "fingerprints": []}]
        report = final_run.build_final_report({"v2b": [rows]}, {"date": "d", "same_day": False})
        self.assertIn("NO: the runs crossed midnight", report)


@needs_db
class TestEndToEndWithAFakeModel(unittest.TestCase):
    """The real pipeline (run.py path, grading, report) with a fake model that answers with the gold SQL."""

    def test_full_run_with_a_fake_model_writes_a_clean_report(self):
        questions = load_questions(path=final_run.HELDOUT)

        def fake_llm(messages):
            first = messages[0]["content"]
            q = next(q for q in questions if f"\n\nQuestion: {q.frage}\n\n" in first)
            reply = q.gold_sql.strip() if q.gold_sql else "NO_QUERY: not in the data"
            return {"raw_model_output": reply, "prompt_tokens": 100, "completion_tokens": 10,
                    "latency_seconds": 0.0, "model": "fake-model", "system_fingerprint": "fp_fake"}

        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            tmp = Path(tmp)
            code = final_run.run_final(results_dir=tmp, llm=fake_llm, checks=[], out=lambda *_: None)
            self.assertEqual(code, 0)
            reports = list(tmp.glob("final_heldout_*.md"))
            self.assertEqual(len(reports), 1)
            report = reports[0].read_text(encoding="utf-8")
            # 6 run files (3 per setup), each with a manifest
            self.assertEqual(len(list(tmp.glob("*_run?_*.jsonl"))), 6)
            self.assertEqual(len(list(tmp.glob("*.manifest.json"))), 6)
        self.assertIn("| r3b_safe | 1 | 30 | 30 |", report)
        self.assertIn("| v2b | 3 | 30 | 30 |", report)
        self.assertIn("fp_fake", report)
        for q in questions:
            self.assertNotIn(q.frage, report)
            if q.gold_sql:
                self.assertNotIn(q.gold_sql.strip(), report)
            self.assertNotIn(q.id, report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
