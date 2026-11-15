"""Tests for app/format.py (D44, part 2). No database, no API."""

import sys
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from format import format_cell, format_table, to_csv  # noqa: E402


class TestFormatCell(unittest.TestCase):
    def test_integers(self):
        self.assertEqual(format_cell(1263744), "1,263,744")
        self.assertEqual(format_cell(0), "0")
        self.assertEqual(format_cell(999), "999")
        self.assertEqual(format_cell(-1234567), "-1,234,567")

    def test_decimal_two_places(self):
        self.assertEqual(format_cell(Decimal("9056373.39")), "9,056,373.39")
        self.assertEqual(format_cell(Decimal("5")), "5.00")
        self.assertEqual(format_cell(Decimal("0.5")), "0.50")

    def test_negative_numbers(self):
        self.assertEqual(format_cell(Decimal("-12.5")), "-12.50")
        self.assertEqual(format_cell(-12.5), "-12.50")
        self.assertEqual(format_cell(Decimal("-1234.567")), "-1,234.57")
        self.assertEqual(format_cell(Decimal("-0.001")), "0.00")  # no "-0.00"

    def test_float(self):
        self.assertEqual(format_cell(1234.5), "1,234.50")
        self.assertEqual(format_cell(0.1 + 0.2), "0.30")

    def test_avg_numeric_with_many_decimals(self):
        self.assertEqual(format_cell(Decimal("4521.123456789012345678")), "4,521.12")
        self.assertEqual(format_cell(Decimal("33.3333333333333333")), "33.33")
        self.assertEqual(format_cell(Decimal("2.675")), "2.68")      # half up, not half even
        self.assertEqual(format_cell(Decimal("0.125")), "0.13")
        self.assertEqual(format_cell(Decimal("1234567.999999")), "1,234,568.00")

    def test_non_finite_numbers(self):
        self.assertEqual(format_cell(float("nan")), "nan")
        self.assertEqual(format_cell(Decimal("Infinity")), "Infinity")

    def test_datetime_always_with_time(self):
        self.assertEqual(format_cell(datetime(2025, 7, 1, 13, 45, 59)), "2025-07-01 13:45")
        self.assertEqual(format_cell(datetime(2025, 7, 1, 0, 0)), "2025-07-01 00:00")

    def test_date(self):
        self.assertEqual(format_cell(date(2025, 7, 1)), "2025-07-01")

    def test_none_is_empty(self):
        self.assertEqual(format_cell(None), "")

    def test_everything_else_is_str(self):
        self.assertEqual(format_cell("Wind Onshore"), "Wind Onshore")
        self.assertEqual(format_cell(True), "True")
        self.assertEqual(format_cell(""), "")


class TestFormatTable(unittest.TestCase):
    def test_table(self):
        rows = [(datetime(2025, 7, 1), Decimal("9056373.391"), 12, None, "x"),
                (date(2025, 7, 2), -1.5, 1000, "a", None)]
        self.assertEqual(format_table(["a", "b", "c", "d", "e"], rows),
                         [["2025-07-01 00:00", "9,056,373.39", "12", "", "x"],
                          ["2025-07-02", "-1.50", "1,000", "a", ""]])

    def test_empty(self):
        self.assertEqual(format_table(["a"], []), [])


class TestToCsv(unittest.TestCase):
    def test_raw_values_not_formatted(self):
        rows = [(datetime(2025, 7, 1), Decimal("9056373.391"), 1263744, None, "Wind, Onshore")]
        text = to_csv(["t (x)", "v", "n", "d", "name"], rows)
        self.assertEqual(text, 't (x),v,n,d,name\n2025-07-01 00:00:00,9056373.391,1263744,,"Wind, Onshore"\n')

    def test_header_only(self):
        self.assertEqual(to_csv(["a", "b"], []), "a,b\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
