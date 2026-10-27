"""
Compares an agent's SQL result against the gold result for one question.

See the per-step comments below for the reasoning — this mirrors the design
reviewed and approved before implementation.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from executor import QueryError, run_query
from loader import Question

_THOUSANDS_RE = re.compile(r"(?<=\d)[,\s](?=\d)")


@dataclass
class ComparisonResult:
    question_id: str
    tier: int
    passed: bool
    reason: str  # short diagnosis: "ok" / "row count mismatch: ..." / "cell mismatch at ..." / etc.


def compare(question: Question, agent_sql: Optional[str]) -> ComparisonResult:
    # STEP 0 — Tier 0 short-circuit. Passing means the agent declined to
    # answer; any SQL text at all (even SQL that returns 0) is a fail.
    if question.is_tier0:
        if agent_sql:
            return ComparisonResult(
                question.id, question.tier, False,
                "tier 0: agent returned SQL when it should have declined",
            )
        return ComparisonResult(question.id, question.tier, True, "ok (declined, as expected)")

    # STEP 1 — Run gold_sql for real. Let QueryError propagate: a broken
    # gold_sql is a grader/gold-set bug, not something to score as an agent
    # failure.
    gold_rows = run_query(question.gold_sql)

    # STEP 2 — Run agent_sql. Missing SQL or a QueryError here are both
    # legitimate fails to score.
    if not agent_sql:
        return ComparisonResult(question.id, question.tier, False, "agent returned no SQL")

    try:
        agent_rows = run_query(agent_sql)
    except QueryError as exc:
        return ComparisonResult(question.id, question.tier, False, f"agent SQL error: {exc}")

    # STEP 3 — Row count check first (cheap shape check).
    if len(gold_rows) != len(agent_rows):
        return ComparisonResult(
            question.id, question.tier, False,
            f"row count mismatch: gold={len(gold_rows)} agent={len(agent_rows)}",
        )

    # STEP 4 — Order handling. Sort both sides unless order is part of the
    # answer, then compare index-aligned either way.
    if question.reihenfolge_relevant:
        gold_ordered, agent_ordered = gold_rows, agent_rows
    else:
        gold_ordered = sorted(gold_rows, key=_sort_key)
        agent_ordered = sorted(agent_rows, key=_sort_key)

    # STEP 5 — Cell-by-cell, by column position.
    for row_idx, (gold_row, agent_row) in enumerate(zip(gold_ordered, agent_ordered)):
        if len(gold_row) != len(agent_row):
            return ComparisonResult(
                question.id, question.tier, False,
                f"column count mismatch at row {row_idx}: gold={len(gold_row)} agent={len(agent_row)}",
            )
        for col_idx, (gold_val, agent_val) in enumerate(zip(gold_row, agent_row)):
            ok, reason = _cells_match(gold_val, agent_val, question.toleranz)
            if not ok:
                return ComparisonResult(
                    question.id, question.tier, False,
                    f"cell mismatch row {row_idx} col {col_idx}: {reason}",
                )

    # STEP 6 — Everything matched.
    return ComparisonResult(question.id, question.tier, True, "ok")


def _sort_key(row: tuple) -> tuple:
    """NULL-safe sort key: None always sorts first, consistently per column,
    so mixed None/non-None values in a column never raise a comparison error."""
    return tuple((0, "") if v is None else (1, v) for v in row)


def _strip_thousands(s: str) -> str:
    """'2 023' / '2,023' -> '2023'. Only reachable if the agent's own SQL
    formats a numeric cell as text (e.g. via to_char) — see O5."""
    return _THOUSANDS_RE.sub("", s)


def _cells_match(gold_val, agent_val, toleranz: float) -> tuple[bool, str]:
    # NULL vs NULL matches; NULL vs anything else fails outright (rule 6 —
    # the Kernenergie trap this benchmark is partly built around).
    if gold_val is None or agent_val is None:
        if gold_val is None and agent_val is None:
            return True, ""
        return False, f"NULL vs non-NULL (gold={gold_val!r} agent={agent_val!r})"

    if isinstance(gold_val, (int, float, Decimal)):
        agent_num = agent_val
        if isinstance(agent_num, str):
            try:
                agent_num = _strip_thousands(agent_num)
            except TypeError:
                return False, f"expected numeric, agent returned {agent_val!r}"
        try:
            agent_num = float(agent_num)
            gold_num = float(gold_val)
        except (TypeError, ValueError):
            return False, f"could not compare numerically: gold={gold_val!r} agent={agent_val!r}"
        if abs(agent_num - gold_num) <= toleranz * max(abs(gold_num), 1):
            return True, ""
        return False, f"numeric mismatch: gold={gold_num} agent={agent_num} (toleranz={toleranz})"

    if isinstance(gold_val, (datetime, date)):
        agent_dt = agent_val
        if isinstance(agent_dt, str):
            try:
                agent_dt = datetime.fromisoformat(agent_dt)
            except ValueError:
                return False, f"expected date/timestamp, agent returned {agent_val!r}"
        gold_cmp = gold_val
        if isinstance(gold_cmp, date) and not isinstance(gold_cmp, datetime):
            gold_cmp = datetime(gold_cmp.year, gold_cmp.month, gold_cmp.day)
        if isinstance(agent_dt, date) and not isinstance(agent_dt, datetime):
            agent_dt = datetime(agent_dt.year, agent_dt.month, agent_dt.day)
        if gold_cmp == agent_dt:
            return True, ""
        return False, f"datetime mismatch: gold={gold_val!r} agent={agent_val!r}"

    # Text: exact match only. These are schema literals ('Wind Onshore',
    # 'Photovoltaik', ...), not free text — no case-folding, no trimming.
    if gold_val == agent_val:
        return True, ""
    return False, f"text mismatch: gold={gold_val!r} agent={agent_val!r}"
