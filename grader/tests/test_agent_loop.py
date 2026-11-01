"""
Offline tests for grader/agent_loop.py and grader/run_r1.py. No OpenAI call is made:
the model is a fake. The SQL checks use the real read-only database (grader_ro).

Run from the grader folder:  python -m unittest discover -s tests -v
"""

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent_loop
import prompt_template_v2b
from executor import QueryError, run_query
from loader import load_questions

BROKEN_HINT = "SELECT mwhh FROM erzeugung LIMIT 1"            # error with a HINT
BROKEN_NO_HINT = "SELECT zero_stretch FROM erzeugung LIMIT 1"  # error without a HINT
WORKING = "SELECT mwh FROM erzeugung LIMIT 1"

ERR_HINT = ('column "mwhh" does not exist\n'
            'HINT: Perhaps you meant to reference the column "erzeugung.mwh".')
ERR_NO_HINT = 'column "zero_stretch" does not exist'


class FakeModel:
    """Returns the given replies in order and records the messages of every call."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(copy.deepcopy(messages))
        if len(self.calls) > len(self.replies):
            raise AssertionError("the loop called the model more often than expected")
        return {"raw_model_output": self.replies[len(self.calls) - 1],
                "prompt_tokens": 100, "completion_tokens": 10, "latency_seconds": 0.5}


def retry_text(error: str) -> str:
    return ("This query failed with the following error from PostgreSQL:\n"
            f"{error}\n"
            "Write a corrected query. Return only the SQL.")


class TestPromptAndSettings(unittest.TestCase):
    def test_attempt_1_prompt_identical_to_v2b_for_all_84(self):
        questions = load_questions()
        identical = 0
        for q in questions:
            model = FakeModel(["NO_QUERY: test"])
            agent_loop.run_question(q.frage, llm=model)
            sent = model.calls[0]
            if (len(sent) == 1 and sent[0]["role"] == "user"
                    and sent[0]["content"] == prompt_template_v2b.build_prompt(q.frage)):
                identical += 1
        print(f"\n{identical}/{len(questions)} identical")
        self.assertEqual(identical, len(questions))
        self.assertEqual(len(questions), 84)

    def test_openai_call_settings(self):
        seen = {}

        def create(**kwargs):
            seen.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="SELECT 1"))],
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2))

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        out = agent_loop.call_openai([{"role": "user", "content": "x"}], client=client)
        self.assertEqual(seen["model"], "gpt-4o")
        self.assertEqual(seen["temperature"], 0)
        self.assertEqual(seen["seed"], 0)
        self.assertEqual(seen["messages"], [{"role": "user", "content": "x"}])
        self.assertEqual((out["prompt_tokens"], out["completion_tokens"]), (5, 2))

    def test_decline_detection_matches_run_v2b(self):
        import run_v2b
        for s in ["NO_QUERY: x", "no_query: x", "  No_Query", "SELECT 1", "", "-- NO_QUERY"]:
            self.assertEqual(agent_loop.is_decline(s), run_v2b.is_decline(s), s)

    def test_fenced_sql_is_stripped_like_v2b(self):
        model = FakeModel(["```sql\nSELECT 1\n```"])
        rec = agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "p")
        self.assertEqual(rec["final_sql"], "SELECT 1")
        self.assertEqual(rec["n_attempts"], 1)

    def test_role_statement_timeout_is_30s(self):
        self.assertEqual(run_query("SHOW statement_timeout"), [("30s",)])


class TestSwitches(unittest.TestCase):
    def test_unimplemented_switches_raise(self):
        for name in ("empty_retry", "decline_review"):
            with self.assertRaises(NotImplementedError):
                agent_loop.run_question("q", {name: True}, llm=FakeModel(["SELECT 1"]))

    def test_unknown_switch_raises(self):
        with self.assertRaises(ValueError):
            agent_loop.run_question("q", {"nope": True}, llm=FakeModel(["SELECT 1"]))

    def test_error_retry_off_is_a_single_attempt_without_execution(self):
        def never(_sql):
            raise AssertionError("SQL must not be executed when error_retry is off")
        model = FakeModel([BROKEN_HINT])
        rec = agent_loop.run_question("q", {"error_retry": False}, llm=model, execute=never,
                                      prompt_builder=lambda q: "p")
        self.assertEqual(rec["n_attempts"], 1)
        self.assertFalse(rec["retried"])
        self.assertEqual(rec["final_sql"], BROKEN_HINT)


class TestLoopBehaviour(unittest.TestCase):
    def test_working_sql_stops_at_attempt_1(self):
        model = FakeModel([WORKING])
        rec = agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "p")
        self.assertEqual(len(model.calls), 1)
        self.assertFalse(rec["retried"])
        self.assertFalse(rec["crashed_on_attempt_1"])
        self.assertEqual(rec["final_sql"], WORKING)

    def test_decline_on_attempt_1_stops(self):
        model = FakeModel(["NO_QUERY: nothing here"])
        rec = agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "p")
        self.assertEqual(len(model.calls), 1)
        self.assertTrue(rec["declined"])
        self.assertIsNone(rec["final_sql"])
        self.assertFalse(rec["declined_after_error"])

    def test_b_broken_then_working(self):
        model = FakeModel([BROKEN_HINT, WORKING])
        rec = agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "PROMPT")
        self.assertEqual(rec["n_attempts"], 2)
        self.assertEqual(len(model.calls), 2)
        self.assertTrue(rec["retried"])
        self.assertTrue(rec["crashed_on_attempt_1"])
        self.assertFalse(rec["cap_hit"])
        self.assertFalse(rec["declined_after_error"])
        self.assertEqual(rec["final_sql"], WORKING)
        # same conversation: prompt, the model's reply, then exactly the retry text
        self.assertEqual(model.calls[1], [
            {"role": "user", "content": "PROMPT"},
            {"role": "assistant", "content": BROKEN_HINT},
            {"role": "user", "content": retry_text(ERR_HINT)},
        ])
        print("\nretry message sent to the model:\n" + model.calls[1][2]["content"])
        self.assertEqual(rec["attempts"][0]["error"], ERR_HINT)
        self.assertIsNone(rec["attempts"][1]["error"])
        self.assertEqual(rec["prompt_tokens"], 200)
        self.assertEqual(rec["completion_tokens"], 20)

    def test_error_without_hint_has_no_hint_line_and_no_context(self):
        model = FakeModel([BROKEN_NO_HINT, WORKING])
        agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "p")
        text = model.calls[1][2]["content"]
        self.assertEqual(text, retry_text(ERR_NO_HINT))
        for forbidden in ("HINT", "LINE 1", "Traceback", "^"):
            self.assertNotIn(forbidden, text)

    def test_c_three_failures_stop_at_cap(self):
        model = FakeModel([BROKEN_HINT, BROKEN_NO_HINT, BROKEN_HINT, WORKING])
        rec = agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "p")
        self.assertEqual(len(model.calls), 3)  # the 4th reply is never requested
        self.assertEqual(rec["n_attempts"], 3)
        self.assertTrue(rec["cap_hit"])
        self.assertFalse(rec["declined"])
        self.assertIsNotNone(rec["attempts"][-1]["error"])
        self.assertEqual(rec["final_sql"], BROKEN_HINT)  # the final attempt is the answer
        self.assertFalse(rec["declined_after_error"])

    def test_d_broken_then_no_query(self):
        model = FakeModel([BROKEN_HINT, "NO_QUERY: the data is missing", WORKING])
        rec = agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "p")
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(rec["n_attempts"], 2)
        self.assertTrue(rec["declined"])
        self.assertTrue(rec["declined_after_error"])
        self.assertFalse(rec["cap_hit"])
        self.assertIsNone(rec["final_sql"])
        self.assertEqual(rec["final_reply"], "NO_QUERY: the data is missing")


class TestReadOnlyRole(unittest.TestCase):
    TABLE = "zz_agent_loop_must_not_exist"

    def test_e_write_statements_are_refused(self):
        statements = [
            f"CREATE TABLE {self.TABLE} (a int)",
            "DELETE FROM erzeugung WHERE false",
            "UPDATE erzeugung SET mwh = mwh WHERE false",
            "INSERT INTO erzeugung SELECT * FROM erzeugung WHERE false",
            "DROP TABLE erzeugung",
        ]
        before = run_query("SELECT COUNT(*) FROM erzeugung")
        for sql in statements:
            with self.assertRaises(QueryError, msg=sql) as ctx:
                run_query(sql)
            # PostgreSQL words the refusal by statement: "permission denied ..." or,
            # for DROP, "must be owner of table ..."
            msg = str(ctx.exception)
            self.assertTrue("permission denied" in msg or "must be owner" in msg, f"{sql}: {msg}")
        self.assertEqual(run_query(f"SELECT to_regclass('public.{self.TABLE}')"), [(None,)])
        self.assertEqual(run_query("SELECT COUNT(*) FROM erzeugung"), before)

    def test_e_write_through_the_loop_comes_back_as_an_error(self):
        model = FakeModel([f"CREATE TABLE {self.TABLE} (a int)", WORKING])
        rec = agent_loop.run_question("q", llm=model, prompt_builder=lambda q: "p")
        self.assertEqual(rec["attempts"][0]["error"], "permission denied for schema public")
        self.assertEqual(model.calls[1][2]["content"], retry_text("permission denied for schema public"))
        self.assertEqual(run_query(f"SELECT to_regclass('public.{self.TABLE}')"), [(None,)])


class TestRunnerSmoke(unittest.TestCase):
    """run_r1.run() end to end with a fake model that answers with the gold SQL
    (and NO_QUERY for tier 0), except that t1_01 first sends broken SQL."""

    def test_full_pipeline_with_fake_model(self):
        import json
        import run_r1

        gold = {q.frage: q for q in load_questions()}
        t101 = next(q for q in gold.values() if q.id == "t1_01")
        state = {"t1_01_calls": 0}

        def fake_llm(messages):
            content = messages[0]["content"]
            frage = content.split("Question: ", 1)[1].split("\n\n", 1)[0]
            q = gold[frage]
            if q.id == "t1_01" and state["t1_01_calls"] == 0:
                state["t1_01_calls"] += 1
                reply = BROKEN_HINT
            elif q.is_tier0:
                reply = "NO_QUERY: not in the data"
            else:
                reply = q.gold_sql
            return {"raw_model_output": reply, "prompt_tokens": 1000, "completion_tokens": 50,
                    "latency_seconds": 0.1}

        with tempfile.TemporaryDirectory() as tmp:
            code = run_r1.run(tag="smoke", llm=fake_llm, results_dir=Path(tmp))
            self.assertEqual(code, 0)  # 84/84
            jsonls = list(Path(tmp).glob("r1_smoke_*.jsonl"))
            logs = list(Path(tmp).glob("r1_smoke_*.log"))
            self.assertEqual((len(jsonls), len(logs)), (1, 1))
            recs = [json.loads(l) for l in open(jsonls[0])]
            self.assertEqual(len(recs), 84)
            self.assertTrue(all(r["passed"] for r in recs))
            first = next(r for r in recs if r["id"] == t101.id)
            self.assertEqual(first["n_attempts"], 2)
            self.assertTrue(first["crashed_on_attempt_1"])
            self.assertEqual(len(first["attempts"]), 2)
            self.assertEqual(sum(r["n_attempts"] for r in recs), 85)
            self.assertIn("Retry rate", logs[0].read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
