"""
Smoke test of app/streamlit_app.py with Streamlit's AppTest. answer_question and summarize are
replaced by fakes: no model call, no database, no API.
"""

import dataclasses
import sys
import unittest
import uuid
from decimal import Decimal
from pathlib import Path
from unittest import mock

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"
sys.path.insert(0, str(APP_DIR))

sys.path.insert(0, str(APP_DIR / "tests"))

import answer  # noqa: E402
import summary  # noqa: E402
import tracing  # noqa: E402
from tracing_fakes import RecordingTracer  # noqa: E402

PAGE = str(APP_DIR / "streamlit_app.py")
QUESTION = "How much electricity did solar produce in total in June 2025?"


def answered_result(question):
    return answer.AnswerResult(
        question=question, status="answered", message="",
        attempts=[answer.Attempt(1, "SELECT SUM(mwh) FROM erzeugung", "ok", None, 1)],
        final_sql="SELECT SUM(mwh) FROM erzeugung", columns=["sum"], rows=[(Decimal("9056373.39"),)],
        row_count=1, seconds_total=1.5, seconds_model=1.2, prompt_tokens=1000, completion_tokens=20,
        cost_usd=0.0027, model="fake-model", system_fingerprint="fp_fake")


def no_rows_result(question):
    sql = "SELECT mwh FROM erzeugung WHERE energietraeger = 'X'"
    return answer.AnswerResult(
        question=question, status="no_rows", message="No rows match this question.",
        attempts=[answer.Attempt(i, sql, "empty_rows", "the query returned no rows", 0) for i in (1, 2, 3)],
        final_sql=sql, columns=["mwh"], rows=[], row_count=0, model="fake-model")


def table_result(columns, rows, sql):
    return lambda question: answer.AnswerResult(
        question=question, status="answered", message="",
        attempts=[answer.Attempt(1, sql, "ok", None, len(rows))], final_sql=sql, columns=columns,
        rows=rows, row_count=len(rows), model="fake-model")


class Fakes:
    def __init__(self, make_result):
        self.make_result = make_result
        self.answer_calls, self.summary_calls = [], []
        self.answer_kwargs, self.summary_kwargs = [], []

    def answer_question(self, question, *a, **k):
        self.answer_calls.append(question)
        self.answer_kwargs.append(k)
        return self.make_result(question)

    def summarize(self, result, *a, **k):
        self.summary_calls.append(result)
        self.summary_kwargs.append(k)
        return summary.Summary("The total was 9,056,373.39.", True, None, [], 200, 20, 0.0007)

    def patched(self):
        return mock.patch.multiple(answer, answer_question=self.answer_question), \
            mock.patch.multiple(summary, summarize=self.summarize)


def texts(at):
    """All visible text of the page, as one string."""
    out = []
    for kind in ("markdown", "info", "warning", "error", "caption", "subheader", "title", "text", "metric"):
        for el in getattr(at, kind):
            out.append(str(getattr(el, "value", "")))
            if kind == "metric":
                out.append(str(el.label))
    return "\n".join(out)


def use_tracer(test, tracer):
    """The page asks tracing.get_tracer() once per process (cached); give it this tracer."""
    import streamlit as st
    st.cache_resource.clear()
    patcher = mock.patch.object(tracing, "get_tracer", return_value=tracer)
    patcher.start()
    test.addCleanup(patcher.stop)
    test.addCleanup(st.cache_resource.clear)


class TestStreamlitApp(unittest.TestCase):
    def setUp(self):
        use_tracer(self, tracing.NullTracer())  # never a real Langfuse client in tests

    def run_page(self, fakes):
        p1, p2 = fakes.patched()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)
        p1.start()
        p2.start()
        at = AppTest.from_file(PAGE, default_timeout=30)
        return at.run()

    def test_renders_without_calling_anything(self):
        fakes = Fakes(answered_result)
        at = self.run_page(fakes)
        self.assertFalse(at.exception)
        self.assertEqual(at.title[0].value, "Ask the German electricity data (SMARD)")
        page = texts(at)
        self.assertIn("An AI writes SQL, the SQL runs behind four safety checks", page)
        self.assertIn("Data source: Bundesnetzagentur | SMARD.de", page)
        self.assertIn("Times are German local time. On the autumn clock-change days one hour appears twice", page)
        labels = [b.label for b in at.button]
        self.assertEqual(labels.count("Ask"), 1)
        self.assertEqual(len(labels), 7)  # Ask + 6 examples
        self.assertEqual((fakes.answer_calls, fakes.summary_calls), ([], []))

    def test_ask_calls_each_fake_once_and_reruns_never_do(self):
        fakes = Fakes(answered_result)
        at = self.run_page(fakes)
        at.text_area(key="question_text").set_value(QUESTION).run()
        self.assertEqual((len(fakes.answer_calls), len(fakes.summary_calls)), (0, 0))  # typing is not asking
        next(b for b in at.button if b.label == "Ask").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(fakes.answer_calls, [QUESTION])
        self.assertEqual(len(fakes.summary_calls), 1)
        page = texts(at)
        self.assertIn("AI summary (every number checked against the table)", page)
        self.assertIn("The total was 9,056,373.39.", page)
        self.assertEqual(at.metric[0].value, "9,056,373.39 MWh")
        self.assertEqual([c.language for c in at.code][0], "sql")
        self.assertIn("SELECT SUM(mwh) FROM erzeugung", at.code[0].value)
        self.assertEqual(len(at.expander), 1)
        self.assertEqual(at.expander[0].label, "Behind the scenes")
        # reruns: plain rerun, a rerun after typing, a rerun after clicking an example button
        at.run()
        at.text_area(key="question_text").set_value("something else").run()
        self.assertEqual(len(fakes.answer_calls), 1)
        self.assertEqual(len(fakes.summary_calls), 1)
        self.assertIn("The total was 9,056,373.39.", texts(at))  # the answer on screen is still the stored one
        # an example button only fills the box
        at.button(key="example_u_08").click().run()
        self.assertEqual(len(fakes.answer_calls), 1)
        self.assertIn("July 2026", at.text_area(key="question_text").value)
        # a second Ask calls once more
        next(b for b in at.button if b.label == "Ask").click().run()
        self.assertEqual(len(fakes.answer_calls), 2)
        self.assertEqual(len(fakes.summary_calls), 2)

    def ask(self, make_result, question="A question"):
        fakes = Fakes(make_result)
        at = self.run_page(fakes)
        at.text_area(key="question_text").set_value(question).run()
        next(b for b in at.button if b.label == "Ask").click().run()
        self.assertFalse(at.exception)
        return at

    def test_charts_by_result_shape(self):
        from datetime import datetime
        months = [(datetime(2025, m, 1), Decimal(100 * m)) for m in range(1, 13)]
        at = self.ask(table_result(["month", "total"], months,
                                   "SELECT DATE_TRUNC('month', zeitpunkt) AS month, SUM(mwh) AS total FROM erzeugung GROUP BY 1"))
        self.assertEqual(len(at.get("plotly_chart")), 1)
        self.assertEqual(len(at.metric), 0)
        ranking = [("Wind Onshore", Decimal(5)), ("Photovoltaik", Decimal(3)), ("Erdgas", Decimal(1))]
        at = self.ask(table_result(["quelle", "total"], ranking,
                                   "SELECT energietraeger AS quelle, SUM(mwh) AS total FROM erzeugung GROUP BY 1 ORDER BY 2 DESC"))
        self.assertEqual(len(at.get("plotly_chart")), 1)
        bar = at.get("plotly_chart")[0].proto.spec
        self.assertIn('"Wind Onshore"', bar)
        self.assertLess(bar.index("Wind Onshore"), bar.index("Photovoltaik"))  # SQL order kept
        at = self.ask(table_result(["a", "b"], [("x", "y")], "SELECT a, b FROM erzeugung"))
        self.assertEqual(len(at.get("plotly_chart")), 0)

    def test_table_has_units_in_the_header_and_row_count(self):
        at = self.ask(table_result(["monat", "total"], [(f"m{i}", Decimal("1234.5")) for i in range(3)],
                                   "SELECT energietraeger AS monat, SUM(mwh) AS total FROM erzeugung GROUP BY 1"))
        df = at.dataframe[0].value
        self.assertEqual(list(df.columns), ["monat", "total (MWh)"])
        self.assertEqual(df.iloc[0, 1], "1,234.50")
        self.assertIn("3 rows", texts(at))

    def test_no_rows_message_and_sql_are_shown(self):
        fakes = Fakes(no_rows_result)
        at = self.run_page(fakes)
        at.text_area(key="question_text").set_value("Show wind in January 2025.").run()
        next(b for b in at.button if b.label == "Ask").click().run()
        self.assertFalse(at.exception)
        self.assertEqual([i.value for i in at.info], ["No rows match this question."])
        self.assertEqual(len(at.metric), 0)
        self.assertIn("SELECT mwh FROM erzeugung WHERE energietraeger = 'X'", at.code[0].value)

    def test_an_exception_in_the_core_is_shown_not_raised(self):
        def boom(question, *a, **k):
            raise RuntimeError("database is down")

        with mock.patch.object(answer, "answer_question", boom):
            at = AppTest.from_file(PAGE, default_timeout=30).run()
            at.text_area(key="question_text").set_value(QUESTION).run()
            next(b for b in at.button if b.label == "Ask").click().run()
        self.assertFalse(at.exception)
        self.assertIn("database is down", at.error[0].value)

    def test_empty_question_is_not_asked(self):
        fakes = Fakes(answered_result)
        at = self.run_page(fakes)
        next(b for b in at.button if b.label == "Ask").click().run()
        self.assertEqual(fakes.answer_calls, [])
        self.assertIn("Type a question first.", [w.value for w in at.warning])


def traced_answer(question):
    return dataclasses.replace(answered_result(question), trace_id="trace-abc", tracing_status="tracing on")


class TestFeedbackButtons(unittest.TestCase):
    def start(self, tracer, make_result=traced_answer):
        use_tracer(self, tracer)
        fakes = Fakes(make_result)
        p1, p2 = fakes.patched()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)
        p1.start()
        p2.start()
        at = AppTest.from_file(PAGE, default_timeout=30).run()
        at.text_area(key="question_text").set_value(QUESTION).run()
        next(b for b in at.button if b.label == "Ask").click().run()
        self.assertFalse(at.exception)
        return at, fakes

    @staticmethod
    def feedback_buttons(at):
        return [b for b in at.button if b.label in ("Yes", "No")]

    def test_g_yes_saves_one_score_on_the_trace_and_hides_the_buttons(self):
        tracer = RecordingTracer()
        at, fakes = self.start(tracer)
        self.assertEqual([b.label for b in self.feedback_buttons(at)], ["Yes", "No"])
        self.assertFalse(any(b.disabled for b in self.feedback_buttons(at)))
        self.assertEqual(tracer.of("score"), [])
        at.button(key="fb_yes_trace-abc").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(tracer.of("score"), [(("trace-abc", "user_says_correct", 1), {})])
        self.assertEqual(self.feedback_buttons(at), [])  # the buttons are gone
        self.assertIn("Thanks, saved.", texts(at))
        self.assertEqual((len(fakes.answer_calls), len(fakes.summary_calls)), (1, 1))  # no model call
        self.assertEqual(len(tracer.of("flush")), 1)
        at.run()  # a rerun does not save again
        self.assertEqual(len(tracer.of("score")), 1)
        self.assertEqual(self.feedback_buttons(at), [])

    def test_no_saves_zero(self):
        tracer = RecordingTracer()
        at, fakes = self.start(tracer)
        at.button(key="fb_no_trace-abc").click().run()
        self.assertEqual(tracer.of("score"), [(("trace-abc", "user_says_correct", 0), {})])
        self.assertEqual(len(fakes.answer_calls), 1)

    def test_tracing_off_shows_disabled_buttons_with_the_hint(self):
        at, fakes = self.start(tracing.NullTracer(), make_result=answered_result)  # trace_id None
        buttons = self.feedback_buttons(at)
        self.assertEqual([b.label for b in buttons], ["Yes", "No"])
        self.assertTrue(all(b.disabled for b in buttons))
        self.assertIn("tracing off", texts(at))

    def test_declined_result_gets_the_buttons_but_no_rows_result_does_not(self):
        def declined(question):
            return answer.AnswerResult(question=question, status="declined_model",
                                       message="The model declined: no forecast data", trace_id="trace-abc")
        at, _ = self.start(RecordingTracer(), make_result=declined)
        self.assertEqual(len(self.feedback_buttons(at)), 2)

        def no_rows(question):
            return dataclasses.replace(no_rows_result(question), trace_id="trace-abc")
        at, _ = self.start(RecordingTracer(), make_result=no_rows)
        self.assertEqual(self.feedback_buttons(at), [])

    def test_session_id_is_one_uuid_per_tab_and_the_tracer_is_passed_in(self):
        tracer = RecordingTracer()
        at, fakes = self.start(tracer)
        sid = fakes.answer_kwargs[0]["session_id"]
        self.assertEqual(str(uuid.UUID(sid, version=4)), sid)
        self.assertIs(fakes.answer_kwargs[0]["tracer"], tracer)
        self.assertIs(fakes.summary_kwargs[0]["tracer"], tracer)
        next(b for b in at.button if b.label == "Ask").click().run()  # a second question in the same tab
        self.assertEqual(fakes.answer_kwargs[1]["session_id"], sid)

    def test_behind_the_scenes_shows_tracing_status_and_trace_id(self):
        at, _ = self.start(RecordingTracer())
        page = texts(at)
        self.assertIn("tracing on. Trace id: trace-abc", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
