"""
Offline tests for grader/answer_comparator.py and grader/answer_columns.yaml (D42). No API call.
Gold results come from the real read-only database (grader_ro).

Run from the grader folder:  python -m unittest discover -s tests -v
"""

import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from answer_comparator import (answer_compare, answer_match, literal_label_columns,
                               load_answer_columns, match_label)
from executor import run_query_with_columns
from loader import load_questions
from _db import needs_db  # noqa: E402  (D46: skipped only when SKIP_DB_TESTS=1)

QUESTIONS = {q.id: q for q in load_questions()}
ENTRIES = load_answer_columns()
_CACHE: dict = {}


def gold(qid):
    """(columns, rows) of the gold query, run once."""
    if qid not in _CACHE:
        _CACHE[qid] = run_query_with_columns(QUESTIONS[qid].gold_sql)
    return _CACHE[qid]


def match(qid, agent_cols, agent_rows):
    q = QUESTIONS[qid]
    g_cols, g_rows = gold(qid)
    return answer_match(agent_cols, agent_rows, g_cols, g_rows, ENTRIES[qid], q.reihenfolge_relevant, q.toleranz)


def project(qid, keep, rename=None):
    """Gold result restricted to the named columns, optionally under other names."""
    cols, rows = gold(qid)
    idx = [cols.index(c) for c in keep]
    names = [(rename or {}).get(c, c) for c in keep]
    return names, [tuple(r[i] for i in idx) for r in rows]


class TestYaml(unittest.TestCase):
    def test_one_entry_per_gold_item_with_sql(self):
        with_sql = {q.id for q in QUESTIONS.values() if q.gold_sql}
        self.assertEqual(set(ENTRIES), with_sql)
        self.assertEqual(len(ENTRIES), 76)

    @needs_db
    def test_columns_exist_in_the_gold_result(self):
        for qid, e in ENTRIES.items():
            cols = gold(qid)[0]
            lists = [e["required"]] + list(e.get("alternatives") or [])
            for lst in lists:
                self.assertTrue(set(lst) <= set(cols), (qid, lst, cols))
            for c in e.get("label_only") or []:
                self.assertIn(c, e["required"])

    def test_review_change_t4_04(self):
        self.assertEqual(ENTRIES["t4_04"]["alternatives"], [["stunden"], ["beginn", "ende"]])
        self.assertEqual(ENTRIES["t4_02"]["alternatives"], [["stunden"], ["beginn", "ende"]])

    def test_label_only_columns_come_from_the_gold_sql(self):
        for qid, e in ENTRIES.items():
            self.assertEqual(e.get("label_only") or [], literal_label_columns(QUESTIONS[qid].gold_sql), qid)
        self.assertEqual({q: e["label_only"] for q, e in ENTRIES.items() if e.get("label_only")},
                         {"t2_15": ["kategorie"], "t3_08": ["typ"], "t3_11": ["gruppe"]})


class TestGoldAgainstItself(unittest.TestCase):
    @needs_db
    def test_every_gold_result_passes_against_itself(self):
        passed = 0
        for qid in ENTRIES:
            cols, rows = gold(qid)
            res = match(qid, list(cols), [tuple(r) for r in rows])
            self.assertTrue(res.passed, (qid, res.reason))
            passed += 1
        self.assertEqual(passed, 76)
        print(f"\n[gold vs itself] {passed}/76 pass")


class TestAnswerMatch(unittest.TestCase):
    @needs_db
    def test_one_required_column_is_enough_t2_06(self):
        cols, rows = project("t2_06", ["preiszone"])
        res = match("t2_06", cols, rows)
        self.assertTrue(res.passed, res.reason)
        self.assertEqual(res.used, "required")

    @needs_db
    def test_english_names_and_different_column_order(self):
        cols, rows = project("t2_04", ["mwh", "monat"], rename={"mwh": "total_generation", "monat": "month"})
        res = match("t2_04", cols, rows)
        self.assertTrue(res.passed, res.reason)
        self.assertEqual(res.assignment, {"monat": "month", "mwh": "total_generation"})

    @needs_db
    def test_half_answer_t3_12_only_the_date_fails(self):
        cols, rows = project("t3_12", ["tag"])
        res = match("t3_12", cols, rows)
        self.assertFalse(res.passed)

    @needs_db
    def test_right_columns_wrong_values_fail(self):
        cols, rows = project("t2_04", ["monat", "mwh"])
        rows = [list(r) for r in rows]
        rows[3][1] = rows[3][1] * 2
        res = match("t2_04", cols, [tuple(r) for r in rows])
        self.assertFalse(res.passed)

    @needs_db
    def test_wrong_label_values_fail(self):
        cols, rows = project("t2_02", ["energietraeger", "mwh"])
        rows = [("Kohle?",) + r[1:] if i == 0 else r for i, r in enumerate(rows)]
        self.assertFalse(match("t2_02", cols, rows).passed)

    @needs_db
    def test_one_row_too_many_or_too_few_fails(self):
        cols, rows = project("t2_04", ["monat", "mwh"])
        self.assertFalse(match("t2_04", cols, rows + [rows[0]]).passed)
        self.assertFalse(match("t2_04", cols, rows[:-1]).passed)
        res = match("t2_04", cols, rows[:-1])
        self.assertIn("row count", res.reason)

    @needs_db
    def test_ranking_with_two_rows_swapped(self):
        # t2_02: reihenfolge_relevant true -> the swap fails
        self.assertTrue(QUESTIONS["t2_02"].reihenfolge_relevant)
        cols, rows = project("t2_02", ["energietraeger", "mwh"])
        swapped = list(rows)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.assertFalse(match("t2_02", cols, swapped).passed)
        self.assertTrue(match("t2_02", cols, rows).passed)
        # t2_04: reihenfolge_relevant false -> the same swap passes
        self.assertFalse(QUESTIONS["t2_04"].reihenfolge_relevant)
        cols, rows = project("t2_04", ["monat", "mwh"])
        swapped = list(rows)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.assertTrue(match("t2_04", cols, swapped).passed)

    # ---- label_only: the label must MEAN the gold label (D43)

    def test_reviewers_case_swapped_weekday_weekend_fails(self):
        # gold: weekday = 100, weekend = 200; agent: weekend = 100, weekday = 200  -> swapped meaning
        entry = ENTRIES["t3_08"]
        gold_cols, gold_rows = ["typ", "eur_mwh"], [("Werktag", Decimal("100")), ("Wochenende", Decimal("200"))]
        swapped = answer_match(["day_type", "price"], [("Weekend", Decimal("100")), ("Weekday", Decimal("200"))],
                               gold_cols, gold_rows, entry, True, 0.005)
        right = answer_match(["day_type", "price"], [("Weekday", Decimal("100")), ("Weekend", Decimal("200"))],
                             gold_cols, gold_rows, entry, True, 0.005)
        self.assertFalse(swapped.passed)
        self.assertTrue(right.passed, right.reason)
        # also with the order not relevant
        swapped_unordered = answer_match(["day_type", "price"], [("Weekend", Decimal("100")), ("Weekday", Decimal("200"))],
                                         gold_cols, gold_rows, entry, False, 0.005)
        self.assertFalse(swapped_unordered.passed)

    @needs_db
    def test_english_labels_with_the_right_numbers_pass(self):
        # t3_08 on the real gold numbers
        cols, rows = project("t3_08", ["typ", "eur_mwh"])
        english = [("Weekday" if r[0] == "Werktag" else "Weekend", r[1]) for r in rows]
        self.assertTrue(match("t3_08", ["kind", "price"], english).passed)
        # t3_11
        cols, rows = project("t3_11", ["gruppe", "eur_mwh"])
        english = [("Above 5000 MWh" if r[0] == "viel Solar" else "5000 MWh or below", r[1]) for r in rows]
        res = match("t3_11", ["group", "price"], english)
        self.assertTrue(res.passed, res.reason)
        # t2_15
        cols, rows = project("t2_15", ["kategorie", "mwh"])
        english = [("Renewable" if r[0] == "Erneuerbar" else "Conventional", r[1]) for r in rows]
        res = match("t2_15", ["category", "total"], english)
        self.assertTrue(res.passed, res.reason)

    @needs_db
    def test_swapped_labels_fail_on_the_real_gold_numbers(self):
        for qid, col, val, a, b in (("t3_08", "typ", "eur_mwh", "Weekday", "Weekend"),
                                    ("t3_11", "gruppe", "eur_mwh", "Above 5000 MWh", "5000 MWh or below"),
                                    ("t2_15", "kategorie", "mwh", "Renewable", "Conventional")):
            cols, rows = project(qid, [col, val])
            first_label = rows[0][0]
            swapped = [(b if r[0] == first_label else a, r[1]) for r in rows]
            self.assertFalse(match(qid, ["x", "y"], swapped).passed, qid)

    @needs_db
    def test_german_labels_and_symbols_pass(self):
        cols, rows = project("t3_11", ["gruppe", "eur_mwh"])
        for hi, lo in (("viel Solar", "wenig Solar"), ("> 5000", "<= 5000"), ("über 5000 MWh", "höchstens 5000 MWh"),
                       ("High solar", "Low solar"), ("more than 5000", "not above 5000")):
            labelled = [(hi if r[0] == "viel Solar" else lo, r[1]) for r in rows]
            res = match("t3_11", ["g", "p"], labelled)
            self.assertTrue(res.passed, (hi, lo, res.reason))

    @needs_db
    def test_a_label_matching_neither_gold_label_fails(self):
        cols, rows = project("t3_08", ["typ", "eur_mwh"])
        odd = [("Tuesday" if r[0] == "Werktag" else "Holiday", r[1]) for r in rows]
        res = match("t3_08", ["kind", "price"], odd)
        self.assertFalse(res.passed)
        self.assertIn("matches no gold label", res.reason)

    @needs_db
    def test_a_label_matching_both_gold_labels_fails(self):
        cols, rows = project("t3_08", ["typ", "eur_mwh"])
        both = [("weekday and weekend", r[1]) for r in rows]
        res = match("t3_08", ["kind", "price"], both)
        self.assertFalse(res.passed)
        self.assertIn("more than one gold label", res.reason)

    @needs_db
    def test_two_gold_groups_given_one_label_fail(self):
        cols, rows = project("t3_11", ["gruppe", "eur_mwh"])
        same = [("above 5000", r[1]) for r in rows]
        self.assertFalse(match("t3_11", ["g", "p"], same).passed)

    def test_longer_phrases_and_negations_are_read_first(self):
        meanings = ENTRIES["t3_11"]["label_meanings"]["gruppe"]
        for text, want in (("above", "viel Solar"), ("Above 5000 MWh", "viel Solar"), ("not above", "wenig Solar"),
                           ("5000 MWh or below", "wenig Solar"), ("below", "wenig Solar"), ("not above 5000", "wenig Solar"),
                           ("no more than 5000", "wenig Solar"), ("more than 5000", "viel Solar"),
                           ("  VIEL Solar  ", "viel Solar"), ("<= 5000", "wenig Solar"), ("< 5000", "wenig Solar"),
                           ("> 5000", "viel Solar"), ("the rest", "wenig Solar")):
            self.assertEqual(match_label(text, meanings), (want, "ok"), text)
        for text in ("something", "5000", ""):
            self.assertEqual(match_label(text, meanings)[1], "none", text)
        non_renewable = ENTRIES["t2_15"]["label_meanings"]["kategorie"]
        self.assertEqual(match_label("Non-renewable", non_renewable), ("Konventionell", "ok"))
        self.assertEqual(match_label("renewables", non_renewable), ("Erneuerbar", "ok"))
        self.assertEqual(match_label("Ökostrom", non_renewable), ("Erneuerbar", "ok"))
        weekdays = ENTRIES["t3_08"]["label_meanings"]["typ"]
        self.assertEqual(match_label("non-weekend", weekdays), ("Werktag", "ok"))
        self.assertEqual(match_label("Mon-Fri", weekdays), ("Werktag", "ok"))
        self.assertEqual(match_label("Saturday and Sunday", weekdays), ("Wochenende", "ok"))

    def test_whole_words_only(self):
        meanings = ENTRIES["t3_11"]["label_meanings"]["gruppe"]
        self.assertEqual(match_label("overall", meanings)[1], "none")      # "over" inside a longer word
        self.assertEqual(match_label("brother", meanings)[1], "none")      # "other" inside a longer word

    @needs_db
    def test_a_numeric_column_is_not_a_label(self):
        # the old rule accepted any column that grouped the rows the same way; now a count cannot be a label
        cols, rows = project("t3_11", ["gruppe", "eur_mwh"])
        numbers_as_labels = [(10 + i, r[1]) for i, r in enumerate(rows)]
        self.assertFalse(match("t3_11", ["n", "price"], numbers_as_labels).passed)

    @needs_db
    def test_label_meanings_cover_every_gold_label(self):
        for qid, entry in ENTRIES.items():
            for col in entry.get("label_only") or []:
                meanings = entry["label_meanings"][col]
                gold_labels = {r[0] for r in project(qid, [col])[1]}
                self.assertEqual(set(meanings), gold_labels, qid)
                for label in gold_labels:                       # each gold label means itself, and only itself
                    self.assertEqual(match_label(label, meanings), (label, "ok"), (qid, label))
                for label, kws in meanings.items():             # keywords are lowercase and not shared
                    self.assertTrue(all(k == k.lower() for k in kws), (qid, label))
                all_kws = [k for kws in meanings.values() for k in kws]
                self.assertEqual(len(all_kws), len(set(all_kws)), (qid, "a keyword belongs to two labels"))

    def test_label_only_without_meanings_is_refused(self):
        entry = {"required": ["g", "v"], "alternatives": [], "label_only": ["g"]}
        with self.assertRaises(ValueError):
            answer_match(["x", "y"], [("a", 1)], ["g", "v"], [("a", 1)], entry, False, 0.005)

    @needs_db
    def test_extra_agent_column_passes(self):
        cols, rows = project("t2_04", ["monat", "mwh"])
        extra = [r + ("extra",) for r in rows]
        res = match("t2_04", cols + ["note"], extra)
        self.assertTrue(res.passed, res.reason)
        self.assertEqual(res.assignment, {"monat": "monat", "mwh": "mwh"})

    @needs_db
    def test_alternative_satisfied_but_not_required_t3_06(self):
        cols, rows = project("t3_06", ["mwh_2024", "mwh_2025", "veraenderung_prozent"])
        res = match("t3_06", cols, rows)
        self.assertTrue(res.passed, res.reason)
        self.assertEqual(res.used, "alternative 1")
        # required itself is also fine
        cols, rows = project("t3_06", ["differenz_mwh", "veraenderung_prozent"])
        self.assertEqual(match("t3_06", cols, rows).used, "required")
        # the percent alone is not enough
        cols, rows = project("t3_06", ["veraenderung_prozent"])
        self.assertFalse(match("t3_06", cols, rows).passed)

    @needs_db
    def test_t4_04_period_alternative(self):
        cols, rows = project("t4_04", ["beginn", "ende"])
        res = match("t4_04", cols, rows)
        self.assertTrue(res.passed, res.reason)
        self.assertEqual(res.used, "alternative 2")

    @needs_db
    def test_type_mismatch_month_number_vs_date(self):
        # as in the strict comparator: a month as a number is not a month as a date
        cols, rows = project("t2_04", ["monat", "mwh"])
        as_numbers = [(r[0].month, r[1]) for r in rows]
        self.assertFalse(match("t2_04", cols, as_numbers).passed)

    @needs_db
    def test_columns_matched_by_values_not_names(self):
        # the agent calls its value column "monat" and its month column "mwh": still matched by values
        cols, rows = project("t2_04", ["monat", "mwh"])
        res = match("t2_04", ["mwh", "monat"], rows)
        self.assertTrue(res.passed, res.reason)

    def test_tolerance_is_the_strict_one(self):
        entry = {"required": ["v"], "alternatives": []}
        ok = answer_match(["v"], [(Decimal("100.4"),)], ["v"], [(Decimal("100"),)], entry, False, 0.005)
        bad = answer_match(["v"], [(Decimal("101"),)], ["v"], [(Decimal("100"),)], entry, False, 0.005)
        self.assertTrue(ok.passed)
        self.assertFalse(bad.passed)

    @needs_db
    def test_agent_with_too_few_columns_fails(self):
        cols, rows = project("t2_04", ["monat"])
        res = match("t2_04", cols, rows)
        self.assertFalse(res.passed)

    def test_unorderable_mixed_types_do_not_crash(self):
        entry = {"required": ["v"], "alternatives": []}
        res = answer_match(["v"], [("x",), (1,)], ["v"], [(1,), (2,)], entry, False, 0.005)
        self.assertFalse(res.passed)


class TestAnswerCompareOneQuestion(unittest.TestCase):
    def test_tier_0_is_graded_like_the_strict_grader(self):
        q = next(x for x in QUESTIONS.values() if x.is_tier0)
        self.assertTrue(answer_compare(q, None, None).passed)
        self.assertTrue(answer_compare(q, "", None).passed)
        self.assertFalse(answer_compare(q, "SELECT 1", None).passed)

    @needs_db
    def test_answer_compare_with_a_sql(self):
        q = QUESTIONS["t2_06"]
        res = answer_compare(q, "SELECT preiszone FROM preise GROUP BY preiszone HAVING COUNT(preis_eur_mwh) > 0 "
                                "ORDER BY AVG(preis_eur_mwh) DESC LIMIT 1", ENTRIES["t2_06"])
        self.assertTrue(res.passed, res.reason)

    @needs_db
    def test_broken_sql_and_no_sql_fail(self):
        q = QUESTIONS["t2_06"]
        self.assertFalse(answer_compare(q, "SELECT nope FROM preise", ENTRIES["t2_06"]).passed)
        self.assertFalse(answer_compare(q, None, ENTRIES["t2_06"]).passed)


if __name__ == "__main__":
    unittest.main()
