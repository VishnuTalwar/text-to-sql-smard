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
import unittest
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
from tracing_fakes import RaisingTracer, RecordingTracer  # noqa: E402

ENV = {"LANGFUSE_PUBLIC_KEY": "pk-test", "LANGFUSE_SECRET_KEY": "sk-secret-123",
       "LANGFUSE_HOST": "https://cloud.langfuse.com"}


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
        self.assertIsNone(t.model_call(None, [], "x", "m", 1, 1, 0.0))
        self.assertIsNone(t.safety_check(None, "sql", {}))
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
            self.assertIsNone(t.model_call("x", [], "o", "m", 1, 1, 0.0))
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
        self.assertEqual(g.status, "tracing off: tracer failed")
        self.assertFalse(g.enabled)
        self.assertEqual(tracing.guarded(None).status, "tracing off: no keys")


class TestLangfuseTracerWithRealSdk(unittest.TestCase):
    """Our calls against the installed Langfuse SDK, with an in-memory exporter (nothing is sent)."""

    def setUp(self):
        from langfuse import Langfuse
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        self.exporter = InMemorySpanExporter()
        self.client = Langfuse(public_key="pk-test", secret_key="sk-test", base_url="http://127.0.0.1:9",
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
        t.model_call(tid, [{"role": "user", "content": "hi"}], "SELECT 1", "gpt-4o", 100, 5, 0.0003,
                     {"attempt": 1, "system_fingerprint": "fp_x"})
        t.safety_check(tid, "SELECT 1", {"blocked": False, "n_rows": 1}, 0.0123)
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
        self.assertEqual(len(tracer.of("safety_check")), 2)
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
        # generation step: messages, output, model, tokens, cost, fingerprint, attempt
        (a1, k1), (a2, k2) = tracer.of("model_call")
        self.assertEqual(a1[2], BROKEN)
        self.assertEqual(a1[3], "fake-model")
        self.assertEqual((a1[4], a1[5], a1[6]), (1000, 20, answer.call_cost(1000, 20)))
        self.assertEqual((k1["metadata"]["attempt"], k2["metadata"]["attempt"]), (1, 2))
        self.assertEqual(k1["metadata"]["system_fingerprint"], "fp_fake")
        self.assertEqual(a2[1][-1]["role"], "user")  # the retry text is the last message of attempt 2's input
        self.assertEqual(len(a2[1]), len(a1[1]) + 2)
        # safety step: first blocked? no: an SQL error, so no wall; second one ran
        (sa1, sk1), (sa2, sk2) = tracer.of("safety_check")
        self.assertEqual(sa1[1], BROKEN)
        self.assertEqual(sa2[2]["n_rows"], 5)
        self.assertFalse(sa2[2]["blocked"])
        self.assertEqual(r.tracing_status, "tracing on")

    def test_c_a_tracer_that_raises_changes_nothing(self):
        null = answer.answer_question("Show some wind generation values.", model_caller=FakeModel([BROKEN, GOOD]))
        with self.assertLogs("app.tracing", "WARNING"):
            bad = answer.answer_question("Show some wind generation values.",
                                         model_caller=FakeModel([BROKEN, GOOD]), tracer=RaisingTracer(),
                                         session_id="s")
        self.assertTrue(same_answer(null, bad))
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
        self.assertEqual(kwargs["metadata"]["step"], "summary")
        self.assertEqual((args[4], args[5]), (200, 10))
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
