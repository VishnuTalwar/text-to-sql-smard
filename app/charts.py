"""
Which chart to draw for a result (D44, step 3c). A pure function: no Streamlit, no database.

  pick_chart(columns, rows) -> (kind, details)

  "metric"  exactly 1 row and 1 column, a number                      details: {"label", "value"}
  "line"    first column is a date/datetime, at least 3 rows, at least one other numeric column
                                                                      details: {"x", "x_index", "y": [names], "y_indexes": [...]}  (up to 5)
  "bar"     first column is text or a whole number (hour, month number, weekday), 2 to 20 rows,
            second column numeric                                     details: {"x", "x_index", "y", "y_index"}
  "none"    anything else                                             details: {}

The rows are never re-sorted: the order is the SQL's order (rankings depend on it). A numeric
column that is all NULL does not count as numeric.
"""

from datetime import date
from decimal import Decimal

MAX_LINE_SERIES = 5
BAR_MIN_ROWS, BAR_MAX_ROWS = 2, 20
LINE_MIN_ROWS = 3

NONE = ("none", {})


def _is_number(v) -> bool:
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) and v == v  # v == v: not NaN


def _is_numeric_column(values) -> bool:
    """Every non-NULL value is a number and at least one value is not NULL."""
    present = [v for v in values if v is not None]
    return bool(present) and all(_is_number(v) for v in present)


def pick_chart(columns, rows) -> tuple[str, dict]:
    rows = list(rows)
    n_cols = len(columns)
    if not rows or n_cols == 0 or any(len(r) != n_cols for r in rows):
        return NONE
    cols = [[r[i] for r in rows] for i in range(n_cols)]

    if len(rows) == 1 and n_cols == 1:
        if _is_number(rows[0][0]):
            return "metric", {"label": columns[0], "value": rows[0][0]}
        return NONE

    first = cols[0]
    if any(v is None for v in first):
        return NONE

    if all(isinstance(v, date) for v in first):  # datetime is a date too
        if len(rows) < LINE_MIN_ROWS:
            return NONE
        y = [i for i in range(1, n_cols) if _is_numeric_column(cols[i])][:MAX_LINE_SERIES]
        if not y:
            return NONE
        return "line", {"x": columns[0], "x_index": 0, "y": [columns[i] for i in y], "y_indexes": y}

    is_label = all(isinstance(v, str) for v in first) or all(
        isinstance(v, int) and not isinstance(v, bool) for v in first)
    if is_label and BAR_MIN_ROWS <= len(rows) <= BAR_MAX_ROWS and n_cols >= 2 and _is_numeric_column(cols[1]):
        return "bar", {"x": columns[0], "x_index": 0, "y": columns[1], "y_index": 1}
    return NONE
