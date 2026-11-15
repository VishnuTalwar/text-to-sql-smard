"""
Units for the output columns of the final SQL (D44, step 3c). Fails closed: a column gets a unit
only when it clearly comes from mwh (-> "MWh") or preis_eur_mwh (-> "EUR/MWh"); anything else
gets None, because no unit is better than a wrong unit.

  unit_for_columns(final_sql) -> list with one entry per output column (a unit string or None),
                                 or None when the columns cannot be listed at all (the SQL does not
                                 parse, is not one SELECT, or has SELECT *)

A unit is given for: the bare column, or SUM / AVG / MIN / MAX of the bare column, either one
optionally inside ROUND(..., n). Not for COUNT, arithmetic (/4, *100), CASE, other functions, window
functions, FILTER, DISTINCT inside the aggregate, or any column of a query whose FROM/JOIN is not
only the tables erzeugung, verbrauch, preise (a CTE or a subquery could change what a name means).
Only the outer SELECT is looked at.

  header_names(columns, units) -> "name (unit)" headers; equal headers get " (2)", " (3)", ... appended
"""

import logging

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

logging.getLogger("sqlglot").setLevel(logging.ERROR)

REAL_TABLES = frozenset({"erzeugung", "verbrauch", "preise"})
UNIT_OF_COLUMN = {"mwh": "MWh", "preis_eur_mwh": "EUR/MWh"}
_AGGREGATES = (exp.Sum, exp.Avg, exp.Min, exp.Max)


def _unit_of(node) -> str | None:
    if isinstance(node, exp.Round):
        return _unit_of(node.this)  # ROUND(<column or aggregate>, n); the digits do not matter
    if isinstance(node, _AGGREGATES):
        return _unit_of_column(node.this)
    return _unit_of_column(node)


def _unit_of_column(node) -> str | None:
    if isinstance(node, exp.Column) and not isinstance(node.this, exp.Star):
        return UNIT_OF_COLUMN.get(node.name.lower())
    return None


def _only_real_tables(select: exp.Select) -> bool:
    cte_names = {c.alias.lower() for c in select.args["with_"].expressions} if select.args.get("with_") else set()
    sources = []
    from_ = select.args.get("from_")
    if from_ is None:
        return False
    sources.append(from_.this)
    sources.extend(j.this for j in select.args.get("joins") or [])
    return all(isinstance(s, exp.Table) and isinstance(s.this, exp.Identifier)
               and s.name.lower() in REAL_TABLES and s.name.lower() not in cte_names
               and not s.args.get("db") and not s.args.get("catalog") for s in sources)


def unit_for_columns(final_sql: str) -> list[str | None] | None:
    try:
        tree = sqlglot.parse_one(final_sql, read="postgres")
    except (SqlglotError, ValueError, TypeError):
        return None
    if not isinstance(tree, exp.Select):  # a UNION or anything else: not looked at
        return None
    items = tree.expressions
    if not items or any(isinstance(e, exp.Star) or (isinstance(e, exp.Column) and isinstance(e.this, exp.Star))
                        for e in items):
        return None
    if not _only_real_tables(tree):
        return [None] * len(items)
    return [_unit_of(e.this if isinstance(e, exp.Alias) else e) for e in items]


def header_names(columns, units=None) -> list[str]:
    """"name (unit)" where a unit is known, the plain name otherwise; made unique."""
    units = list(units) if units and len(units) == len(columns) else [None] * len(columns)
    names, seen = [], {}
    for col, unit in zip(columns, units):
        name = f"{col} ({unit})" if unit else str(col)
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return names
