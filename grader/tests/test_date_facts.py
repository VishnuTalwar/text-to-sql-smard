"""
Tests for grader/date_facts.py (the date finder for R3). No API call; the row counts use
the real read-only database (data runs from 2023-06-01 to 2026-06-01 23:45).

Run from the grader folder:  python -m unittest discover -s tests -v
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import date_facts as df


def D(y, m, d):
    return datetime(y, m, d)


class TestTextPeriods(unittest.TestCase):
    def test_month_english(self):
        self.assertEqual(df.find_periods_in_text("The table does not contain data for February 2026."),
                         ([(D(2026, 2, 1), D(2026, 3, 1))], False))

    def test_year_alone(self):
        self.assertEqual(df.find_periods_in_text("Data for 2025 is missing."),
                         ([(D(2025, 1, 1), D(2026, 1, 1))], False))

    def test_german_months_full_and_short(self):
        for text, want in [("Daten für Dezember 2025 fehlen.", (D(2025, 12, 1), D(2026, 1, 1))),
                           ("Februar 2026 fehlt.", (D(2026, 2, 1), D(2026, 3, 1))),
                           ("Dez. 2025", (D(2025, 12, 1), D(2026, 1, 1))),
                           ("Dec 2025", (D(2025, 12, 1), D(2026, 1, 1))),
                           ("März 2026", (D(2026, 3, 1), D(2026, 4, 1))),
                           ("Mai 2025", (D(2025, 5, 1), D(2025, 6, 1)))]:
            self.assertEqual(df.find_periods_in_text(text)[0], [want], text)

    def test_days(self):
        day = (D(2025, 3, 3), D(2025, 3, 4))
        for text in ["3 March 2025", "March 3, 2025", "3rd of March 2025", "3. März 2025", "2025-03-03"]:
            self.assertEqual(df.find_periods_in_text(text)[0], [day], text)
        self.assertEqual(df.find_periods_in_text("1. Januar 2026")[0], [(D(2026, 1, 1), D(2026, 1, 2))])

    def test_a_day_is_not_also_read_as_month_or_year(self):
        self.assertEqual(len(df.find_periods_in_text("Data for 3 March 2025 is missing.")[0]), 1)

    def test_open_ended_words(self):
        for text in ["no data after 2024-01-30", "missing after January 2024", "daten seit 2025",
                     "Data until 2026", "not before March 2025", "nach Mai 2025", "ab 2025", "bis 2026", "since 2025"]:
            self.assertTrue(df.find_periods_in_text(text)[1], text)
        self.assertFalse(df.find_periods_in_text("Data for 2025 is missing.")[1])
        self.assertFalse(df.find_periods_in_text("Daten für Dezember 2025 fehlen.")[1])

    def test_whole_words_only(self):
        # "abc", "afterwards" style substrings must not count as open-ended words
        self.assertFalse(df.find_periods_in_text("Table abc has no row for 2025.")[1])

    def test_no_period(self):
        self.assertEqual(df.find_periods_in_text("The table does not contain information about the day of the week."),
                         ([], False))

    def test_years_outside_2023_2026_are_ignored(self):
        self.assertEqual(df.find_periods_in_text("No data for 2022 or 2027.")[0], [])


class TestSqlPeriods(unittest.TestCase):
    def test_range(self):
        sql = "SELECT SUM(mwh) FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'"
        self.assertEqual(df.find_periods_in_sql(sql), [(D(2026, 7, 1), D(2026, 8, 1))])

    def test_extract_year_and_month(self):
        self.assertEqual(df.find_periods_in_sql("SELECT 1 FROM erzeugung WHERE EXTRACT(YEAR FROM zeitpunkt) = 2025"),
                         [(D(2025, 1, 1), D(2026, 1, 1))])
        self.assertEqual(df.find_periods_in_sql(
            "SELECT 1 FROM erzeugung WHERE EXTRACT(YEAR FROM zeitpunkt) = 2025 AND EXTRACT(MONTH FROM zeitpunkt) = 6"),
            [(D(2025, 6, 1), D(2025, 7, 1))])

    def test_day_cast_and_between_and_casts(self):
        self.assertEqual(df.find_periods_in_sql("SELECT 1 FROM erzeugung WHERE zeitpunkt::date = '2025-06-15'"),
                         [(D(2025, 6, 15), D(2025, 6, 16))])
        self.assertEqual(df.find_periods_in_sql(
            "SELECT 1 FROM erzeugung WHERE zeitpunkt::date BETWEEN '2025-06-01' AND '2025-06-30'"),
            [(D(2025, 6, 1), D(2025, 7, 1))])
        self.assertEqual(df.find_periods_in_sql(
            "SELECT 1 FROM erzeugung WHERE zeitpunkt >= DATE '2026-07-01' AND zeitpunkt < '2026-08-01'::date"),
            [(D(2026, 7, 1), D(2026, 8, 1))])

    def test_no_zeitpunkt_condition(self):
        self.assertEqual(df.find_periods_in_sql("SELECT SUM(mwh) FROM erzeugung WHERE energietraeger = 'Erdgas'"), [])
        self.assertEqual(df.find_periods_in_sql("SELECT SUM(mwh) FROM erzeugung"), [])
        self.assertEqual(df.find_periods_in_sql("this is ((( not sql"), [])

    def test_one_period_per_select(self):
        sql = ("SELECT 1 FROM erzeugung WHERE zeitpunkt >= '2024-01-01' AND zeitpunkt < '2025-01-01' "
               "UNION ALL SELECT 2 FROM erzeugung WHERE zeitpunkt >= '2025-01-01' AND zeitpunkt < '2026-01-01'")
        self.assertEqual(df.find_periods_in_sql(sql), [(D(2024, 1, 1), D(2025, 1, 1)), (D(2025, 1, 1), D(2026, 1, 1))])


class TestDecisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = df.get_connection()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def review(self, reason):
        return df.decline_review_decision(reason, self.conn)

    def test_rows_in_period(self):
        c = df.rows_in_period(self.conn, D(2026, 7, 1), D(2026, 8, 1))
        self.assertEqual(c, {"erzeugung": 0, "verbrauch": 0, "preise": 0})
        c = df.rows_in_period(self.conn, D(2025, 6, 1), D(2025, 6, 2))
        self.assertTrue(all(n > 0 for n in c.values()), c)

    def test_review_fires_for_false_date_claims(self):
        r = self.review("The table does not contain data for February 2026.")
        self.assertTrue(r["fire"])
        self.assertEqual(r["periods"][0]["start"], D(2026, 2, 1))
        self.assertEqual(r["periods"][0]["end"], D(2026, 3, 1))
        self.assertGreater(sum(r["periods"][0]["rows"].values()), 0)
        r = self.review("Data for 2025 is missing.")
        self.assertTrue(r["fire"])
        self.assertEqual((r["periods"][0]["start"], r["periods"][0]["end"]), (D(2025, 1, 1), D(2026, 1, 1)))
        self.assertTrue(self.review("Daten für Dezember 2025 fehlen.")["fire"])

    def test_review_does_not_fire_when_open_ended(self):
        r = self.review("There is no data for nuclear power after 2024-01-30.")
        self.assertTrue(r["open_ended"])
        self.assertFalse(r["fire"])
        r = self.review("Nuclear power data is missing after January 2024.")
        self.assertTrue(r["open_ended"])
        self.assertFalse(r["fire"])

    def test_review_does_not_fire_when_the_claim_is_true(self):
        r = self.review("Data for July 2026 is missing.")
        self.assertFalse(r["fire"])
        self.assertEqual(sum(r["periods"][0]["rows"].values()), 0)

    def test_review_does_not_fire_without_a_period(self):
        r = self.review("The table does not contain information about the day of the week.")
        self.assertEqual(r["periods"], [])
        self.assertFalse(r["fire"])

    def test_review_needs_every_period_to_have_rows(self):
        self.assertFalse(self.review("No data for March 2025 or July 2026.")["fire"])

    def test_empty_fact_fires_for_a_period_without_rows(self):
        r = df.empty_fact_decision(
            "SELECT SUM(mwh) FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'", self.conn)
        self.assertTrue(r["fire"])
        self.assertEqual((r["periods"][0]["start"], r["periods"][0]["end"]), (D(2026, 7, 1), D(2026, 8, 1)))

    def test_empty_fact_does_not_fire_when_rows_exist(self):
        r = df.empty_fact_decision("SELECT SUM(mwh) FROM erzeugung WHERE EXTRACT(YEAR FROM zeitpunkt) = 2025", self.conn)
        self.assertFalse(r["fire"])
        self.assertEqual((r["periods"][0]["start"], r["periods"][0]["end"]), (D(2025, 1, 1), D(2026, 1, 1)))
        self.assertGreater(sum(r["periods"][0]["rows"].values()), 0)

    def test_empty_fact_without_a_period(self):
        r = df.empty_fact_decision("SELECT SUM(mwh) FROM erzeugung WHERE energietraeger = 'Erdgas'", self.conn)
        self.assertEqual(r["periods"], [])
        self.assertFalse(r["fire"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
