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

    def test_union_with_two_periods_is_unknown(self):
        sql = ("SELECT 1 FROM erzeugung WHERE zeitpunkt >= '2024-01-01' AND zeitpunkt < '2025-01-01' "
               "UNION ALL SELECT 2 FROM erzeugung WHERE zeitpunkt >= '2025-01-01' AND zeitpunkt < '2026-01-01'")
        self.assertEqual(df.find_periods_in_sql(sql), df.UNKNOWN)

    def test_cte_and_outer_select_with_the_same_period(self):
        sql = ("WITH j AS (SELECT zeitpunkt, mwh FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01') "
               "SELECT SUM(mwh) FROM j WHERE energietraeger IS NOT NULL")
        self.assertEqual(df.find_periods_in_sql(sql), [(D(2026, 7, 1), D(2026, 8, 1))])

    def test_cte_and_outer_select_with_different_periods_is_unknown(self):
        sql = ("WITH j AS (SELECT zeitpunkt, mwh FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01') "
               "SELECT SUM(mwh) FROM j WHERE zeitpunkt >= '2025-01-01' AND zeitpunkt < '2025-02-01'")
        self.assertEqual(df.find_periods_in_sql(sql), df.UNKNOWN)

    def test_zeitpunkt_outside_conditions_is_fine(self):
        sql = ("SELECT zeitpunkt, DATE_TRUNC('month', zeitpunkt) AS m, SUM(mwh) FROM erzeugung "
               "WHERE zeitpunkt >= '2025-01-01' AND zeitpunkt < '2026-01-01' GROUP BY zeitpunkt ORDER BY zeitpunkt")
        self.assertEqual(df.find_periods_in_sql(sql), [(D(2025, 1, 1), D(2026, 1, 1))])
        self.assertEqual(df.find_periods_in_sql("SELECT DATE_TRUNC('month', zeitpunkt), SUM(mwh) FROM erzeugung GROUP BY 1"), [])

    def test_qualified_column_and_flipped_comparison(self):
        sql = "SELECT 1 FROM erzeugung e WHERE '2026-07-01' <= e.zeitpunkt AND e.zeitpunkt < '2026-08-01'"
        self.assertEqual(df.find_periods_in_sql(sql), [(D(2026, 7, 1), D(2026, 8, 1))])

    def test_open_ended_bound_stays_supported(self):
        p = df.find_periods_in_sql("SELECT 1 FROM erzeugung WHERE zeitpunkt >= '2026-07-01'")
        self.assertEqual(p[0][0], D(2026, 7, 1))

    # ---- shapes that must give UNKNOWN (D40)

    def unknown(self, sql):
        self.assertEqual(df.find_periods_in_sql(sql), df.UNKNOWN, sql)

    def test_not_is_unknown(self):
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE NOT (zeitpunkt >= '2026-07-01')")
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE NOT (zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01')")
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE zeitpunkt NOT BETWEEN '2026-07-01' AND '2026-07-31'")

    def test_or_is_unknown(self):
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE zeitpunkt < '2024-01-01' OR zeitpunkt >= '2026-01-01'")
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE energietraeger = 'Erdgas' "
                     "AND (zeitpunkt >= '2026-07-01' OR zeitpunkt < '2024-01-01')")

    def test_case_is_unknown(self):
        self.unknown("SELECT SUM(CASE WHEN zeitpunkt >= '2026-07-01' THEN mwh END) FROM erzeugung")
        self.unknown("SELECT SUM(CASE WHEN zeitpunkt >= '2026-07-01' THEN mwh END) FROM erzeugung "
                     "WHERE zeitpunkt >= '2026-01-01' AND zeitpunkt < '2027-01-01'")

    def test_function_other_than_extract_is_unknown(self):
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE DATE_TRUNC('month', zeitpunkt) = '2026-07-01'")
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE TO_CHAR(zeitpunkt, 'YYYY-MM') = '2026-07'")
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE zeitpunkt + INTERVAL '1 day' >= '2026-07-01'")

    def test_having_only_is_unknown(self):
        self.unknown("SELECT energietraeger, SUM(mwh) FROM erzeugung GROUP BY energietraeger "
                     "HAVING MAX(zeitpunkt) >= '2026-07-01'")

    def test_join_on_is_unknown(self):
        self.unknown("SELECT 1 FROM erzeugung e JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt "
                     "WHERE e.zeitpunkt >= '2026-07-01' AND e.zeitpunkt < '2026-08-01'")
        self.unknown("SELECT 1 FROM erzeugung e JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt")

    def test_expression_subquery_is_unknown(self):
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE mwh > "
                     "(SELECT AVG(mwh) FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01')")
        self.unknown("SELECT SUM(mwh) FROM erzeugung WHERE NOT EXISTS "
                     "(SELECT 1 FROM verbrauch WHERE zeitpunkt >= '2026-07-01')")

    def test_unsupported_comparison_is_unknown(self):
        self.unknown("SELECT 1 FROM erzeugung WHERE zeitpunkt <> '2026-07-01'")
        self.unknown("SELECT 1 FROM erzeugung WHERE zeitpunkt IN ('2026-07-01', '2026-07-02')")
        self.unknown("SELECT 1 FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < NOW()")

    def test_month_without_year_and_contradictions_are_unknown(self):
        self.unknown("SELECT 1 FROM erzeugung WHERE EXTRACT(MONTH FROM zeitpunkt) = 7")
        self.unknown("SELECT 1 FROM erzeugung WHERE EXTRACT(YEAR FROM zeitpunkt) = 2025 AND EXTRACT(YEAR FROM zeitpunkt) = 2026")
        self.unknown("SELECT 1 FROM erzeugung WHERE zeitpunkt >= '2026-08-01' AND zeitpunkt < '2026-07-01'")

    def test_unparseable_sql_mentioning_zeitpunkt_is_unknown(self):
        self.unknown("SELECT FROM WHERE zeitpunkt >= ((( '2026-07-01'")

    def test_year_combined_with_a_bound(self):
        sql = "SELECT 1 FROM erzeugung WHERE EXTRACT(YEAR FROM zeitpunkt) = 2025 AND zeitpunkt >= '2025-06-01'"
        self.assertEqual(df.find_periods_in_sql(sql), [(D(2025, 6, 1), D(2026, 1, 1))])

    # ---- the u_08 SQL of R3b (three variants, runs 1 to 3): July 2026

    U08 = [
        "SELECT SUM(mwh) AS total_wind_generation\nFROM erzeugung\nWHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'\n"
        "AND energietraeger IN ('Wind Onshore', 'Wind Offshore');",
        "SELECT SUM(mwh) AS total_wind_generation\nFROM erzeugung\nWHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'\n"
        "AND energietraeger IN ('Wind Onshore', 'Wind Offshore');",
        "SELECT SUM(mwh) \nFROM erzeugung \nWHERE energietraeger IN ('Wind Onshore', 'Wind Offshore') \n"
        "AND zeitpunkt >= '2026-07-01' \nAND zeitpunkt < '2026-08-01';",
    ]

    def test_u08_variants_give_july_2026(self):
        for sql in self.U08:
            self.assertEqual(df.find_periods_in_sql(sql), [(D(2026, 7, 1), D(2026, 8, 1))], sql)


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

    def test_system_decline_still_fires_on_the_u08_sql(self):
        for sql in TestSqlPeriods.U08:
            r = df.empty_fact_decision(sql, self.conn)
            self.assertTrue(r["fire"], sql)
            self.assertFalse(r["unknown"])
            self.assertEqual((r["periods"][0]["start"], r["periods"][0]["end"]), (D(2026, 7, 1), D(2026, 8, 1)))

    def test_empty_fact_does_not_fire_when_the_period_is_unknown(self):
        # Every one of these would be read as "July 2026 onward" or "July 2026" by a naive finder.
        for sql in ["SELECT SUM(mwh) FROM erzeugung WHERE NOT (zeitpunkt >= '2026-07-01')",
                    "SELECT SUM(mwh) FROM erzeugung WHERE zeitpunkt < '2024-01-01' OR zeitpunkt >= '2026-07-01'",
                    "SELECT SUM(CASE WHEN zeitpunkt >= '2026-07-01' THEN mwh END) FROM erzeugung",
                    "SELECT SUM(mwh) FROM erzeugung WHERE DATE_TRUNC('month', zeitpunkt) = '2026-07-01'",
                    "SELECT energietraeger FROM erzeugung GROUP BY energietraeger HAVING MAX(zeitpunkt) >= '2026-07-01'"]:
            r = df.empty_fact_decision(sql, self.conn)
            self.assertFalse(r["fire"], sql)
            self.assertTrue(r["unknown"], sql)
            self.assertEqual(r["periods"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
