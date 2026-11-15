"""
One cell formatter for everything the user sees (D44): the result table on the screen and the
table the summary model reads. Keeping one function means the summary can only copy numbers
exactly as the screen shows them.

  integers          1,263,744
  other numbers     9,056,373.39   -12.50   (Decimal or float, 2 decimals, half up)
  datetime          2025-07-01 00:00   (the time is always shown, also at 00:00)
  date              2025-07-01
  None              "" (empty)
  everything else   str(value)
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal


def format_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):  # bool is an int in Python; show True/False
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, (Decimal, float)):
        try:
            d = value if isinstance(value, Decimal) else Decimal(repr(value))
            if not d.is_finite():
                return str(value)
            d = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return str(value)
        if d == 0:
            d = abs(d)  # no "-0.00"
        return f"{d:,.2f}"
    if isinstance(value, datetime):  # before date: a datetime is also a date
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def format_table(columns, rows) -> list[list[str]]:
    """The rows as lists of strings, one string per cell. The column names are not included."""
    return [[format_cell(v) for v in row] for row in rows]
