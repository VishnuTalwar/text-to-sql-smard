"""
Date finder for the decline review (R3) and the empty-result fact. Not wired into the
loop yet; agent_loop.py is unchanged.

  find_periods_in_text(reason)  dates and periods named in a NO_QUERY reason
  find_periods_in_sql(sql)      periods the SQL asks for through conditions on zeitpunkt
  rows_in_period(conn, s, e)    rows per table for zeitpunkt >= s and < e
  decline_review_decision(...)  fires if a decline claims a period is missing but the
                                database has rows for every period named
  empty_fact_decision(...)      fires if an empty result comes from a period with no rows

Periods are half-open (start, end) pairs of datetimes. A year alone is the whole year, a
month the whole month, a day that day. Years outside 2023 to 2026 are not recognised
(the data runs from 2023-06-01 to 2026-06-01), so such a claim never fires the review.

All counting uses the read-only role through get_connection() (same account as
executor.py). Nothing here calls the API.
"""

import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import sqlglot
from sqlglot import exp

TABLES = ("erzeugung", "verbrauch", "preise")

OPEN_ENDED_WORDS = ("after", "before", "since", "until", "from",
                    "nach", "vor", "seit", "bis", "ab")
_OPEN_ENDED_RE = re.compile(r"\b(" + "|".join(OPEN_ENDED_WORDS) + r")\b", re.IGNORECASE)

MONTHS = {
    # English
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
    # German (the ones that differ from English)
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "mrz": 3, "mai": 5, "juni": 6,
    "juli": 7, "oktober": 10, "okt": 10, "dezember": 12, "dez": 12,
}
_LETTER = "A-Za-zÄÖÜäöüß"
_MONTH = (r"(?<![" + _LETTER + r"])(" + "|".join(sorted(MONTHS, key=len, reverse=True)) +
          r")\.?(?![" + _LETTER + r"])")
_YEAR = r"(?<!\d)(202[3-6])(?!\d)"
_DAY_SUFFIX = r"(?:st|nd|rd|th)?"

_ISO_DATE = re.compile(_YEAR + r"-(\d{2})-(\d{2})(?!\d)")
_DAY_MONTH_YEAR = re.compile(r"(?<!\d)(\d{1,2})" + _DAY_SUFFIX + r"\.?\s+(?:of\s+)?" + _MONTH + r",?\s+" + _YEAR,
                             re.IGNORECASE)
_MONTH_DAY_YEAR = re.compile(_MONTH + r"\s+(\d{1,2})" + _DAY_SUFFIX + r",?\s+" + _YEAR, re.IGNORECASE)
_MONTH_YEAR = re.compile(_MONTH + r",?\s+" + _YEAR, re.IGNORECASE)
_ISO_MONTH = re.compile(_YEAR + r"-(\d{2})(?!\d|-)")
_YEAR_ONLY = re.compile(_YEAR)


def _month_start(y: int, m: int) -> datetime:
    return datetime(y, m, 1)


def _next_month(y: int, m: int) -> datetime:
    return datetime(y + (m == 12), 1 if m == 12 else m + 1, 1)


def _day(y: int, m: int, d: int):
    try:
        start = datetime(y, m, d)
    except ValueError:
        return None
    return (start, start + timedelta(days=1))


def find_periods_in_text(reason: str) -> tuple[list[tuple[datetime, datetime]], bool]:
    """(periods, open_ended). open_ended is True if the text contains one of the words
    after, before, since, until, from, nach, vor, seit, bis, ab (whole words, any case)."""
    open_ended = bool(_OPEN_ENDED_RE.search(reason))
    text = reason
    found: list[tuple[datetime, datetime]] = []

    def take(pattern, build):
        nonlocal text
        for m in list(pattern.finditer(text)):
            period = build(m)
            if period is not None:
                found.append(period)
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)  # do not read these dates again

    take(_ISO_DATE, lambda m: _day(int(m[1]), int(m[2]), int(m[3])))
    take(_DAY_MONTH_YEAR, lambda m: _day(int(m[3]), MONTHS[m[2].lower()], int(m[1])))
    take(_MONTH_DAY_YEAR, lambda m: _day(int(m[3]), MONTHS[m[1].lower()], int(m[2])))
    take(_MONTH_YEAR, lambda m: (_month_start(int(m[2]), MONTHS[m[1].lower()]),
                                 _next_month(int(m[2]), MONTHS[m[1].lower()])))
    take(_ISO_MONTH, lambda m: (_month_start(int(m[1]), int(m[2])), _next_month(int(m[1]), int(m[2])))
         if 1 <= int(m[2]) <= 12 else None)
    take(_YEAR_ONLY, lambda m: (datetime(int(m[1]), 1, 1), datetime(int(m[1]) + 1, 1, 1)))
    return sorted(set(found)), open_ended


# ---------------------------------------------------------------- SQL

_MIN, _MAX = datetime(1, 1, 1), datetime(9999, 12, 31)
_MICRO = timedelta(microseconds=1)


def _literal_datetime(node):
    """(datetime, date_only) for a date/timestamp string literal, else None.
    Casts like '2025-01-01'::date, DATE '2025-01-01' and TIMESTAMP '...' are looked through."""
    while isinstance(node, (exp.Cast, exp.TryCast, exp.Paren)):
        node = node.this
    if not (isinstance(node, exp.Literal) and node.is_string):
        return None
    s = node.this.strip().replace("T", " ")
    for fmt, date_only in (("%Y-%m-%d", True), ("%Y-%m-%d %H:%M", False),
                           ("%Y-%m-%d %H:%M:%S", False), ("%Y-%m-%d %H:%M:%S.%f", False)):
        try:
            return datetime.strptime(s, fmt), date_only
        except ValueError:
            pass
    return None


def _zeitpunkt_side(node):
    """(is_zeitpunkt, cast_to_date) for one side of a comparison."""
    cast_date = False
    while isinstance(node, (exp.Cast, exp.TryCast, exp.Paren)):
        if isinstance(node, (exp.Cast, exp.TryCast)) and node.to is not None and \
                node.to.this == exp.DataType.Type.DATE:
            cast_date = True
        node = node.this
    if isinstance(node, exp.Column) and node.name.lower() == "zeitpunkt":
        return True, cast_date
    return False, False


def _bounds(op, lit, cast_date):
    """(lower, upper) half-open bounds one comparison puts on zeitpunkt."""
    dt, date_only = lit
    step = timedelta(days=1) if cast_date else _MICRO
    # with the column cast to a date, the literal stands for a whole day
    if op == "eq":
        return dt, dt + step
    if op == "ge":
        return dt, None
    if op == "gt":
        return dt + step, None
    if op == "lt":
        return None, dt
    if op == "le":
        return None, dt + step
    raise ValueError(op)


_FLIP = {"ge": "le", "gt": "lt", "le": "ge", "lt": "gt", "eq": "eq"}
_OPS = {exp.GTE: "ge", exp.GT: "gt", exp.LTE: "le", exp.LT: "lt", exp.EQ: "eq"}


def find_periods_in_sql(sql: str) -> list[tuple[datetime, datetime]]:
    """Periods asked for by conditions on zeitpunkt, one per SELECT: comparisons with
    date/timestamp literals (>=, >, <, <=, =, BETWEEN) and EXTRACT(YEAR/MONTH FROM
    zeitpunkt) = n (year and month combined if both appear). A missing lower or upper
    bound is open (year 1 / year 9999). Returns [] if nothing is found or the SQL does
    not parse."""
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return []
    if tree is None:
        return []
    scopes: dict[int, dict] = {}

    def scope(node):
        sel = node.find_ancestor(exp.Select)
        return scopes.setdefault(id(sel), {"lo": [], "hi": [], "year": None, "month": None})

    for node in tree.find_all(exp.Between):
        is_z, cast_date = _zeitpunkt_side(node.this)
        low, high = _literal_datetime(node.args.get("low")), _literal_datetime(node.args.get("high"))
        if is_z and low and high:
            sc = scope(node)
            sc["lo"].append(_bounds("ge", low, cast_date)[0])
            sc["hi"].append(_bounds("le", high, cast_date)[1])

    for node in tree.find_all(exp.Binary):
        op = _OPS.get(type(node))
        if op is None:
            continue
        left, right = node.this, node.expression
        # EXTRACT(YEAR|MONTH FROM zeitpunkt) = n
        for ext, num in ((left, right), (right, left)):
            if op == "eq" and isinstance(ext, exp.Extract) and isinstance(num, exp.Literal) and not num.is_string:
                is_z, _ = _zeitpunkt_side(ext.expression)
                unit = (ext.this.name if hasattr(ext.this, "name") else str(ext.this)).upper()
                if is_z and unit in ("YEAR", "MONTH"):
                    sc = scope(node)
                    sc["year" if unit == "YEAR" else "month"] = int(num.this)
        is_z, cast_date = _zeitpunkt_side(left)
        lit = _literal_datetime(right)
        use_op = op
        if not (is_z and lit):
            is_z, cast_date = _zeitpunkt_side(right)
            lit = _literal_datetime(left)
            use_op = _FLIP[op]
        if is_z and lit:
            lo, hi = _bounds(use_op, lit, cast_date)
            sc = scope(node)
            if lo is not None:
                sc["lo"].append(lo)
            if hi is not None:
                sc["hi"].append(hi)

    periods = []
    for sc in scopes.values():
        if sc["lo"] or sc["hi"]:
            periods.append((max(sc["lo"]) if sc["lo"] else _MIN, min(sc["hi"]) if sc["hi"] else _MAX))
        elif sc["year"] is not None:
            y, m = sc["year"], sc["month"]
            if m is not None and 1 <= m <= 12:
                periods.append((_month_start(y, m), _next_month(y, m)))
            elif m is None:
                periods.append((datetime(y, 1, 1), datetime(y + 1, 1, 1)))
    return sorted(set(p for p in periods if p[0] < p[1]))


# ---------------------------------------------------------------- database

def get_connection():
    """Connection with the read-only role, like executor.run_query (never the loader account)."""
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "smard"),
        user=os.environ["GRADER_DB_USER"],
        password=os.environ["GRADER_DB_PASSWORD"],
    )


def rows_in_period(conn, start: datetime, end: datetime) -> dict[str, int]:
    """Rows per table with zeitpunkt >= start and < end."""
    counts = {}
    with conn.cursor() as cur:
        for table in TABLES:  # fixed names, never user input
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE zeitpunkt >= %s AND zeitpunkt < %s", (start, end))
            counts[table] = cur.fetchone()[0]
    return counts


def _describe(conn, periods):
    return [{"start": s, "end": e, "rows": rows_in_period(conn, s, e)} for s, e in periods]


def decline_review_decision(reason: str, conn=None) -> dict:
    """Fires only if a period is found in the reason, the reason is not open-ended, and
    every period found has at least one row in some table."""
    own = conn is None
    conn = conn or get_connection()
    try:
        periods, open_ended = find_periods_in_text(reason)
        detail = _describe(conn, periods)
    finally:
        if own:
            conn.close()
    if not periods:
        why = "no period found"
    elif open_ended:
        why = "open-ended wording"
    elif not all(sum(d["rows"].values()) > 0 for d in detail):
        why = "a period has no rows (the claim is true)"
    else:
        why = "every period has rows"
    return {"fire": bool(periods) and not open_ended and all(sum(d["rows"].values()) > 0 for d in detail),
            "open_ended": open_ended, "periods": detail, "why": why}


def empty_fact_decision(sql: str, conn=None) -> dict:
    """Fires only if a period is found in the SQL and every table has 0 rows for every
    period found."""
    own = conn is None
    conn = conn or get_connection()
    try:
        periods = find_periods_in_sql(sql)
        detail = _describe(conn, periods)
    finally:
        if own:
            conn.close()
    fire = bool(periods) and all(sum(d["rows"].values()) == 0 for d in detail)
    return {"fire": fire, "periods": detail,
            "why": "no period found" if not periods else ("no rows in any table" if fire else "rows exist")}
