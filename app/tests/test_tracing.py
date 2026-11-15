"""
Tracing tests (D45). No network: no OpenAI, no Langfuse server. The real Langfuse SDK is used only with an
in-memory span exporter and a dead local address, to check that our calls fit the SDK.
"""

import dataclasses
import json
import logging
import os
import subprocess
import sys
import time
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "tests"))

import answer  # noqa: E402
import summary  # noqa: E402
import tracing  # noqa: E402
from test_answer import (BROKEN, GOOD, FakeModel, TestEquivalenceWithRunPy)  # noqa: E402
from tracing_fakes import RaisingStepTracer, RaisingTracer, RecordingTracer  # noqa: E402

KEYS = {"LANGFUSE_PUBLIC_KEY": "pk-test", "LANGFUSE_SECRET_KEY": "sk-secret-123"}
ENV = {**KEYS, "LANGFUSE_BASE_URL": "https://cloud.langfuse.com"}
ENV_OLD = {**KEYS, "LANGFUSE_HOST": "https://old.example.com"}


class SummaryModel:
    def __init__(self, reply="The table lists generation values."):
        self.reply, self.calls = reply, 0

    def __call__(self, messages):
        self.calls += 1
        return {"raw_model_output": self.reply, "prompt_tokens": 200, "completion_tokens": 10,
                "latency_seconds": 0.1, "model": "fake-model", "system_fingerprint": "fp_fake"}


def same_answer(a, b):
    """Everything an AnswerResult says about the answer (timing and tracing fields left out)."""
    skip = {"seconds_total", "seconds_model", "trace_id", "tracing_status"}
    da, db = dataclasses.asdict(a), dataclasses.asdict(b)
    return {k: v for k, v in da.items() if k not in skip} == {k: v for k, v in db.items() if k not in skip}


class TestGetTracer(unittest.TestCase):
    def test_d_no_env_vars_gives_null_tracer(self):
        t = tracing.get_tracer(environ={})
        self.assertIsInstance(t, tracing.NullTracer)
        self.assertEqual(t.status, "tracing off: no keys")
        self.assertFalse(t.enabled)

    def test_d_real_environment_without_langfuse_vars(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("dotenv.load_dotenv"):
            t = tracing.get_tracer()
        self.assertIsInstance(t, tracing.NullTracer)
        self.assertEqual(t.status, "tracing off: no keys")

    def test_one_missing_variable_is_no_keys(self):
        for name in ENV:
            env = {k: v for k, v in ENV.items() if k != name}
            self.assertEqual(tracing.get_tracer(environ=env).status, "tracing off: no keys", name)

    def test_each_url_name_alone_works_and_base_url_wins(self):
        def start(env):
            made = {}
            t = tracing.get_tracer(environ=env, client_factory=lambda **kw: made.update(kw) or object())
            return t, made

        t, made = start(ENV)
        self.assertEqual((t.status, made["base_url"]), ("tracing on", "https://cloud.langfuse.com"))
        t, made = start(ENV_OLD)  # LANGFUSE_HOST alone
        self.assertEqual((t.status, made["base_url"]), ("tracing on", "https://old.example.com"))
        t, made = start({**ENV, **ENV_OLD})  # both: LANGFUSE_BASE_URL is read first
        self.assertEqual(made["base_url"], "https://cloud.langfuse.com")
        t, made = start(KEYS)  # neither
        self.assertEqual(t.status, "tracing off: no keys")
        self.assertEqual(made, {})

    def test_all_three_variables_start_a_langfuse_tracer(self):
        made = {}

        def factory(**kwargs):
            made.update(kwargs)
            return object()

        t = tracing.get_tracer(environ=ENV, client_factory=factory)
        self.assertIsInstance(t, tracing.LangfuseTracer)
        self.assertEqual(t.status, "tracing on")
        self.assertEqual(made, {"public_key": "pk-test", "secret_key": "sk-secret-123",
                                "base_url": "https://cloud.langfuse.com"})

    def test_client_that_fails_to_start(self):
        def factory(**kwargs):
            raise RuntimeError("boom sk-secret-123")

        with self.assertLogs("app.tracing", "WARNING") as logs:
            t = tracing.get_tracer(environ=ENV, client_factory=factory)
        self.assertIsInstance(t, tracing.NullTracer)
        self.assertEqual(t.status, "tracing off: client failed to start")
        self.assertNotIn("sk-secret-123", "\n".join(logs.output))

    def test_null_tracer_does_nothing(self):
        t = tracing.NullTracer()
        self.assertIsNone(t.start_trace("n", "q", session_id="s", tags=["a"], metadata={}))
        for step in (t.model_call(None, []), t.safety_check(None, "sql")):
            self.assertIsNone(step.finish("out"))
            self.assertIsNone(step.fail(RuntimeError("x")))
        self.assertIsNone(t.loop_decision(None, 1, "ok"))
        self.assertIsNone(t.summary(None, True))
        self.assertFalse(t.score("t", "n", 1))
        self.assertIsNone(t.end_trace(None, {}))
        self.assertIsNone(t.flush())


class FailingClient:
    def __init__(self, fail_on):
        self.fail_on = fail_on

    def start_observation(self, **kwargs):
        if self.fail_on == "start_observation":
            raise RuntimeError("down: sk-secret-123 and sk-openai-456")
        raise AssertionError("not reached")

    def flush(self):
        raise RuntimeError("flush down")

    def create_score(self, **kwargs):
        raise RuntimeError("score down")


class TestLangfuseTracerFailOpen(unittest.TestCase):
    def test_failure_logs_one_warning_switches_off_and_never_raises(self):
        t = tracing.LangfuseTracer(FailingClient("start_observation"), secrets=["sk-secret-123", "sk-openai-456"])
        with self.assertLogs("app.tracing", "WARNING") as logs:
            self.assertIsNone(t.start_trace("n", "q"))
            # after the failure every call is a quiet no-op
            self.assertIsNone(t.start_trace("n", "q"))
            t.model_call("x", []).finish("o")
            self.assertFalse(t.score("x", "n", 1))
            self.assertIsNone(t.flush())
        self.assertEqual(len(logs.output), 1)
        self.assertNotIn("sk-secret-123", logs.output[0])
        self.assertNotIn("sk-openai-456", logs.output[0])
        self.assertTrue(t.status.startswith("tracing off: start_trace failed"))
        self.assertFalse(t.enabled)

    def test_flush_and_score_failures_do_not_raise(self):
        t = tracing.LangfuseTracer(FailingClient("none"))
        with self.assertLogs("app.tracing", "WARNING"):
            self.assertFalse(t.score("trace", "user_says_correct", 1))
        t = tracing.LangfuseTracer(FailingClient("none"))
        with self.assertLogs("app.tracing", "WARNING"):
            self.assertIsNone(t.flush())
        self.assertFalse(t.enabled)

    def test_guarded_wraps_a_tracer_whose_every_method_raises(self):
        g = tracing.guarded(RaisingTracer())
        with self.assertLogs("app.tracing", "WARNING"):
            self.assertIsNone(g.start_trace("n", "q"))
            self.assertFalse(g.score("t", "n", 1))
            self.assertIsNone(g.flush())
            g.model_call("t", []).finish("o")  # the step of a failed call is a harmless no-op step
            g.safety_check("t", "sql").fail(RuntimeError("x"))
        self.assertEqual(g.status, "tracing off: tracer failed")
        self.assertFalse(g.enabled)
        self.assertEqual(tracing.guarded(None).status, "tracing off: no keys")


class TestLangfuseTracerWithRealSdk(unittest.TestCase):
    """Our calls against the installed Langfuse SDK, with an in-memory exporter (nothing is sent)."""

    def setUp(self):
        from langfuse import Langfuse
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        self.exporter = InMemorySpanExporter()
        # the SDK keeps one set of resources per public key, so every test needs its own key (and exporter)
        self.client = Langfuse(public_key=f"pk-test-{uuid.uuid4().hex}", secret_key="sk-test", base_url="http://127.0.0.1:9",
                               span_exporter=self.exporter)
        self.tracer = tracing.LangfuseTracer(self.client, secrets=["sk-test"])
        self.addCleanup(self.client.shutdown)

    def spans(self):
        self.tracer.flush()
        return {s.name: s for s in self.exporter.get_finished_spans()}

    def test_trace_with_nested_steps(self):
        t = self.tracer
        tid = t.start_trace("answer_question", "How much solar?", session_id="sess-1", tags=["r3b_safe"],
                            metadata={"config": "grader/configs/r3b_safe.yaml", "model": "m", "git_commit": "abc1234"})
        self.assertRegex(tid, r"^[0-9a-f]{32}$")
        step = t.model_call(tid, [{"role": "user", "content": "hi"}], {"attempt": 1})
        step.finish("SELECT 1", "gpt-4o", 100, 5, 0.0003, {"system_fingerprint": "fp_x"})
        t.safety_check(tid, "SELECT 1").finish({"blocked": False, "n_rows": 1, "seconds": 0.0123})
        t.loop_decision(tid, 1, "ok", {"n_rows": 1})
        t.end_trace(tid, {"status": "answered"}, tags=["answered", "r3b_safe"])
        t.summary(tid, False, "number_check", [Decimal("5")])  # after the root has ended
        self.assertTrue(t.enabled, t.status)
        spans = self.spans()
        root = spans["answer_question"]
        self.assertEqual(json.loads(root.attributes["langfuse.observation.output"]), {"status": "answered"})
        self.assertEqual(root.attributes["langfuse.observation.input"], "How much solar?")
        gen = spans["model call"]
        self.assertEqual(gen.attributes["langfuse.observation.type"], "generation")
        self.assertEqual(gen.attributes["langfuse.observation.model.name"], "gpt-4o")
        self.assertEqual(json.loads(gen.attributes["langfuse.observation.usage_details"]),
                         {"input": 100, "output": 5, "total": 105})
        self.assertEqual(json.loads(gen.attributes["langfuse.observation.cost_details"]), {"total": 0.0003})
        self.assertEqual(gen.attributes["langfuse.observation.metadata.attempt"], "1")
        self.assertEqual(gen.attributes["langfuse.observation.metadata.system_fingerprint"], '"fp_x"')
        self.assertEqual(gen.attributes["langfuse.observation.input"], '[{"role": "user", "content": "hi"}]')
        self.assertEqual(gen.parent.span_id, root.context.span_id)
        for name, span in spans.items():  # one trace, session id on every step
            self.assertEqual(span.context.trace_id, root.context.trace_id, name)
            self.assertEqual(span.attributes["session.id"], "sess-1", name)
        self.assertEqual(spans["safety check and run"].attributes["langfuse.observation.input"], "SELECT 1")
        self.assertEqual(json.loads(spans["safety check and run"].attributes["langfuse.observation.output"]),
                         {"blocked": False, "n_rows": 1, "seconds": 0.0123})
        self.assertEqual(spans["trace result"].attributes["langfuse.trace.tags"], ("answered", "r3b_safe"))
        check = json.loads(spans["summary number check"].attributes["langfuse.observation.output"])
        self.assertEqual(check, {"shown": False, "hidden_reason": "number_check", "unknown_numbers": ["5"]})


    def test_a_failed_step_records_the_error_and_has_a_duration(self):
        tid = self.tracer.start_trace("answer_question", "q")
        step = self.tracer.safety_check(tid, "SELECT oops")
        time.sleep(0.05)
        step.fail(RuntimeError("column oops does not exist"))
        span = self.spans()["safety check and run"]
        self.assertEqual(span.attributes["langfuse.observation.level"], "ERROR")
        self.assertIn("column oops does not exist", span.attributes["langfuse.observation.output"])
        self.assertGreaterEqual(span.end_time - span.start_time, 0.05e9)

    def test_real_durations_a_slow_model_gives_a_generation_of_at_least_0_2_s(self):
        class SlowModel(FakeModel):
            def __call__(self, messages):
                time.sleep(0.2)
                return super().__call__(messages)

        r = answer.answer_question("Show some wind generation values.", model_caller=SlowModel([GOOD]),
                                   tracer=self.tracer)
        self.assertEqual(r.status, "answered")
        self.assertTrue(self.tracer.enabled, self.tracer.status)
        spans = self.spans()
        gen = spans["model call"]
        self.assertGreaterEqual(gen.end_time - gen.start_time, 0.2e9)
        self.assertEqual(json.loads(gen.attributes["langfuse.observation.usage_details"]),
                         {"input": 1000, "output": 20, "total": 1020})
        self.assertEqual(gen.attributes["langfuse.observation.output"], GOOD)
        safety = spans["safety check and run"]  # the step covers the real run, not just a point in time
        self.assertGreater(safety.end_time, safety.start_time)
        self.assertLess(safety.start_time, gen.end_time + 1e9)
        self.assertGreaterEqual(safety.start_time, gen.end_time)  # it starts after the model call returned


class TestAnswerQuestionTracing(unittest.TestCase):
    def test_a_equivalence_with_run_py_also_with_a_recording_tracer(self):
        tracer = RecordingTracer()
        TestEquivalenceWithRunPy("test_g_same_attempts_and_final_sql_as_run_py").check_equivalence(tracer)
        self.assertEqual(len(tracer.of("start_trace")), 5)
        self.assertEqual(len(tracer.of("end_trace")), 5)

    def test_b_two_attempts_error_then_good(self):
        tracer = RecordingTracer()
        r = answer.answer_question("Show some wind generation values.", model_caller=FakeModel([BROKEN, GOOD]),
                                   tracer=tracer, session_id="sess-9")
        self.assertEqual(r.status, "answered")
        self.assertEqual(len(r.attempts), 2)
        self.assertEqual(len(tracer.of("model_call")), 2)
        self.assertEqual(len(tracer.of("model_call.finish")), 2)
        self.assertEqual(len(tracer.of("safety_check")), 2)
        self.assertEqual(len(tracer.of("safety_check.fail")), 1)    # attempt 1: the SQL error
        self.assertEqual(len(tracer.of("safety_check.finish")), 1)  # attempt 2: ran
        self.assertEqual(len(tracer.of("loop_decision")), 2)
        self.assertEqual([a[2] for a, _ in tracer.of("loop_decision")], ["error", "ok"])
        # all steps on the one trace the answer reports
        self.assertEqual(r.trace_id, "trace-1")
        for m in ("model_call", "safety_check", "loop_decision", "end_trace"):
            self.assertTrue(all(a[0] == "trace-1" for a, _ in tracer.of(m)), m)
        (args, kwargs), = tracer.of("end_trace")
        self.assertEqual(args[1]["status"], "answered")
        self.assertEqual(args[1]["final_sql"], GOOD)
        self.assertEqual(kwargs["tags"], ["answered", "r3b_safe"])
        # start of the trace: name, question, session id, tags, metadata
        (args, kwargs), = tracer.of("start_trace")
        self.assertEqual(args, ("answer_question", "Show some wind generation values."))
        self.assertEqual(kwargs["session_id"], "sess-9")
        self.assertEqual(kwargs["tags"], ["r3b_safe"])
        self.assertEqual(set(kwargs["metadata"]), {"config", "model", "git_commit"})
        self.assertEqual(kwargs["metadata"]["config"], answer.DEFAULT_CONFIG)
        self.assertEqual(kwargs["metadata"]["model"], "gpt-4o-2024-08-06")
        self.assertTrue(kwargs["metadata"]["git_commit"])
        # generation step: starts with the messages and the attempt number, ends with output, model, tokens, cost
        (a1, k1), (a2, k2) = tracer.of("model_call")
        (f1, g1), (f2, g2) = tracer.of("model_call.finish")
        self.assertEqual((k1, k2), ({}, {}))
        self.assertEqual((a1[2]["attempt"], a2[2]["attempt"]), (1, 2))
        self.assertEqual(f1[0], BROKEN)
        self.assertEqual(f1[1], "fake-model")
        self.assertEqual((f1[2], f1[3], f1[4]), (1000, 20, answer.call_cost(1000, 20)))
        self.assertEqual(f1[5]["system_fingerprint"], "fp_fake")
        self.assertEqual(a2[1][-1]["role"], "user")  # the retry text is the last message of attempt 2's input
        self.assertEqual(len(a2[1]), len(a1[1]) + 2)
        # safety steps: the first query failed, the second ran
        (sa1, _), (sa2, _) = tracer.of("safety_check")
        self.assertEqual((sa1[1], sa2[1]), (BROKEN, GOOD))
        (fail_args, _), = tracer.of("safety_check.fail")
        self.assertIn("mwhh", str(fail_args[0]))
        (ok_args, _), = tracer.of("safety_check.finish")
        self.assertEqual(ok_args[0]["n_rows"], 5)
        self.assertFalse(ok_args[0]["blocked"])
        self.assertEqual(r.tracing_status, "tracing on")

    def test_c_a_tracer_that_raises_changes_nothing(self):
        null = answer.answer_question("Show some wind generation values.", model_caller=FakeModel([BROKEN, GOOD]))
        with self.assertLogs("app.tracing", "WARNING"):
            bad = answer.answer_question("Show some wind generation values.",
                                         model_caller=FakeModel([BROKEN, GOOD]), tracer=RaisingTracer(),
                                         session_id="s")
        self.assertTrue(same_answer(null, bad))
        with self.assertLogs("app.tracing", "WARNING"):  # steps whose finish/fail raise
            bad2 = answer.answer_question("Show some wind generation values.",
                                          model_caller=FakeModel([BROKEN, GOOD]), tracer=RaisingStepTracer())
        self.assertTrue(same_answer(null, bad2))
        self.assertIsNone(bad.trace_id)
        self.assertEqual(null.tracing_status, "tracing off: no keys")
        self.assertEqual(bad.tracing_status, "tracing off: tracer failed")
        # summarize: same Summary with a null tracer and a tracer that raises
        with self.assertLogs("app.tracing", "WARNING"):
            s_bad = summary.summarize(null, model_caller=SummaryModel(), tracer=RaisingTracer())
        s_null = summary.summarize(null, model_caller=SummaryModel())
        self.assertEqual(s_bad, s_null)
        self.assertTrue(s_null.shown)

    def test_tracer_none_calls_nothing_and_equals_old_behaviour(self):
        r = answer.answer_question("Show some wind generation values.", model_caller=FakeModel([GOOD]))
        self.assertEqual((r.status, r.trace_id), ("answered", None))

    def test_a_model_error_closes_the_trace_and_is_raised_as_before(self):
        def broken_model(messages):
            raise ConnectionError("no network")

        tracer = RecordingTracer()
        with self.assertRaises(ConnectionError):
            answer.answer_question("q?", model_caller=broken_model, tracer=tracer)
        (args, kwargs), = tracer.of("end_trace")
        self.assertEqual(args[1], {"status": "exception", "error": "ConnectionError"})
        (fail_args, _), = tracer.of("model_call.fail")  # the step is closed with the error, then it is re-raised
        self.assertIsInstance(fail_args[0], ConnectionError)
        self.assertEqual(len(tracer.of("flush")), 1)

    def test_e_summary_steps_are_on_the_same_trace(self):
        tracer = RecordingTracer()
        r = answer.answer_question("Show some wind generation values.", model_caller=FakeModel([GOOD]),
                                   tracer=tracer)
        s = summary.summarize(r, model_caller=SummaryModel(), tracer=tracer)
        self.assertTrue(s.shown)
        gens = tracer.of("model_call")
        self.assertEqual(len(gens), 2)  # the answer's model call and the summary's
        (args, kwargs) = gens[1]
        self.assertEqual(args[0], r.trace_id)
        self.assertEqual(args[2], {"step": "summary"})
        (fargs, _) = tracer.of("model_call.finish")[1]
        self.assertEqual((fargs[2], fargs[3]), (200, 10))
        (sargs, _), = tracer.of("summary")
        self.assertEqual(sargs, (r.trace_id, True, None, []))
        self.assertEqual(len(tracer.of("start_trace")), 1)  # no second trace
        self.assertEqual(tracer.calls[-1][0], "flush")      # flushed after the summary
        # a hidden summary records the reason
        s2 = summary.summarize(r, model_caller=SummaryModel("The table shows 12345 rows."), tracer=tracer)
        self.assertFalse(s2.shown)
        sargs, _ = tracer.of("summary")[-1]
        self.assertEqual(sargs[:3], (r.trace_id, False, "number_check"))
        self.assertEqual([str(n) for n in sargs[3]], ["12345"])

    def test_f_trace_output_holds_at_most_50_rows(self):
        tracer = RecordingTracer()
        r = answer.answer_question("Show sixty values.", model_caller=FakeModel(["SELECT mwh FROM erzeugung LIMIT 60"]),
                                   tracer=tracer)
        self.assertEqual(r.row_count, 60)
        (args, _), = tracer.of("end_trace")
        out = args[1]
        self.assertEqual(len(out["rows"]), 50)
        self.assertEqual(out["row_count"], 60)
        self.assertTrue(out["rows_truncated"])
        self.assertEqual(out["status"], "answered")
        json.dumps(out)  # JSON-ready (Decimal and datetime values are converted)

    def test_trace_output_converts_values_and_keeps_small_results_whole(self):
        from datetime import datetime
        res = answer.AnswerResult(question="q", status="answered", message="", final_sql="SELECT 1",
                                  columns=["t", "x"], rows=[(datetime(2025, 7, 1, 0, 15), Decimal("1.50"))], row_count=1)
        out = answer.trace_output(res)
        self.assertEqual(out["rows"], [["2025-07-01T00:15:00", "1.50"]])
        self.assertFalse(out["rows_truncated"])
        json.dumps(out)


class TestRunPyIsNotTraced(unittest.TestCase):
    def test_h_grader_sources_do_not_mention_tracing_or_langfuse(self):
        for path in sorted((PROJECT_ROOT / "grader").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for word in ("import tracing", "from tracing", "langfuse"):
                self.assertNotIn(word, text.lower() if word == "langfuse" else text, f"{path.name}: {word}")

    def test_h_importing_run_py_loads_neither_tracing_nor_langfuse(self):
        code = ("import sys; sys.path.insert(0, 'grader'); import run, agent_loop, safe_runner; "
                "print('tracing' in sys.modules, 'langfuse' in sys.modules)")
        out = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip().splitlines()[-1], "False False")


if __name__ == "__main__":
    unittest.main(verbosity=2)
