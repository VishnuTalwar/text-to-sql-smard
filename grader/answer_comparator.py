"""
Answer-correctness comparator (D42), the second score next to the strict one (comparator.py, D19).

The strict comparator demands every gold column. This one demands only the *required answer
columns* of grader/answer_columns.yaml (or one listed alternative):

  * the agent result must have the same number of rows as the gold result;
  * every needed gold column is matched to one agent column by its VALUES, not by its name
    (every one-to-one assignment is tried; extra agent columns are allowed and ignored);
  * the projected tables are compared as ordered lists if reihenfolge_relevant is true, otherwise
    as multisets (sorted, then aligned, exactly as the strict comparator does it);
  * cell comparison and tolerance are the strict comparator's own (_cells_match, _sort_key are
    imported from comparator.py, not copied): types are compared as there, so a month as a number
    does not equal a month as a date;
  * label_only columns (labels written as string literals in the gold SQL, e.g. CASE ... THEN
    'viel Solar') only have to group the rows the same way: the same agent value must always
    correspond to the same gold value and vice versa (a one-to-one renaming), aligned with the
    other needed columns.

Tier 0 (no gold SQL) is graded exactly as the strict grader does it.

Known limits: a computed column that is not a gold column does not count; rows that tie on all
non-label needed columns are aligned by label text, so a label_only column with ties could
misalign; the number of column assignments tried is capped (MAX_ASSIGNMENTS).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import sqlglot
import yaml
from sqlglot import exp

from comparator import ComparisonResult, _cells_match, _sort_key, compare
from executor import QueryError, run_query_with_columns
from loader import Question

ANSWER_COLUMNS_PATH = Path(__file__).resolve().parent / "answer_columns.yaml"
MAX_ASSIGNMENTS = 5000


@dataclass
class AnswerResult:
    passed: bool
    reason: str                                    # "ok ..." or why it failed
    assignment: dict = field(default_factory=dict)  # gold column -> agent column name (when passed)
    used: Optional[str] = None                     # "required" or "alternative <n>" (when passed)


# ------------------------------------------------------------------ the YAML

def load_answer_columns(path: Path = ANSWER_COLUMNS_PATH) -> dict[str, dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["items"]}


def literal_label_columns(gold_sql: str) -> list[str]:
    """Result columns of the gold query whose values can only be string literals written in the
    query: a plain 'text' or a CASE whose every result (and ELSE) is a literal. From the SQL only."""
    def literal_only(e) -> bool:
        while isinstance(e, (exp.Paren, exp.Alias)):
            e = e.this
        if isinstance(e, exp.Cast):
            return literal_only(e.this)
        if isinstance(e, exp.Literal):
            return e.is_string
        if isinstance(e, exp.Case):
            results = [i.args["true"] for i in e.args.get("ifs", [])]
            if e.args.get("default") is not None:
                results.append(e.args["default"])
            return bool(results) and all(literal_only(r) for r in results)
        return False

    tree = sqlglot.parse_one(gold_sql, read="postgres")
    select = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
    return [p.alias_or_name for p in select.expressions if literal_only(p)]


# ------------------------------------------------------------------ matching

def _sorted_rows(rows: list[tuple], idxs: list[int]) -> list[tuple]:
    """Sort rows by the given columns with the strict comparator's key; mixed types that cannot
    be ordered fall back to a text key (such columns will not match anyway)."""
    try:
        return sorted(rows, key=lambda r: _sort_key(tuple(r[i] for i in idxs)))
    except TypeError:
        return sorted(rows, key=lambda r: tuple((0, "") if r[i] is None else (1, str(r[i])) for i in idxs))


def _hashable(v):
    try:
        hash(v)
        return v
    except TypeError:
        return repr(v)


def _pattern(values: list, ordered: bool):
    """Shape of a label column, independent of the label text: for an ordered table the sequence of
    first-occurrence numbers, otherwise the sorted group sizes."""
    if ordered:
        seen: dict = {}
        return tuple(seen.setdefault(_hashable(v), len(seen)) for v in values)
    counts: dict = {}
    for v in values:
        counts[_hashable(v)] = counts.get(_hashable(v), 0) + 1
    return tuple(sorted(counts.values()))


def _column_compatible(g_vals: list, a_vals: list, is_label: bool, ordered: bool, tol: float) -> bool:
    """Necessary condition for a gold column to be matched to an agent column (cheap pre-filter)."""
    if is_label:
        return _pattern(g_vals, ordered) == _pattern(a_vals, ordered)
    if not ordered:
        g_vals = [r[0] for r in _sorted_rows([(v,) for v in g_vals], [0])]
        a_vals = [r[0] for r in _sorted_rows([(v,) for v in a_vals], [0])]
    return all(_cells_match(g, a, tol)[0] for g, a in zip(g_vals, a_vals))


def _joint_match(gold_rows, agent_rows, g_idx, a_idx, label_flags, g_names, ordered, tol) -> tuple[bool, str]:
    """Compare the projected tables. g_idx/a_idx: the assigned columns, in the same order."""
    pos = list(range(len(g_idx)))
    nonlabel = [k for k in pos if not label_flags[k]]
    labels = [k for k in pos if label_flags[k]]
    g_proj = [tuple(r[i] for i in g_idx) for r in gold_rows]
    a_proj = [tuple(r[i] for i in a_idx) for r in agent_rows]
    if not ordered:
        order = nonlabel + labels
        g_proj = _sorted_rows(g_proj, order)
        a_proj = _sorted_rows(a_proj, order)
    g2a: dict = {}
    a2g: dict = {}
    for n, (gr, ar) in enumerate(zip(g_proj, a_proj)):
        for k in nonlabel:
            ok, why = _cells_match(gr[k], ar[k], tol)
            if not ok:
                return False, f"row {n} column {g_names[k]}: {why}"
        for k in labels:
            g, a = _hashable(gr[k]), _hashable(ar[k])
            if g2a.setdefault(g, a) != a or a2g.setdefault(a, g) != g:
                return False, (f"row {n} label column {g_names[k]}: labels are not a consistent "
                               f"one-to-one renaming (gold {gr[k]!r} vs agent {ar[k]!r})")
    return True, "ok"


def _try_needed(needed: list[str], label_only: set, agent_cols, agent_rows, gold_cols, gold_rows,
                ordered: bool, tol: float) -> tuple[bool, str, dict]:
    missing = [c for c in needed if c not in gold_cols]
    if missing:
        raise ValueError(f"answer_columns.yaml names columns that the gold result does not have: {missing}")
    if len(agent_cols) < len(needed):
        return False, f"agent returned {len(agent_cols)} columns, {len(needed)} needed ({', '.join(needed)})", {}
    g_idx = [gold_cols.index(c) for c in needed]
    flags = [c in label_only for c in needed]
    a_columns = [[r[j] for r in agent_rows] for j in range(len(agent_cols))]
    candidates = []
    for gi, flag, name in zip(g_idx, flags, needed):
        g_vals = [r[gi] for r in gold_rows]
        cand = [j for j in range(len(agent_cols))
                if _column_compatible(g_vals, a_columns[j], flag, ordered, tol)]
        if not cand:
            return False, f"no agent column has the values of {name}", {}
        candidates.append(cand)

    tried = 0
    last = "no assignment of the needed columns matched jointly"

    def assignments(i, used):
        if i == len(needed):
            yield []
            return
        for j in candidates[i]:
            if j not in used:
                for rest in assignments(i + 1, used | {j}):
                    yield [j] + rest

    for a_idx in assignments(0, frozenset()):
        tried += 1
        if tried > MAX_ASSIGNMENTS:
            return False, f"gave up after {MAX_ASSIGNMENTS} column assignments", {}
        ok, why = _joint_match(gold_rows, agent_rows, g_idx, a_idx, flags, needed, ordered, tol)
        if ok:
            return True, "ok", {g: agent_cols[j] for g, j in zip(needed, a_idx)}
        last = why
    if tried == 0:
        shown = "; ".join(f"{n} -> {[agent_cols[j] for j in c]}" for n, c in zip(needed, candidates))
        return False, f"no one-to-one assignment of agent columns to the needed columns (candidates: {shown})", {}
    return False, last, {}


def answer_match(agent_cols: list, agent_rows: list, gold_cols: list, gold_rows: list, entry: dict,
                 reihenfolge_relevant: bool, toleranz: float) -> AnswerResult:
    """Does the agent result contain the required answer columns (or one alternative) with the
    right values? See the module text."""
    if len(agent_rows) != len(gold_rows):
        return AnswerResult(False, f"row count mismatch: gold={len(gold_rows)} agent={len(agent_rows)}")
    label_only = set(entry.get("label_only") or [])
    options = [("required", list(entry["required"]))]
    options += [(f"alternative {n}", list(alt)) for n, alt in enumerate(entry.get("alternatives") or [], 1)]
    failures = []
    for name, needed in options:
        ok, why, assignment = _try_needed(needed, label_only, agent_cols, agent_rows, gold_cols, gold_rows,
                                          reihenfolge_relevant, toleranz)
        if ok:
            return AnswerResult(True, f"ok ({name}: {', '.join(needed)})", assignment, name)
        failures.append(f"{name} [{', '.join(needed)}]: {why}")
    return AnswerResult(False, "; ".join(failures))


# ------------------------------------------------------------------ one question

def answer_compare(question: Question, agent_sql: Optional[str], entry: Optional[dict],
                   run: Callable = run_query_with_columns) -> ComparisonResult:
    """Grade one answer with the answer comparator; same ComparisonResult as the strict compare().
    Tier 0 is graded by the strict comparator itself (declined or not). run(sql) -> (columns, rows)
    can be replaced (the re-grade passes a cache)."""
    if question.is_tier0:
        return compare(question, agent_sql)
    gold_cols, gold_rows = run(question.gold_sql)  # a broken gold query propagates, as in compare()
    if not agent_sql:
        return ComparisonResult(question.id, question.tier, False, "agent returned no SQL")
    try:
        agent_cols, agent_rows = run(agent_sql)
    except QueryError as exc:
        return ComparisonResult(question.id, question.tier, False, f"agent SQL error: {exc}")
    res = answer_match(agent_cols, agent_rows, gold_cols, gold_rows, entry,
                       question.reihenfolge_relevant, question.toleranz)
    return ComparisonResult(question.id, question.tier, res.passed, res.reason)
