"""
Tests for app/answer.py (D44, step 3a). No API call: the model is a fake. The SQL runs against
the real database as grader_ro, through the real safe runner.

Run from the project folder:  python -m unittest discover -s app/tests -v
Only gold_set_smard.yaml is read (never the held-out file).
"""

import contextlib
import copy
import io
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "app"))

import answer  # noqa: E402  (puts grader/ on sys.path)
import run as grader_run  # noqa: E402
from executor import run_query  # noqa: E402
from loader import GOLD_SET_PATH, load_questions  # noqa: E402

CONFIG = PROJECT_ROOT / "grader" / "configs" / "r3b_safe.yaml"
GOOD = "SELECT mwh FROM erzeugung LIMIT 5"
NO_PERIOD_EMPTY = "SELECT mwh FROM erzeugung WHERE energietraeger = 'Nonexistent'"
# no rows, but the period has data, so the system decline cannot fire
EMPTY_IN_DATA_PERIOD = ("SELECT mwh FROM erzeugung WHERE energietraeger = 'Nonexistent' "
                        "AND zeitpunkt >= '2025-01-01' AND zeitpunkt < '2025-02-01'")
WIND_JULY_2026 = ("SELECT SUM(mwh) FROM erzeugung WHERE energietraeger = 'Wind Onshore' "
                  "AND zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'")
DELETE_IN_CTE = "WITH x AS (DELETE FROM preise RETURNING *) SELECT * FROM x"
BROKEN = "SELECT mwhh FROM erzeugung LIMIT 1"


class FakeModel:
    """Returns the given replies in order; fails if the code asks for more."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(copy.deepcopy(messages))
        if len(self.calls) > len(self.replies):
            raise AssertionError("the model was called more often than expected")
        raw = self.replies[len(self.calls) - 1]
        return {"raw_model_output": raw, "prompt_tokens": 1000, "completion_tokens": 20,
                "latency_seconds": 0.5, "model": "fake-model", "system_fingerprint": "fp_fake"}


class TestAnswerQuestion(unittest.TestCase):
    def test_a_normal_answer(self):
        r = answer.answer_question("Show some wind generation values.", model_caller=FakeModel([GOOD]))
        self.assertEqual(r.status, "answered")
        self.assertEqual(r.message, "")
        self.assertEqual(len(r.attempts), 1)
        self.assertEqual((r.attempts[0].number, r.attempts[0].sql, r.attempts[0].outcome), (1, GOOD, "ok"))
        self.assertEqual(r.attempts[0].row_count, 5)
        self.assertEqual(r.row_count, 5)
        self.assertEqual(len(r.rows), 5)
        self.assertEqual(r.columns, ["mwh"])
        self.assertEqual(r.final_sql, GOOD)
        self.assertFalse(r.rewritten_after_empty)
        # numbers: 1000 in, 20 out at 2.50 / 10.00 per 1M tokens
        self.assertEqual((r.prompt_tokens, r.completion_tokens), (1000, 20))
        self.assertAlmostEqual(r.cost_usd, (1000 * 2.50 + 20 * 10.00) / 1e6, places=6)
        self.assertEqual((r.model, r.system_fingerprint), ("fake-model", "fp_fake"))
        self.assertEqual(r.seconds_model, 0.5)
        self.assertGreaterEqual(r.seconds_total, r.seconds_model)

    def test_b_model_declines(self):
        model = FakeModel(["NO_QUERY: the tables have no weather data."])
        r = answer.answer_question("What was the temperature in Berlin?", model_caller=model)
        self.assertEqual(r.status, "declined_model")
        self.assertEqual(r.message, "The model declined: the tables have no weather data.")
        self.assertEqual(len(model.calls), 1)
        self.assertEqual((r.attempts[0].sql, r.attempts[0].outcome), (None, "declined_model"))
        self.assertIsNone(r.final_sql)
        self.assertEqual((r.rows, r.row_count), ([], 0))

    def test_c_system_decline_for_a_period_without_data(self):
        model = FakeModel([WIND_JULY_2026])
        r = answer.answer_question("What was the total wind generation in July 2026?", model_caller=model)
        self.assertEqual(r.status, "declined_system")
        self.assertEqual(r.message, "No data: the tables have no rows for the period 2026-07-01 to 2026-07-31.")
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(len(r.attempts), 1)
        self.assertEqual(r.attempts[0].outcome, "declined_system")
        self.assertEqual(r.attempts[0].sql, WIND_JULY_2026)
        self.assertIsNone(r.final_sql)

    def test_d_first_query_empty_second_has_rows(self):
        model = FakeModel([NO_PERIOD_EMPTY, GOOD])
        r = answer.answer_question("Show some wind generation values.", model_caller=model)
        self.assertEqual(r.status, "answered")
        self.assertTrue(r.rewritten_after_empty)
        self.assertEqual(r.message, answer.MSG_REWRITTEN)
        self.assertEqual([a.outcome for a in r.attempts], ["empty_rows", "ok"])
        self.assertEqual([a.sql for a in r.attempts], [NO_PERIOD_EMPTY, GOOD])
        self.assertEqual(r.final_sql, GOOD)
        self.assertEqual(r.row_count, 5)
        self.assertEqual(len(model.calls), 2)

    def test_e_every_attempt_empty(self):
        model = FakeModel([EMPTY_IN_DATA_PERIOD] * 3)
        r = answer.answer_question("Show wind generation in January 2025.", model_caller=model)
        self.assertEqual(r.status, "no_rows")
        self.assertEqual(r.message, "No rows match this question.")
        self.assertEqual(len(r.attempts), 3)
        self.assertEqual([a.outcome for a in r.attempts], ["empty_rows"] * 3)
        self.assertFalse(r.rewritten_after_empty)
        self.assertEqual((r.rows, r.row_count), ([], 0))
        self.assertEqual(len(model.calls), 3)

    def test_f_delete_in_a_cte_is_blocked_and_nothing_changes(self):
        before = run_query("SELECT COUNT(*) FROM preise")
        model = FakeModel([DELETE_IN_CTE] * 3)
        r = answer.answer_question("Delete all prices.", model_caller=model)
        self.assertEqual(r.status, "blocked")
        first = r.attempts[0]
        self.assertEqual((first.outcome, first.wall), ("blocked", 1))
        self.assertIn("Delete", first.reason)
        self.assertEqual(r.message, f"The query was blocked by safety check (wall 1): {first.reason}")
        self.assertEqual(len(r.attempts), 3)
        self.assertEqual(run_query("SELECT COUNT(*) FROM preise"), before)
        self.assertGreater(before[0][0], 0)

    def test_f2_blocked_first_then_a_good_answer(self):
        r = answer.answer_question("Show some values.", model_caller=FakeModel([DELETE_IN_CTE, GOOD]))
        self.assertEqual(r.status, "answered")
        self.assertEqual([a.outcome for a in r.attempts], ["blocked", "ok"])
        self.assertEqual(r.attempts[0].wall, 1)
        self.assertFalse(r.rewritten_after_empty)

    def test_error_after_three_attempts(self):
        r = answer.answer_question("Show some values.", model_caller=FakeModel([BROKEN] * 3))
        self.assertEqual(r.status, "error")
        self.assertTrue(r.message.startswith("The query failed after 3 attempts: "))
        self.assertIn('column "mwhh" does not exist', r.message)
        self.assertEqual([a.outcome for a in r.attempts], ["error"] * 3)


# ---------------------------------------------------------------- g. equivalence with run.py

def _find_question(messages, questions):
    first = messages[0]["content"]
    for q in questions:
        if f"\n\nQuestion: {q.frage}\n\n" in first:
            return q
    raise AssertionError("no exam question found in the prompt")


class ScriptedModel:
    """Same fake replies for both paths. Reply = gold SQL, except where scripted."""

    def __init__(self, questions, script):
        self.questions, self.script, self.calls = questions, script, 0

    def __call__(self, messages):
        self.calls += 1
        q = _find_question(messages, self.questions)
        attempt = 1 + sum(1 for m in messages if m["role"] == "assistant")
        replies = self.script.get(q.id)
        raw = replies[attempt - 1] if replies else q.gold_sql.strip()
        return {"raw_model_output": raw, "prompt_tokens": 500, "completion_tokens": 30,
                "latency_seconds": 0.25, "model": "fake-model", "system_fingerprint": "fp_fake"}


class TestEquivalenceWithRunPy(unittest.TestCase):
    IDS = ["t1_01", "t2_01", "t3_01", "t4_01", "t4_02"]

    def test_g_same_attempts_and_final_sql_as_run_py(self):
        self.assertEqual(Path(GOLD_SET_PATH).name, "gold_set_smard.yaml")
        questions = load_questions()
        by_id = {q.id: q for q in questions}
        chosen = [by_id[i] for i in self.IDS]
        self.assertEqual(sorted({q.tier for q in chosen}), [1, 2, 3, 4])
        # t2_01: an SQL error first; t3_01: an empty result first (no period); the rest: gold SQL
        script = {"t2_01": [BROKEN, by_id["t2_01"].gold_sql.strip()],
                  "t3_01": [NO_PERIOD_EMPTY, by_id["t3_01"].gold_sql.strip()]}

        cfg, _ = grader_run.load_config(CONFIG)
        model_run = ScriptedModel(questions, script)
        with grader_run.prompt_builder(cfg["prompt"], cfg["examples"]) as build, \
                contextlib.redirect_stdout(io.StringIO()):
            out = grader_run.run_once(cfg, chosen, build, model_run, 0, True)
        self.assertIsNotNone(out)

        model_app = ScriptedModel(questions, script)
        for q in chosen:
            with self.subTest(question=q.id):
                loop = out["loops"][q.id]
                r = answer.answer_question(q.frage, model_caller=model_app)
                self.assertEqual(len(r.attempts), loop["n_attempts"])
                for mine, theirs in zip(r.attempts, loop["attempts"]):
                    self.assertEqual(mine.number, theirs["attempt"])
                    self.assertEqual(mine.sql, theirs["extracted_sql"])
                    self.assertEqual(mine.row_count, theirs["n_rows"])
                    self.assertEqual(mine.wall, theirs["wall"])
                    self.assertEqual(mine.outcome == "blocked", theirs["blocked"])
                    self.assertEqual(mine.outcome in ("error", "blocked"), theirs["error"] is not None)
                    self.assertEqual(mine.outcome in ("empty_rows", "empty_null"),
                                     theirs["check_fired"] in ("empty_rows", "empty_null"))
                self.assertEqual(r.final_sql, out["agent_sqls"][q.id] or None)
                self.assertEqual((r.prompt_tokens, r.completion_tokens),
                                 (loop["prompt_tokens"], loop["completion_tokens"]))
                self.assertEqual(r.cost_usd, out["records"][[x.id for x in chosen].index(q.id)]["cost_usd"])
        self.assertEqual(model_app.calls, model_run.calls, "different number of model calls")
        # the script really exercised a retry on both sides
        self.assertEqual(out["loops"]["t2_01"]["n_attempts"], 2)
        self.assertEqual(out["loops"]["t3_01"]["n_attempts"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
