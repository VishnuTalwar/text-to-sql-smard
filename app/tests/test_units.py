"""Tests for app/units.py (D44, step 3c). Pure: no database, no API."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from units import header_names, unit_for_columns  # noqa: E402


class TestUnitForColumns(unittest.TestCase):
    def test_sum_of_mwh(self):
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) FROM erzeugung WHERE energietraeger = 'Wind Onshore'"), ["MWh"])

    def test_round_avg_price(self):
        self.assertEqual(unit_for_columns("SELECT ROUND(AVG(preis_eur_mwh), 2) FROM preise"), ["EUR/MWh"])

    def test_bare_columns_aggregates_and_aliases(self):
        sql = ("SELECT energietraeger, SUM(mwh) AS total, MAX(mwh) AS peak, MIN(mwh), AVG(mwh), mwh AS einzel "
               "FROM erzeugung GROUP BY 1, mwh")
        self.assertEqual(unit_for_columns(sql), [None, "MWh", "MWh", "MWh", "MWh", "MWh"])
        self.assertEqual(unit_for_columns("SELECT MIN(preis_eur_mwh) AS tief, preis_eur_mwh FROM preise"),
                         ["EUR/MWh", "EUR/MWh"])
        self.assertEqual(unit_for_columns("SELECT ROUND(SUM(mwh), 1) AS s FROM verbrauch"), ["MWh"])

    def test_the_unit_follows_the_expression_not_the_alias(self):
        self.assertEqual(unit_for_columns("SELECT COUNT(*) AS mwh FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) AS preis_eur_mwh FROM erzeugung"), ["MWh"])

    def test_count_has_no_unit(self):
        self.assertEqual(unit_for_columns("SELECT COUNT(*) FROM preise WHERE preis_eur_mwh < 0"), [None])
        self.assertEqual(unit_for_columns("SELECT COUNT(mwh) FROM erzeugung"), [None])

    def test_arithmetic_has_no_unit(self):
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) / 4 FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT AVG(mwh) * 4 AS mw FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT mwh + 1 FROM erzeugung"), [None])

    def test_share_in_percent_has_no_unit(self):
        sql = ("SELECT SUM(mwh) * 100.0 / SUM(SUM(mwh)) OVER () AS share FROM erzeugung")
        self.assertEqual(unit_for_columns(sql), [None])
        sql = ("SELECT SUM(mwh) * 100.0 / (SELECT SUM(mwh) FROM erzeugung) FROM erzeugung "
               "WHERE energietraeger = 'Erdgas'")
        self.assertEqual(unit_for_columns(sql), [None])

    def test_case_and_other_functions_have_no_unit(self):
        self.assertEqual(unit_for_columns("SELECT CASE WHEN mwh > 0 THEN mwh ELSE 0 END FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT COALESCE(SUM(mwh), 0) FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT ABS(mwh) FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) FILTER (WHERE mwh > 0) FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT SUM(DISTINCT mwh) FROM erzeugung"), [None])
        self.assertEqual(unit_for_columns("SELECT ROUND(AVG(mwh)::numeric, 2) FROM erzeugung"), [None])

    def test_value_from_a_cte_has_no_unit(self):
        sql = "WITH x AS (SELECT SUM(mwh) AS mwh FROM erzeugung) SELECT mwh FROM x"
        self.assertEqual(unit_for_columns(sql), [None])
        sql = "WITH x AS (SELECT mwh FROM erzeugung) SELECT SUM(mwh) FROM x"
        self.assertEqual(unit_for_columns(sql), [None])

    def test_value_from_a_subquery_has_no_unit(self):
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) FROM (SELECT mwh FROM erzeugung) t"), [None])
        sql = "SELECT SUM(mwh) FROM erzeugung e JOIN (SELECT 1 AS k) s ON TRUE"
        self.assertEqual(unit_for_columns(sql), [None])

    def test_a_cte_named_like_a_table_is_not_the_table(self):
        sql = "WITH erzeugung AS (SELECT 1 AS mwh) SELECT SUM(mwh) FROM erzeugung"
        self.assertEqual(unit_for_columns(sql), [None])

    def test_a_cte_that_is_not_used_does_not_matter(self):
        sql = "WITH x AS (SELECT 1) SELECT SUM(mwh) FROM erzeugung"
        self.assertEqual(unit_for_columns(sql), ["MWh"])

    def test_joins_of_real_tables(self):
        sql = ("SELECT AVG(p.preis_eur_mwh), SUM(e.mwh) FROM preise p JOIN erzeugung e ON p.zeitpunkt = e.zeitpunkt")
        self.assertEqual(unit_for_columns(sql), ["EUR/MWh", "MWh"])

    def test_trailing_semicolon_and_whitespace(self):
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) FROM erzeugung;"), ["MWh"])
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) FROM erzeugung;  \n"), ["MWh"])

    def test_select_star_cannot_be_listed(self):
        self.assertIsNone(unit_for_columns("SELECT * FROM erzeugung"))
        self.assertIsNone(unit_for_columns("SELECT e.* FROM erzeugung e"))
        self.assertIsNone(unit_for_columns("SELECT mwh, * FROM erzeugung"))

    def test_unparseable_or_not_a_select(self):
        self.assertIsNone(unit_for_columns("SELEC SUM(mwh FROM"))
        self.assertIsNone(unit_for_columns(""))
        self.assertIsNone(unit_for_columns("DELETE FROM preise"))
        self.assertIsNone(unit_for_columns("SELECT mwh FROM erzeugung UNION SELECT mwh FROM verbrauch"))

    def test_other_schema_is_not_the_table(self):
        self.assertEqual(unit_for_columns("SELECT SUM(mwh) FROM other.erzeugung"), [None])

    def test_one_entry_per_output_column(self):
        sql = "SELECT date_trunc('month', zeitpunkt) AS m, SUM(mwh) AS s FROM erzeugung GROUP BY 1 ORDER BY 1"
        self.assertEqual(unit_for_columns(sql), [None, "MWh"])


class TestHeaderNames(unittest.TestCase):
    def test_units_in_brackets(self):
        self.assertEqual(header_names(["monat", "mwh"], [None, "MWh"]), ["monat", "mwh (MWh)"])

    def test_no_units(self):
        self.assertEqual(header_names(["a", "b"], None), ["a", "b"])
        self.assertEqual(header_names(["a", "b"], [None, None]), ["a", "b"])

    def test_wrong_length_is_ignored(self):
        self.assertEqual(header_names(["a", "b"], ["MWh"]), ["a", "b"])

    def test_duplicates_are_made_unique(self):
        self.assertEqual(header_names(["x", "x", "x"], None), ["x", "x (2)", "x (3)"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
