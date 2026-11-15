"""Tests for app/charts.py (D44, step 3c). Pure function: no database, no API."""

import sys
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from charts import pick_chart  # noqa: E402

D = Decimal
MONTHS = [(datetime(2025, m, 1), D(100 * m)) for m in range(1, 13)]


class TestPickChart(unittest.TestCase):
    def test_metric(self):
        self.assertEqual(pick_chart(["total"], [(D("9056373.39"),)]), ("metric", {"label": "total", "value": D("9056373.39")}))
        self.assertEqual(pick_chart(["n"], [(0,)])[0], "metric")
        self.assertEqual(pick_chart(["x"], [(1.5,)])[0], "metric")

    def test_not_a_metric(self):
        self.assertEqual(pick_chart(["x"], [(None,)])[0], "none")
        self.assertEqual(pick_chart(["x"], [("text",)])[0], "none")
        self.assertEqual(pick_chart(["x"], [(True,)])[0], "none")
        self.assertEqual(pick_chart(["a", "b"], [(1, 2)])[0], "none")          # 1 row, 2 columns
        self.assertEqual(pick_chart(["x"], [(1,), (2,)])[0], "none")            # 2 rows, 1 column

    def test_line_for_dates(self):
        kind, d = pick_chart(["month", "mwh"], MONTHS)
        self.assertEqual((kind, d["x"], d["y"], d["x_index"], d["y_indexes"]), ("line", "month", ["mwh"], 0, [1]))

    def test_line_with_date_objects_and_three_rows(self):
        rows = [(date(2025, 1, d), D(d)) for d in (1, 2, 3)]
        self.assertEqual(pick_chart(["day", "v"], rows)[0], "line")

    def test_line_uses_up_to_five_numeric_columns(self):
        rows = [(datetime(2025, 1, d), 1, 2, 3, 4, 5, 6, "txt") for d in (1, 2, 3)]
        kind, d = pick_chart(list("abcdefgh"), rows)
        self.assertEqual(kind, "line")
        self.assertEqual(d["y"], ["b", "c", "d", "e", "f"])
        self.assertEqual(d["y_indexes"], [1, 2, 3, 4, 5])

    def test_line_skips_text_and_all_null_columns(self):
        rows = [(datetime(2025, 1, d), "x", None, D(d)) for d in (1, 2, 3)]
        kind, d = pick_chart(["t", "label", "empty", "v"], rows)
        self.assertEqual((kind, d["y"], d["y_indexes"]), ("line", ["v"], [3]))

    def test_two_date_rows_is_none(self):
        self.assertEqual(pick_chart(["month", "mwh"], MONTHS[:2])[0], "none")

    def test_dates_without_a_numeric_column_is_none(self):
        self.assertEqual(pick_chart(["t", "label"], [(datetime(2025, 1, d), "x") for d in (1, 2, 3)])[0], "none")

    def test_all_null_numeric_column_is_none(self):
        rows = [(datetime(2025, 1, d), None) for d in (1, 2, 3)]
        self.assertEqual(pick_chart(["t", "v"], rows)[0], "none")
        rows = [("a", None), ("b", None)]
        self.assertEqual(pick_chart(["k", "v"], rows)[0], "none")

    def test_bar_for_text_labels(self):
        rows = [("Wind Onshore", D(5)), ("Photovoltaik", D(3)), ("Erdgas", D(1))]
        kind, d = pick_chart(["quelle", "mwh"], rows)
        self.assertEqual((kind, d["x"], d["y"], d["x_index"], d["y_index"]), ("bar", "quelle", "mwh", 0, 1))

    def test_bar_for_integer_buckets(self):
        rows = [(h, D(h)) for h in range(24)]
        self.assertEqual(pick_chart(["hour", "avg"], rows)[0], "none")           # 24 > 20 rows
        self.assertEqual(pick_chart(["hour", "avg"], rows[:20])[0], "bar")
        rows = [(m, D(m)) for m in range(1, 13)]
        self.assertEqual(pick_chart(["month", "avg"], rows)[0], "bar")

    def test_bar_uses_only_the_first_numeric_column(self):
        rows = [("a", 1, 2), ("b", 3, 4)]
        kind, d = pick_chart(["k", "v1", "v2"], rows)
        self.assertEqual((kind, d["y"]), ("bar", "v1"))

    def test_bar_row_limits(self):
        label_rows = lambda n: [(f"k{i}", i) for i in range(n)]
        self.assertEqual(pick_chart(["k", "v"], label_rows(1))[0], "none")
        self.assertEqual(pick_chart(["k", "v"], label_rows(2))[0], "bar")
        self.assertEqual(pick_chart(["k", "v"], label_rows(20))[0], "bar")
        self.assertEqual(pick_chart(["k", "v"], label_rows(21))[0], "none")

    def test_bar_needs_a_numeric_second_column(self):
        self.assertEqual(pick_chart(["k", "v"], [("a", "x"), ("b", "y")])[0], "none")
        self.assertEqual(pick_chart(["k"], [("a",), ("b",)])[0], "none")

    def test_other_shapes_are_none(self):
        self.assertEqual(pick_chart(["a", "b"], [])[0], "none")
        self.assertEqual(pick_chart([], [])[0], "none")
        self.assertEqual(pick_chart(["k", "v"], [(None, 1), ("b", 2)])[0], "none")   # a NULL label
        self.assertEqual(pick_chart(["k", "v"], [(D("1.5"), 1), (D("2.5"), 2)])[0], "none")  # decimal labels
        self.assertEqual(pick_chart(["k", "v"], [(True, 1), (False, 2)])[0], "none")

    def test_rows_are_never_resorted(self):
        rows = [("c", D(1)), ("a", D(9)), ("b", D(5))]
        original = list(rows)
        pick_chart(["k", "v"], rows)
        self.assertEqual(rows, original)
        rows = [(datetime(2025, 1, 3), 1), (datetime(2025, 1, 1), 2), (datetime(2025, 1, 2), 3)]
        original = list(rows)
        pick_chart(["t", "v"], rows)
        self.assertEqual(rows, original)  # the function neither sorts nor reports a sorted copy


if __name__ == "__main__":
    unittest.main(verbosity=2)
