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
        self.assertEqual(seen["model"], "gpt-4o-2024-08-06")  # pinned snapshot (D36)
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
    def test_decline_review_switch_is_implemented(self):
        rec = agent_loop.run_question("q", {"decline_review": True}, llm=FakeModel(["SELECT 1"]),
                                      prompt_builder=lambda q: "p")
        self.assertEqual(rec["n_attempts"], 1)
        self.assertFalse(rec["review_fired"])

    def test_empty_retry_switch_is_implemented(self):
        rec = agent_loop.run_question("q", {"empty_retry": True}, llm=FakeModel(["SELECT 1"]),
                                      prompt_builder=lambda q: "p")
        self.assertEqual(rec["n_attempts"], 1)

    def test_model_is_pinned_to_the_dated_snapshot(self):
        import naive_agent
        self.assertEqual(naive_agent.MODEL, "gpt-4o-2024-08-06")
        self.assertIs(agent_loop.MODEL, naive_agent.MODEL)

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


class TestEmptyRetry(unittest.TestCase):
    """Row R2: empty_retry. Real read-only database, fake model."""
    BOTH = {"error_retry": True, "empty_retry": True}
    ZERO_ROWS = "SELECT mwh FROM erzeugung WHERE false"
    ONE_NULL = "SELECT NULL::numeric"
    ONE_ZERO = "SELECT 0"
    WITH_ROWS = "SELECT mwh FROM erzeugung LIMIT 2"
    NO_ROWS_TEXT = ("This query ran but returned no rows.\n"
                    "Write a corrected query. Return only the SQL.")
    ONLY_NULL_TEXT = ("This query ran but returned only NULL values.\n"
                      "Write a corrected query. Return only the SQL.")

    def run_q(self, replies, switches="both"):
        model = FakeModel(replies)
        sw = self.BOTH if switches == "both" else switches
        rec = agent_loop.run_question("q", sw, llm=model, prompt_builder=lambda q: "PROMPT")
        return model, rec

    def test_a_zero_rows_then_rows(self):
        model, rec = self.run_q([self.ZERO_ROWS, self.WITH_ROWS])
        self.assertEqual(rec["n_attempts"], 2)
        self.assertEqual(model.calls[1], [
            {"role": "user", "content": "PROMPT"},
            {"role": "assistant", "content": self.ZERO_ROWS},
            {"role": "user", "content": self.NO_ROWS_TEXT},
        ])
        self.assertEqual(rec["final_sql"], self.WITH_ROWS)
        self.assertEqual([a["check_fired"] for a in rec["attempts"]], ["empty_rows", None])
        self.assertTrue(rec["empty_on_attempt1"])
        self.assertTrue(rec["retried_after_empty"])
        self.assertFalse(rec["declined_after_empty"])
        self.assertFalse(rec["ended_empty"])

    def test_b_only_null_then_no_query(self):
        model, rec = self.run_q([self.ONE_NULL, "NO_QUERY: no data for that period", self.WITH_ROWS])
        self.assertEqual(len(model.calls), 2)  # NO_QUERY stops the loop
        self.assertEqual(model.calls[1][2]["content"], self.ONLY_NULL_TEXT)
        self.assertEqual(rec["attempts"][0]["check_fired"], "empty_null")
        self.assertTrue(rec["declined"])
        self.assertTrue(rec["declined_after_empty"])
        self.assertFalse(rec["declined_after_error"])
        self.assertIsNone(rec["final_sql"])

    def test_c_a_single_zero_is_not_empty(self):
        model, rec = self.run_q([self.ONE_ZERO])
        self.assertEqual(len(model.calls), 1)
        self.assertFalse(rec["retried"])
        self.assertIsNone(rec["attempts"][0]["check_fired"])
        self.assertFalse(rec["empty_on_attempt1"])
        self.assertEqual(rec["final_sql"], self.ONE_ZERO)

    def test_d_error_then_empty_then_rows(self):
        model, rec = self.run_q([BROKEN_HINT, self.ZERO_ROWS, self.WITH_ROWS, "SELECT 99"])
        self.assertEqual(len(model.calls), 3)  # stops at 3 attempts in total
        self.assertEqual(rec["n_attempts"], 3)
        # one conversation, in order: prompt, broken SQL, error text, empty SQL, "no rows" text
        self.assertEqual(model.calls[1][2]["content"], retry_text(ERR_HINT))
        self.assertEqual(model.calls[2], [
            {"role": "user", "content": "PROMPT"},
            {"role": "assistant", "content": BROKEN_HINT},
            {"role": "user", "content": retry_text(ERR_HINT)},
            {"role": "assistant", "content": self.ZERO_ROWS},
            {"role": "user", "content": self.NO_ROWS_TEXT},
        ])
        self.assertEqual([a["check_fired"] for a in rec["attempts"]], ["error", "empty_rows", None])
        self.assertEqual(rec["final_sql"], self.WITH_ROWS)
        self.assertTrue(rec["crashed_on_attempt_1"])
        self.assertFalse(rec["empty_on_attempt1"])
        self.assertTrue(rec["retried_after_error"])
        self.assertTrue(rec["retried_after_empty"])
        self.assertFalse(rec["cap_hit"])

    def test_last_attempt_still_empty_is_the_answer(self):
        model, rec = self.run_q([self.ZERO_ROWS, self.ONE_NULL, self.ZERO_ROWS, self.WITH_ROWS])
        self.assertEqual(len(model.calls), 3)
        self.assertEqual(rec["final_sql"], self.ZERO_ROWS)
        self.assertTrue(rec["ended_empty"])
        self.assertTrue(rec["cap_hit"])
        self.assertEqual([a["check_fired"] for a in rec["attempts"]], ["empty_rows", "empty_null", "empty_rows"])

    def test_e_empty_retry_off_returns_the_empty_result_after_one_attempt(self):
        for switches in ({"error_retry": True, "empty_retry": False}, {}):  # {} = the default switches
            model, rec = self.run_q([self.ZERO_ROWS, self.WITH_ROWS], switches)
            self.assertEqual(len(model.calls), 1)
            self.assertEqual(rec["n_attempts"], 1)
            self.assertEqual(rec["final_sql"], self.ZERO_ROWS)
            self.assertIsNone(rec["attempts"][0]["check_fired"])
            self.assertFalse(rec["empty_on_attempt1"])

    def test_empty_kind_helper(self):
        self.assertEqual(agent_loop.empty_kind([]), "empty_rows")
        self.assertEqual(agent_loop.empty_kind([(None,), (None,)]), "empty_null")
        self.assertEqual(agent_loop.empty_kind([(None, None)]), "empty_null")
        self.assertIsNone(agent_loop.empty_kind([(0,)]))
        self.assertIsNone(agent_loop.empty_kind([(None, 0)]))
        self.assertIsNone(agent_loop.empty_kind([("",)]))
        self.assertIsNone(agent_loop.empty_kind(None))

    def test_f_attempt_1_prompt_identical_to_v2b_for_all_84_with_r2_switches(self):
        questions = load_questions()
        identical = 0
        for q in questions:
            model = FakeModel(["NO_QUERY: test"])
            agent_loop.run_question(q.frage, self.BOTH, llm=model)
            sent = model.calls[0]
            if (len(sent) == 1 and sent[0]["role"] == "user"
                    and sent[0]["content"] == prompt_template_v2b.build_prompt(q.frage)):
                identical += 1
        print(f"\nR2 switches: {identical}/{len(questions)} attempt-1 prompts identical to v2b")
        self.assertEqual(identical, len(questions))

    def test_run_r2_pipeline_with_fake_model(self):
        """run_r2.run() end to end: u_08 first answers with SQL that returns one NULL,
        then declines after the empty retry; t4_03 first returns no rows."""
        import json
        import run_r2

        gold = {q.frage: q for q in load_questions()}
        u08_sql = ("SELECT SUM(mwh) FROM erzeugung WHERE energietraeger IN ('Wind Onshore','Wind Offshore') "
                   "AND zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'")

        def fake_llm(messages):
            frage = messages[0]["content"].split("Question: ", 1)[1].split("\n\n", 1)[0]
            q = gold[frage]
            if q.id == "u_08":
                reply = u08_sql if len(messages) == 1 else "NO_QUERY: no data for July 2026"
            elif q.id == "t4_03" and len(messages) == 1:
                reply = self.ZERO_ROWS
            elif q.is_tier0:
                reply = "NO_QUERY: not in the data"
            else:
                reply = q.gold_sql
            return {"raw_model_output": reply, "prompt_tokens": 1000, "completion_tokens": 50,
                    "latency_seconds": 0.1, "model": "gpt-4o-2024-08-06", "system_fingerprint": "fp_test"}

        with tempfile.TemporaryDirectory() as tmp:
            code = run_r2.run(tag="smoke", llm=fake_llm, results_dir=Path(tmp))
            self.assertEqual(code, 0)  # 84/84
            logs = list(Path(tmp).glob("r2_smoke_*.log")); jsonls = list(Path(tmp).glob("r2_smoke_*.jsonl"))
            self.assertEqual((len(logs), len(jsonls)), (1, 1))
            recs = {r["id"]: r for r in map(json.loads, open(jsonls[0]))}
            self.assertEqual(len(recs), 84)
            self.assertTrue(recs["u_08"]["declined_after_empty"])
            self.assertTrue(recs["u_08"]["empty_on_attempt1"])
            self.assertEqual(recs["u_08"]["n_attempts"], 2)
            self.assertTrue(recs["t4_03"]["retried_after_empty"])
            self.assertTrue(recs["t4_03"]["fixed_after_empty"])  # gold SQL on attempt 2 passes
            report = logs[0].read_text()
            for needle in ("Empty on attempt 1", "u_08 (July 2026)", "declined after", "Share with an empty-result retry"):
                self.assertIn(needle.lower(), report.lower())


class TestDeclineReview(unittest.TestCase):
    """Row R3: decline review and empty fact (date_facts.py). Real read-only database, fake model."""
    R3 = {"error_retry": True, "empty_retry": True, "decline_review": True}
    R2 = {"error_retry": True, "empty_retry": True, "decline_review": False}
    WITH_ROWS = "SELECT mwh FROM erzeugung LIMIT 2"
    JULY_2026 = ("SELECT SUM(mwh) FROM erzeugung "
                 "WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'")
    EMPTY_NO_DATE = ("SELECT e.zeitpunkt FROM erzeugung e JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt "
                     "WHERE e.mwh < -1000000")
    FALSE_CLAIM = "NO_QUERY: The table does not contain data for February 2026."

    def run_q(self, replies, switches=None):
        model = FakeModel(replies)
        rec = agent_loop.run_question("q", self.R3 if switches is None else switches, llm=model,
                                      prompt_builder=lambda q: "PROMPT")
        return model, rec

    def test_a_false_date_claim_is_reviewed_once(self):
        model, rec = self.run_q([self.FALSE_CLAIM, self.WITH_ROWS])
        want = ('Your reason was: "The table does not contain data for February 2026."\n'
                "Fact: the tables have rows for the period 2026-02-01 to 2026-02-28.\n"
                "Reply again following the original instructions.")
        self.assertEqual(model.calls[1], [
            {"role": "user", "content": "PROMPT"},
            {"role": "assistant", "content": self.FALSE_CLAIM},
            {"role": "user", "content": want},
        ])
        print("\nREVIEW MESSAGE (test a):\n" + want)
        self.assertEqual(rec["n_attempts"], 2)
        self.assertEqual(rec["final_sql"], self.WITH_ROWS)
        self.assertEqual([a["check_fired"] for a in rec["attempts"]], ["review", None])
        self.assertTrue(rec["review_fired"])
        self.assertTrue(rec["answered_after_review"])
        self.assertFalse(rec["declined_after_review"])
        self.assertEqual((rec["review_periods"][0]["start"], rec["review_periods"][0]["end"]), ("2026-02-01", "2026-02-28"))
        self.assertGreater(sum(rec["review_periods"][0]["rows"].values()), 0)

    def test_b_true_claim_is_not_reviewed(self):
        model, rec = self.run_q(["NO_QUERY: Data for July 2026 is missing.", self.WITH_ROWS])
        self.assertEqual(len(model.calls), 1)
        self.assertTrue(rec["declined"])
        self.assertFalse(rec["review_fired"])

    def test_c_open_ended_claim_is_not_reviewed(self):
        model, rec = self.run_q(["NO_QUERY: There is no data for nuclear power after 2024-01-30.", self.WITH_ROWS])
        self.assertEqual(len(model.calls), 1)
        self.assertTrue(rec["declined"])
        self.assertFalse(rec["review_fired"])

    def test_d_second_decline_stands_after_one_review(self):
        claim = "NO_QUERY: Data for 2025 is missing."
        model, rec = self.run_q([claim, claim, self.WITH_ROWS])
        self.assertEqual(len(model.calls), 2)  # exactly one review, no second one
        self.assertEqual(model.calls[1][2]["content"],
                         'Your reason was: "Data for 2025 is missing."\n'
                         "Fact: the tables have rows for the period 2025-01-01 to 2025-12-31.\n"
                         "Reply again following the original instructions.")
        self.assertTrue(rec["declined"])
        self.assertTrue(rec["review_fired"])
        self.assertTrue(rec["declined_after_review"])
        self.assertFalse(rec["answered_after_review"])
        self.assertIsNone(rec["final_sql"])

    def test_e_no_review_when_the_cap_is_reached(self):
        model, rec = self.run_q([BROKEN_HINT, BROKEN_NO_HINT, self.FALSE_CLAIM, self.WITH_ROWS])
        self.assertEqual(len(model.calls), 3)
        self.assertEqual(rec["n_attempts"], 3)
        self.assertTrue(rec["declined"])
        self.assertFalse(rec["review_fired"])
        self.assertEqual([a["check_fired"] for a in rec["attempts"]], ["error", "error", None])

    def test_review_is_possible_on_attempt_2_and_leaves_room_for_attempt_3(self):
        model, rec = self.run_q([BROKEN_HINT, self.FALSE_CLAIM, BROKEN_NO_HINT, self.WITH_ROWS])
        self.assertEqual([a["check_fired"] for a in rec["attempts"]], ["error", "review", "error"])
        self.assertEqual(len(model.calls), 3)
        self.assertTrue(rec["cap_hit"])

    def test_f_empty_fact_for_a_period_without_rows(self):
        model, rec = self.run_q([self.JULY_2026, "NO_QUERY: Data for July 2026 is missing."])
        want = ("This query ran but returned only NULL values.\n"
                "Fact: the tables have no rows for the period 2026-07-01 to 2026-07-31.\n"
                "Write a corrected query. Return only the SQL.")
        self.assertEqual(model.calls[1], [
            {"role": "user", "content": "PROMPT"},
            {"role": "assistant", "content": self.JULY_2026},
            {"role": "user", "content": want},
        ])
        print("\nEMPTY-FACT MESSAGE (test f):\n" + want)
        self.assertTrue(rec["empty_fact_fired"])
        self.assertEqual((rec["empty_fact_period"][0]["start"], rec["empty_fact_period"][0]["end"]), ("2026-07-01", "2026-07-31"))
        self.assertTrue(rec["declined"])
        self.assertTrue(rec["declined_after_empty"])
        self.assertFalse(rec["review_fired"])  # a decline after the empty fact is not reviewed (claim is true)

    def test_g_no_fact_without_a_date_in_the_sql(self):
        model, rec = self.run_q([self.EMPTY_NO_DATE, self.WITH_ROWS])
        self.assertEqual(model.calls[1][2]["content"],
                         "This query ran but returned no rows.\nWrite a corrected query. Return only the SQL.")
        self.assertNotIn("Fact", model.calls[1][2]["content"])
        self.assertFalse(rec["empty_fact_fired"])
        self.assertEqual(rec["empty_fact_period"], [])

    def test_h_decline_review_off_behaves_like_r2(self):
        for replies in ([self.FALSE_CLAIM, self.WITH_ROWS], [self.JULY_2026, "NO_QUERY: x", self.WITH_ROWS],
                        [self.EMPTY_NO_DATE, self.WITH_ROWS], [BROKEN_HINT, self.WITH_ROWS]):
            m_off, r_off = self.run_q(replies, dict(self.R2))
            m_default, r_default = self.run_q(replies, {"error_retry": True, "empty_retry": True})
            self.assertEqual(m_off.calls, m_default.calls)
            for key in ("final_sql", "n_attempts", "declined", "retried", "review_fired", "empty_fact_fired"):
                self.assertEqual(r_off[key], r_default[key], key)
        # no review and no fact line with the switch off
        m, r = self.run_q([self.FALSE_CLAIM, self.WITH_ROWS], dict(self.R2))
        self.assertEqual(len(m.calls), 1)
        self.assertFalse(r["review_fired"])
        m, r = self.run_q([self.JULY_2026, "NO_QUERY: x"], dict(self.R2))
        self.assertEqual(m.calls[1][2]["content"],
                         "This query ran but returned only NULL values.\nWrite a corrected query. Return only the SQL.")
        self.assertFalse(r["empty_fact_fired"])

    def test_i_attempt_1_prompt_identical_to_v2b_for_all_84_with_r3_switches(self):
        questions = load_questions()
        identical = 0
        for q in questions:
            model = FakeModel(["NO_QUERY: test"])
            agent_loop.run_question(q.frage, self.R3, llm=model)
            sent = model.calls[0]
            if (len(sent) == 1 and sent[0]["role"] == "user"
                    and sent[0]["content"] == prompt_template_v2b.build_prompt(q.frage)):
                identical += 1
        print(f"\nR3 switches: {identical}/{len(questions)} attempt-1 prompts identical to v2b")
        self.assertEqual(identical, len(questions))

    def test_run_r3_pipeline_with_fake_model(self):
        """run_r3.run() end to end. t1_12 is first declined with a false date claim and then
        answered; u_01 declines with open-ended wording (no review); u_08 gets the empty fact
        and then declines."""
        import json
        import run_r3

        gold = {q.frage: q for q in load_questions()}

        def fake_llm(messages):
            frage = messages[0]["content"].split("Question: ", 1)[1].split("\n\n", 1)[0]
            q = gold[frage]
            if q.id == "t1_12":
                reply = "NO_QUERY: Data for February 2026 is not available." if len(messages) == 1 else q.gold_sql
            elif q.id == "u_08":
                reply = self.JULY_2026 if len(messages) == 1 else "NO_QUERY: Data for July 2026 is missing."
            elif q.id == "u_01":
                reply = "NO_QUERY: Nuclear power data is missing after January 2024."
            elif q.is_tier0:
                reply = "NO_QUERY: not in the data"
            else:
                reply = q.gold_sql
            return {"raw_model_output": reply, "prompt_tokens": 1000, "completion_tokens": 50,
                    "latency_seconds": 0.1, "model": "gpt-4o-2024-08-06", "system_fingerprint": "fp_test"}

        with tempfile.TemporaryDirectory() as tmp:
            code = run_r3.run(tag="smoke", llm=fake_llm, results_dir=Path(tmp))
            self.assertEqual(code, 0)  # 84/84
            logs = list(Path(tmp).glob("r3_smoke_*.log")); jsonls = list(Path(tmp).glob("r3_smoke_*.jsonl"))
            self.assertEqual((len(logs), len(jsonls)), (1, 1))
            recs = {r["id"]: r for r in map(json.loads, open(jsonls[0]))}
            self.assertTrue(recs["t1_12"]["review_fired"])
            self.assertTrue(recs["t1_12"]["answered_after_review"])
            self.assertFalse(recs["u_01"]["review_fired"])
            self.assertEqual(recs["u_01"]["n_attempts"], 1)
            self.assertTrue(recs["u_08"]["empty_fact_fired"])
            self.assertTrue(recs["u_08"]["declined_after_empty"])
            self.assertEqual(sum(r["review_fired"] for r in recs.values()), 1)
            report = logs[0].read_text().lower()
            for needle in ("decline reviews fired", "empty facts fired", "u_01 (nuclear", "u_08 after which message",
                           "declined after the empty_null message with the database fact"):
                self.assertIn(needle, report)


class TestEmptyFactDecline(unittest.TestCase):
    """Row R3b: empty_fact_decline. Real read-only database, fake model."""
    R3B = {"error_retry": True, "empty_retry": True, "decline_review": True, "empty_fact_decline": True}
    R3 = {"error_retry": True, "empty_retry": True, "decline_review": True}
    JULY_2026 = TestDeclineReview.JULY_2026
    WITH_ROWS = "SELECT mwh FROM erzeugung LIMIT 2"
    EMPTY_FEB = ("SELECT mwh FROM erzeugung WHERE zeitpunkt >= '2026-02-01' AND zeitpunkt < '2026-03-01' "
                 "AND mwh < -1000000")
    EMPTY_NO_DATE = TestDeclineReview.EMPTY_NO_DATE
    REASON = "No data: the tables have no rows for the period 2026-07-01 to 2026-07-31."

    def run_q(self, replies, switches=None):
        model = FakeModel(replies)
        rec = agent_loop.run_question("q", self.R3B if switches is None else switches, llm=model,
                                      prompt_builder=lambda q: "PROMPT")
        return model, rec

    def test_a_proven_empty_period_stops_with_a_system_decline(self):
        model, rec = self.run_q([self.JULY_2026, self.WITH_ROWS])
        self.assertEqual(len(model.calls), 1)  # no second model call
        self.assertTrue(rec["declined"])
        self.assertTrue(rec["system_declined"])
        self.assertIsNone(rec["final_sql"])
        self.assertEqual(rec["final_reply"], "NO_QUERY: " + self.REASON)
        print("\nSYSTEM DECLINE REASON (test a):\n" + self.REASON)
        self.assertEqual((rec["system_decline_period"][0]["start"], rec["system_decline_period"][0]["end"]),
                         ("2026-07-01", "2026-07-31"))
        self.assertEqual(rec["n_attempts"], 1)
        self.assertFalse(rec["retried"])
        self.assertFalse(rec["ended_empty"])
        self.assertFalse(rec["empty_fact_fired"])  # the R3 Fact line is never sent
        self.assertFalse(rec["declined_after_empty"])
        self.assertFalse(rec["cap_hit"])

    def test_graded_like_a_no_query(self):
        # the reply starts with NO_QUERY, so the existing decline detection treats it as one
        self.assertTrue(agent_loop.is_decline(agent_loop.run_question(
            "q", self.R3B, llm=FakeModel([self.JULY_2026]), prompt_builder=lambda q: "p")["final_reply"]))

    def test_b_empty_result_over_a_period_with_rows_uses_the_r2_message(self):
        model, rec = self.run_q([self.EMPTY_FEB, self.WITH_ROWS])
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(model.calls[1][2]["content"],
                         "This query ran but returned no rows.\nWrite a corrected query. Return only the SQL.")
        self.assertFalse(rec["system_declined"])
        self.assertFalse(rec["empty_fact_fired"])
        self.assertEqual(rec["final_sql"], self.WITH_ROWS)

    def test_c_empty_result_without_a_date_uses_the_r2_message(self):
        model, rec = self.run_q([self.EMPTY_NO_DATE, self.WITH_ROWS])
        self.assertEqual(model.calls[1][2]["content"],
                         "This query ran but returned no rows.\nWrite a corrected query. Return only the SQL.")
        self.assertFalse(rec["system_declined"])
        self.assertEqual(rec["system_decline_period"], [])

    def test_system_decline_after_an_earlier_error_retry(self):
        model, rec = self.run_q([BROKEN_HINT, self.JULY_2026, self.WITH_ROWS])
        self.assertEqual(len(model.calls), 2)
        self.assertTrue(rec["system_declined"])
        self.assertEqual(rec["n_attempts"], 2)
        self.assertTrue(rec["retried_after_error"])

    def test_d_switch_off_behaves_like_r3(self):
        for replies in ([self.JULY_2026, "NO_QUERY: x"], [self.EMPTY_FEB, self.WITH_ROWS],
                        [self.EMPTY_NO_DATE, self.WITH_ROWS], [BROKEN_HINT, self.WITH_ROWS],
                        ["NO_QUERY: Data for 2025 is missing.", self.WITH_ROWS]):
            m_off, r_off = self.run_q(replies, dict(self.R3, empty_fact_decline=False))
            m_default, r_default = self.run_q(replies, dict(self.R3))
            self.assertEqual(m_off.calls, m_default.calls)
            for key in ("final_sql", "final_reply", "n_attempts", "declined", "system_declined",
                        "empty_fact_fired", "review_fired"):
                self.assertEqual(r_off[key], r_default[key], key)
        # with the switch off the R3 Fact line is still sent
        m, r = self.run_q([self.JULY_2026, "NO_QUERY: x"], dict(self.R3))
        self.assertIn("Fact: the tables have no rows for the period 2026-07-01 to 2026-07-31.", m.calls[1][2]["content"])
        self.assertFalse(r["system_declined"])

    def test_e_attempt_1_prompt_identical_to_v2b_for_all_84_with_r3b_switches(self):
        questions = load_questions()
        identical = 0
        for q in questions:
            model = FakeModel(["NO_QUERY: test"])
            agent_loop.run_question(q.frage, self.R3B, llm=model)
            sent = model.calls[0]
            if (len(sent) == 1 and sent[0]["role"] == "user"
                    and sent[0]["content"] == prompt_template_v2b.build_prompt(q.frage)):
                identical += 1
        print(f"\nR3b switches: {identical}/{len(questions)} attempt-1 prompts identical to v2b")
        self.assertEqual(identical, len(questions))

    def test_run_r3b_pipeline_with_fake_model(self):
        import json
        import run_r3b

        gold = {q.frage: q for q in load_questions()}

        def fake_llm(messages):
            frage = messages[0]["content"].split("Question: ", 1)[1].split("\n\n", 1)[0]
            q = gold[frage]
            if q.id == "u_08":
                reply = self.JULY_2026
            elif q.is_tier0:
                reply = "NO_QUERY: not in the data"
            else:
                reply = q.gold_sql
            return {"raw_model_output": reply, "prompt_tokens": 1000, "completion_tokens": 50,
                    "latency_seconds": 0.1, "model": "gpt-4o-2024-08-06", "system_fingerprint": "fp_test"}

        with tempfile.TemporaryDirectory() as tmp:
            code = run_r3b.run(tag="smoke", llm=fake_llm, results_dir=Path(tmp))
            self.assertEqual(code, 0)  # 84/84: u_08 passes through the system decline
            logs = list(Path(tmp).glob("r3b_smoke_*.log")); jsonls = list(Path(tmp).glob("r3b_smoke_*.jsonl"))
            self.assertEqual((len(logs), len(jsonls)), (1, 1))
            recs = {r["id"]: r for r in map(json.loads, open(jsonls[0]))}
            self.assertTrue(recs["u_08"]["system_declined"])
            self.assertTrue(recs["u_08"]["passed"])
            self.assertEqual(recs["u_08"]["n_attempts"], 1)
            self.assertEqual(recs["u_08"]["raw_model_output"], "NO_QUERY: " + self.REASON)
            self.assertIsNone(recs["u_08"]["extracted_sql"])
            self.assertEqual(sum(r["system_declined"] for r in recs.values()), 1)
            report = logs[0].read_text().lower()
            for needle in ("system declines", "u_08", "declined by the system after the empty result"):
                self.assertIn(needle, report)


class TestModelVersionLogging(unittest.TestCase):
    """response.model and response.system_fingerprint are saved per call and end up
    in every .jsonl record (null if the response has no such field)."""

    @staticmethod
    def _response(**extra):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="SELECT 1"))],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2), **extra)

    def _recorded_record(self, response):
        import result_logging
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: response)))
        agent_module = SimpleNamespace(OpenAI=lambda *a, **k: client)
        recorder = result_logging.install_recorder(agent_module)
        recorder.begin()
        agent_module.OpenAI().chat.completions.create(model="gpt-4o-2024-08-06", messages=[])
        question = SimpleNamespace(id="x_01", tier=1, frage="q")
        result = SimpleNamespace(passed=True, reason="ok")
        return result_logging.make_record(question, result, "SELECT 1", recorder.take())

    def test_result_logging_writes_both_fields(self):
        rec = self._recorded_record(self._response(model="gpt-4o-2024-08-06", system_fingerprint="fp_test"))
        self.assertEqual(rec["model"], "gpt-4o-2024-08-06")
        self.assertEqual(rec["system_fingerprint"], "fp_test")
        self.assertEqual(rec["prompt_tokens"], 5)  # the existing fields are unchanged

    def test_result_logging_null_if_missing(self):
        rec = self._recorded_record(self._response())  # no model, no fingerprint
        self.assertIn("model", rec)
        self.assertIn("system_fingerprint", rec)
        self.assertIsNone(rec["model"])
        self.assertIsNone(rec["system_fingerprint"])

    def test_call_openai_returns_both_fields(self):
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: self._response(model="gpt-4o-2024-08-06", system_fingerprint="fp_test"))))
        out = agent_loop.call_openai([{"role": "user", "content": "x"}], client=client)
        self.assertEqual((out["model"], out["system_fingerprint"]), ("gpt-4o-2024-08-06", "fp_test"))
        out = agent_loop.call_openai([{"role": "user", "content": "x"}], client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: self._response()))))
        self.assertEqual((out["model"], out["system_fingerprint"]), (None, None))

    def test_sent_settings_are_unchanged(self):
        seen = {}
        def create(**kw):
            seen.update(kw)
            return self._response(model="gpt-4o-2024-08-06", system_fingerprint="fp_test")
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        agent_loop.call_openai([{"role": "user", "content": "x"}], client=client)
        self.assertEqual((seen["model"], seen["temperature"], seen["seed"]), ("gpt-4o-2024-08-06", 0, 0))

    def test_attempts_and_jsonl_record_carry_both_fields(self):
        import json
        import run_r1

        gold = {q.frage: q for q in load_questions()}
        calls = {"n": 0}

        def fake_llm(messages):
            frage = messages[0]["content"].split("Question: ", 1)[1].split("\n\n", 1)[0]
            q = gold[frage]
            calls["n"] += 1
            if q.id == "t1_01" and len(messages) == 1:
                reply = BROKEN_HINT
            elif q.is_tier0:
                reply = "NO_QUERY: x"
            else:
                reply = q.gold_sql
            return {"raw_model_output": reply, "prompt_tokens": 1, "completion_tokens": 1,
                    "latency_seconds": 0.0, "model": "gpt-4o-2024-08-06",
                    "system_fingerprint": f"fp_test_{calls['n']}"}

        with tempfile.TemporaryDirectory() as tmp:
            run_r1.run(tag="mv", llm=fake_llm, results_dir=Path(tmp))
            recs = [json.loads(l) for l in open(next(Path(tmp).glob("r1_mv_*.jsonl")))]
        self.assertEqual(len(recs), 84)
        for r in recs:
            self.assertEqual(r["model"], "gpt-4o-2024-08-06")
            self.assertTrue(r["system_fingerprint"].startswith("fp_test_"))
            for a in r["attempts"]:  # per attempt
                self.assertEqual(a["model"], "gpt-4o-2024-08-06")
                self.assertTrue(a["system_fingerprint"].startswith("fp_test_"))
        retried = next(r for r in recs if r["id"] == "t1_01")
        self.assertEqual(len(retried["attempts"]), 2)
        self.assertEqual(retried["system_fingerprint"], retried["attempts"][-1]["system_fingerprint"])
        self.assertNotEqual(retried["attempts"][0]["system_fingerprint"], retried["attempts"][1]["system_fingerprint"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
