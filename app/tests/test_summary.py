"""Tests for app/summary.py (D44, part 3). The model is a fake; no API call, no database."""

import sys
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import summary  # noqa: E402
from answer import AnswerResult  # noqa: E402
from summary import extract_numbers, number_check, summarize  # noqa: E402

D = Decimal


class FakeModel:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def __call__(self, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return {"raw_model_output": self.reply, "prompt_tokens": 200, "completion_tokens": 20,
                "latency_seconds": 0.1}


def result(question="What was the total in 2025?", columns=("total",), rows=((D("9056373.39"),), (D("8123456.78"),)),
           status="answered", row_count=None):
    return AnswerResult(question=question, status=status, message="", columns=list(columns),
                        rows=list(rows), row_count=len(rows) if row_count is None else row_count)


class TestExtractNumbers(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(extract_numbers("9,056,373.39 and 2025 and 0.25"), [D("9056373.39"), D(2025), D("0.25")])

    def test_leading_zeros(self):
        self.assertEqual(extract_numbers("07"), extract_numbers("7"))
        self.assertEqual(extract_numbers("07"), [D(7)])

    def test_iso_date_is_all_positive(self):
        self.assertEqual(extract_numbers("2025-07-01"), [D(2025), D(7), D(1)])
        self.assertEqual(extract_numbers("2025-07-01 00:00"), [D(2025), D(7), D(1), D(0), D(0)])

    def test_minus(self):
        self.assertEqual(extract_numbers("-12.50"), [D("-12.50")])
        self.assertEqual(extract_numbers("fell to −5"), [D(-5)])          # unicode minus
        self.assertEqual(extract_numbers("is -5.00."), [D("-5.00")])
        self.assertEqual(extract_numbers("5 - 3"), [D(5), D(3)])           # not directly before

    def test_percent_ignored(self):
        self.assertEqual(extract_numbers("12.5%"), [D("12.5")])

    def test_sentence_end_is_not_a_decimal(self):
        self.assertEqual(extract_numbers("The total was 5."), [D(5)])

    def test_no_numbers(self):
        self.assertEqual(extract_numbers("none here"), [])


class TestNumberCheck(unittest.TestCase):
    def test_ok_and_unknown(self):
        ok, unknown = number_check("It was 7 in 2025.", [["7"]], "In 2025?")
        self.assertTrue(ok)
        self.assertEqual(unknown, [])
        ok, unknown = number_check("It was 8 in 2025.", [["7"]], "In 2025?")
        self.assertFalse(ok)
        self.assertEqual(unknown, [D(8)])

    def test_column_names_count(self):
        self.assertTrue(number_check("Das Ergebnis für 2025 ist 3.", [["3"]], "Frage?", columns=["jahr_2025"])[0])

    def test_banned_word_is_reported(self):
        ok, unknown = number_check("It is twice as high.", [], "q")
        self.assertFalse(ok)
        self.assertEqual(unknown, ["twice"])

    def test_banned_words_whole_words_any_case(self):
        for text in ("About HALF of it", "Eine Hälfte davon", "dreimal so viel", "Nine sources", "Es sind zwölf",
                     "a Dozen", "Millionen", "Triple"):
            self.assertFalse(number_check(text, [], "q")[0], text)
        for text in ("Phone numbers", "Onshore wind", "Einheit stimmt", "tenant",
                     "ein Wert", "one source", "the quarter-hour price"):  # "ein", "one", "quarter" are not banned  # contain a banned word only as part
            self.assertTrue(number_check(text, [], "q")[0], text)


class TestSummarize(unittest.TestCase):
    def test_1_number_from_table_and_year_from_question(self):
        m = FakeModel("In 2025 the total was 9,056,373.39.")
        s = summarize(result(), model_caller=m)
        self.assertTrue(s.shown)
        self.assertIsNone(s.hidden_reason)
        self.assertEqual(s.text, "In 2025 the total was 9,056,373.39.")
        self.assertEqual(len(m.calls), 1)
        self.assertEqual((s.prompt_tokens, s.completion_tokens), (200, 20))
        self.assertAlmostEqual(s.cost_usd, (200 * 2.50 + 20 * 10.00) / 1e6, places=6)

    def test_2_invented_number(self):
        s = summarize(result(), model_caller=FakeModel("In 2025 the total was 9,056,373.39 across 17 sources."))
        self.assertFalse(s.shown)
        self.assertEqual(s.hidden_reason, "number_check")
        self.assertEqual(s.unknown_numbers, [D(17)])
        self.assertIsNone(s.text)
        self.assertEqual(s.prompt_tokens, 200)  # tokens of the call are still reported

    def test_3_rounded_number(self):
        s = summarize(result(), model_caller=FakeModel("In 2025 the total was 9.06 million."))
        self.assertFalse(s.shown)
        self.assertIn(s.hidden_reason, ("number_check", "banned_word"))
        s = summarize(result(), model_caller=FakeModel("In 2025 the total was about 9.06."))
        self.assertEqual(s.hidden_reason, "number_check")
        self.assertEqual(s.unknown_numbers, [D("9.06")])

    def test_4_date_in_words_matches_iso_cell(self):
        r = result(question="When was the peak?", columns=("zeitpunkt",), rows=[(datetime(2025, 7, 1, 0, 0),), (datetime(2025, 7, 2, 0, 0),)])
        s = summarize(r, model_caller=FakeModel("The peak was on 1 July 2025."))
        self.assertTrue(s.shown, s.unknown_numbers)

    def test_5_minus_sign(self):
        q = "What was the change?"
        s = summarize(result(q, ("change",), [(D("5"),), (D("7"),)]), model_caller=FakeModel("The change was -5.00."))
        self.assertFalse(s.shown)
        self.assertEqual(s.hidden_reason, "number_check")
        self.assertEqual(s.unknown_numbers, [D("-5.00")])
        s = summarize(result(q, ("change",), [(D("-5"),), (D("7"),)]), model_caller=FakeModel("The change was -5.00."))
        self.assertTrue(s.shown)

    def test_6_banned_word(self):
        s = summarize(result(), model_caller=FakeModel("It was twice as high as 9,056,373.39."))
        self.assertFalse(s.shown)
        self.assertEqual(s.hidden_reason, "banned_word")
        self.assertEqual(s.unknown_numbers, ["twice"])

    def test_7_too_long(self):
        s = summarize(result(), model_caller=FakeModel("It was 9,056,373.39. That is the total. It is for 2025."))
        self.assertEqual((s.shown, s.hidden_reason), (False, "too_long"))
        long_one = "The total was 9,056,373.39 " + " ".join(["and"] * 60) + "."
        s = summarize(result(), model_caller=FakeModel(long_one))
        self.assertEqual((s.shown, s.hidden_reason), (False, "too_long"))
        s = summarize(result(), model_caller=FakeModel("It was 9,056,373.39. That is the total."))  # 2 sentences: fine
        self.assertTrue(s.shown)

    def test_8_too_many_rows(self):
        m = FakeModel("It was 9,056,373.39.")
        s = summarize(result(row_count=51), model_caller=m)
        self.assertEqual((s.shown, s.hidden_reason, s.text), (False, "too_many_rows", None))
        self.assertEqual(m.calls, [])
        s = summarize(result(row_count=0, rows=[]), model_caller=m)
        self.assertEqual(s.hidden_reason, "too_many_rows")
        self.assertEqual(m.calls, [])
        self.assertEqual((s.prompt_tokens, s.completion_tokens, s.cost_usd), (0, 0, 0.0))
        # exactly 50 is allowed
        s = summarize(result(row_count=50), model_caller=m)
        self.assertEqual(len(m.calls), 1)

    def test_9_not_answered(self):
        for status in ("declined_model", "no_rows", "declined_system", "blocked", "error"):
            m = FakeModel("It was 9,056,373.39.")
            s = summarize(result(status=status), model_caller=m)
            self.assertEqual((s.shown, s.hidden_reason), (False, "not_answered"), status)
            self.assertEqual(m.calls, [], status)

    def test_10_model_error_never_crashes(self):
        s = summarize(result(), model_caller=FakeModel(error=RuntimeError("API down")))
        self.assertEqual((s.shown, s.hidden_reason, s.text), (False, "model_error", None))
        s = summarize(result(), model_caller=FakeModel(reply=None))
        self.assertEqual(s.hidden_reason, "model_error")
        s = summarize(result(), model_caller=FakeModel(reply="   "))
        self.assertEqual(s.hidden_reason, "model_error")

    def test_11_german(self):
        r = result(question="Wie hoch war die Erzeugung im Juli 2025?", columns=("summe_mwh",),
                   rows=[(D("9056373.39"),), (D("1.5"),)])
        s = summarize(r, model_caller=FakeModel("Die Erzeugung im Juli 2025 betrug 9,056,373.39."))
        self.assertTrue(s.shown, s.unknown_numbers)

    def test_12_quarter_hour_is_allowed(self):
        r = result(question="What was the highest price?", columns=("preis",), rows=[(D("512"),), (D("300"),)])
        s = summarize(r, model_caller=FakeModel("The highest quarter-hour price was 512.00."))
        self.assertTrue(s.shown, (s.hidden_reason, s.unknown_numbers))

    def test_13_german_article_ein_is_allowed(self):
        r = result(question="Wie hoch war die Erzeugung im Juli 2025?", columns=("summe_mwh",),
                   rows=[(D("9056373.39"),), (D("1.5"),)])
        s = summarize(r, model_caller=FakeModel(
            "Im Juli 2025 lag die Erzeugung bei 9,056,373.39 und ein Wert war negativ."))
        self.assertTrue(s.shown, (s.hidden_reason, s.unknown_numbers))

    def test_14_banned_word_from_the_question_is_allowed(self):
        r = result(question="How much solar in the first half of 2025?", columns=("mwh",),
                   rows=[(D("1234"),), (D("99"),)])
        s = summarize(r, model_caller=FakeModel("In the first half of 2025 solar produced 1,234.00."))
        self.assertTrue(s.shown, (s.hidden_reason, s.unknown_numbers))
        # the allowance is for that word only: another banned word still hides the sentence
        s = summarize(r, model_caller=FakeModel("In the first half of 2025 solar produced twice 1,234.00."))
        self.assertEqual((s.shown, s.hidden_reason, s.unknown_numbers), (False, "banned_word", ["twice"]))

    def test_15_twice_is_still_banned(self):
        r = result(question="How high were the prices?", columns=("preis",), rows=[(D("5"),), (D("6"),)])
        s = summarize(r, model_caller=FakeModel("Prices were twice as high as 5.00."))
        self.assertEqual((s.shown, s.hidden_reason, s.unknown_numbers), (False, "banned_word", ["twice"]))

    def test_single_value_gets_no_summary_and_no_model_call(self):
        m = FakeModel("The total in 2025 was 9,056,373.39.")
        s = summarize(result(rows=[(D("9056373.39"),)]), model_caller=m)
        self.assertEqual((s.shown, s.hidden_reason, s.text), (False, "single_value", None))
        self.assertEqual(m.calls, [])
        self.assertEqual((s.prompt_tokens, s.completion_tokens, s.cost_usd), (0, 0, 0.0))
        # one row with two columns, and two rows with one column, are not single values
        for cols, rows in ((("a", "b"), [(D("1"), D("2"))]), (("a",), [(D("1"),), (D("2"),)])):
            m = FakeModel("The values are 1.00 and 2.00 here.")
            s = summarize(result(columns=cols, rows=rows), model_caller=m)
            self.assertEqual(len(m.calls), 1, cols)

    def test_reply_under_4_words_is_hidden_as_too_short(self):
        r = result(question="What was the price?", columns=("price",), rows=[(D("10536110.75"),), (D("5"),)])
        s = summarize(r, model_caller=FakeModel("10,536,110.75"))  # only the number itself
        self.assertEqual((s.shown, s.hidden_reason, s.text), (False, "too_short", None))
        self.assertEqual(s.prompt_tokens, 200)  # the call happened and is still reported
        s = summarize(r, model_caller=FakeModel("The price was 10,536,110.75."))  # 4 words: fine
        self.assertTrue(s.shown)
        s = summarize(r, model_caller=FakeModel("The price: 10,536,110.75"))  # 3 words
        self.assertEqual(s.hidden_reason, "too_short")

    def test_normal_six_word_sentence_is_shown(self):
        r = result(question="What was the price?", columns=("price",), rows=[(D("10536110.75"),), (D("5"),)])
        s = summarize(r, model_caller=FakeModel("The highest price was 10,536,110.75 overall."))
        self.assertEqual((s.shown, s.text), (True, "The highest price was 10,536,110.75 overall."))

    def test_model_sees_only_question_columns_and_table(self):
        m = FakeModel("It was 9,056,373.39 in 2025.")
        summarize(result(), model_caller=m)
        content = m.calls[0][0]["content"]
        self.assertEqual(len(m.calls[0]), 1)
        self.assertTrue(content.startswith(summary.INSTRUCTIONS))
        self.assertIn("Question: What was the total in 2025?", content)
        self.assertTrue(content.endswith("total\n9,056,373.39\n8,123,456.78"))
        self.assertNotIn("SELECT", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
