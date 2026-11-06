"""
Safe runner: four walls in front of every SQL query the agent writes (D41).

    safe_execute(sql, limits) -> SafeResult

  Wall 1  static check with sqlglot (postgres dialect), before the database is touched:
          exactly one statement, a SELECT (a WITH ... SELECT or a UNION of SELECTs is fine),
          no write or admin node anywhere in the tree (CTEs and subqueries included), only
          the tables erzeugung, verbrauch, preise (CTE names are allowed; this also blocks
          pg_catalog and information_schema), at least one of those tables is read, no
          function on the deny list.
  Wall 2  EXPLAIN (FORMAT JSON), no ANALYZE: blocked if the estimated total cost is above
          limits.max_plan_cost.
  Wall 3  runs as grader_ro in a READ ONLY transaction with statement_timeout = limits.timeout_ms.
          At most limits.max_rows + 1 rows are fetched (a server-side cursor and fetchmany,
          never fetchall); if more come back the result is blocked as "too_many_rows".
  Wall 4  every block is returned as a structured result (blocked=True, wall, reason, kind)
          instead of being raised.

What is NOT a block: a query that passes the walls and then fails in PostgreSQL (unknown
column, type error, ...) raises executor.QueryError exactly as executor.run_query does, so
the loop's error message is the same PostgreSQL message as before.

Gold queries do not use this module; they keep running through executor.run_query.

Limits live in one file, grader/limits.yaml (max_plan_cost, max_rows, timeout_ms), calibrated
on the gold queries: python safe_runner.py --calibrate.
"""

import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import psycopg2
import psycopg2.errors
import sqlglot
import yaml
from sqlglot import exp
from sqlglot.errors import SqlglotError

from executor import QueryError  # also loads .env

# sqlglot warns whenever it falls back to a generic Command (SET, DO, VACUUM, ...); those are blocked anyway.
logging.getLogger("sqlglot").setLevel(logging.ERROR)

GRADER_DIR = Path(__file__).resolve().parent
LIMITS_PATH = GRADER_DIR / "limits.yaml"

ALLOWED_TABLES = frozenset({"erzeugung", "verbrauch", "preise"})
ALLOWED_SCHEMAS = frozenset({"", "public"})

# Function-name deny list. A name is blocked if it equals an entry of DENY_FUNCTIONS or starts
# with an entry of DENY_PREFIXES. Everything that starts with pg_ is blocked (pg_sleep,
# pg_read_file, pg_ls_dir, pg_terminate_backend, ...). The query_to_xml family is on the list
# because it runs a SQL *string* on the server, which would walk around wall 1.
DENY_PREFIXES = ("pg_", "lo_", "dblink", "txid_", "query_to_xml", "table_to_xml",
                 "cursor_to_xml", "schema_to_xml", "database_to_xml")
DENY_FUNCTIONS = frozenset({"set_config", "current_setting", "lowrite", "loread",
                            "nextval", "setval", "currval"})

# Node types that mean a write, a change of settings, or any other non-SELECT statement.
_WRITE_NODE_NAMES = (
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "TruncateTable",
    "Grant", "Revoke", "Copy", "Set", "SetItem", "Into", "Lock", "Command", "Use", "Pragma",
    "Analyze", "Transaction", "Commit", "Rollback", "Refresh", "Declare", "Kill", "Show",
    "Describe", "Comment", "Execute", "LoadData", "Cache", "Uncache", "Attach", "Detach",
    "Export", "Install", "Summarize",
)
WRITE_NODES = tuple(getattr(exp, n) for n in _WRITE_NODE_NAMES if hasattr(exp, n))


@dataclass
class Limits:
    max_plan_cost: float
    max_rows: int
    timeout_ms: int


@dataclass
class SafeResult:
    blocked: bool
    wall: int | None = None        # 1, 2 or 3 when blocked
    reason: str | None = None      # short text, also what the model is told
    kind: str | None = None        # static | plan_cost | timeout | too_many_rows
    rows: list | None = None       # only when not blocked and the query was run
    plan_cost: float | None = None
    n_rows: int | None = None
    seconds: float | None = None   # wall 3 run time
    detail: dict = field(default_factory=dict)


def load_limits(path: Path = LIMITS_PATH) -> Limits:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Limits(max_plan_cost=float(data["max_plan_cost"]), max_rows=int(data["max_rows"]),
                  timeout_ms=int(data["timeout_ms"]))


# ------------------------------------------------------------------ wall 1

def _block(reason: str) -> SafeResult:
    return SafeResult(blocked=True, wall=1, reason=reason, kind="static")


def _function_names(tree: exp.Expression) -> set[str]:
    names = set()
    for node in tree.walk():
        if isinstance(node, exp.Anonymous):
            names.add(node.name.lower())
        elif isinstance(node, exp.Func):
            names.add(node.sql_name().lower())
    return names


def denied_function(name: str) -> bool:
    n = name.lower()
    return n in DENY_FUNCTIONS or n.startswith(DENY_PREFIXES)


def _parse_error_text(exc: SqlglotError) -> str:
    """Short, plain description of a parser error: what went wrong, near which text, which line."""
    errors = getattr(exc, "errors", None) or []
    if errors:
        e = errors[0]
        near = " ".join(str(e.get("highlight") or "").split())
        where = f' near "{near}"' if near else ""
        line = f", line {e['line']}" if e.get("line") else ""
        return f"{str(e.get('description') or 'syntax error').strip()}{where}{line}"
    return " ".join(str(exc).split())[:100]


def check_static(sql: str) -> SafeResult | None:
    """Wall 1. None if the query passes, otherwise the blocked result."""
    if not isinstance(sql, str) or not sql.strip():
        return _block("empty query")
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except SqlglotError as exc:  # ParseError, TokenError
        return _block(f"the text could not be parsed as one SELECT statement ({_parse_error_text(exc)})")
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return _block(f"{len(statements)} statements (or text after the semicolon); exactly one SELECT is allowed")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.SetOperation)):
        return _block(f"the statement is {type(tree).__name__}, not a SELECT")

    for node in tree.walk():
        if isinstance(node, WRITE_NODES):
            return _block(f"{type(node).__name__} is not allowed (read-only SELECT queries only)")

    cte_names = {c.alias.lower() for c in tree.find_all(exp.CTE) if c.alias}
    for name in cte_names:
        if name.startswith("pg_"):
            return _block(f"CTE name {name} is not allowed")

    real_tables = 0
    for table in tree.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            continue  # a table function; checked below with the function deny list
        name = table.name.lower()
        schema = table.db.lower()
        catalog = table.catalog.lower()
        if not schema and not catalog and name in cte_names:
            continue
        if catalog or schema not in ALLOWED_SCHEMAS or name not in ALLOWED_TABLES:
            qualified = ".".join(p for p in (table.catalog, table.db, table.name) if p)
            return _block(f"table {qualified} is not allowed; only erzeugung, verbrauch and preise can be read")
        real_tables += 1

    for fname in sorted(_function_names(tree)):
        if denied_function(fname):
            return _block(f"function {fname} is not allowed")

    if real_tables == 0:
        return _block("the query reads none of the tables erzeugung, verbrauch, preise")
    return None


# ------------------------------------------------------------------ database

def connect():
    """A fresh grader_ro connection (same settings as executor.run_query), READ ONLY."""
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "smard"),
        user=os.environ["GRADER_DB_USER"],
        password=os.environ["GRADER_DB_PASSWORD"],
    )
    conn.set_session(readonly=True, autocommit=False)
    return conn


def _explain_cost(cur, sql: str) -> float:
    cur.execute("EXPLAIN (FORMAT JSON) " + sql.rstrip().rstrip(";") + "\n")
    plan = cur.fetchone()[0]
    if isinstance(plan, str):
        import json
        plan = json.loads(plan)
    return float(plan[0]["Plan"]["Total Cost"])


def _timeout_block(wall: int, limits: Limits) -> SafeResult:
    return SafeResult(blocked=True, wall=wall, kind="timeout",
                      reason=f"timeout: the query ran longer than {limits.timeout_ms} ms")


def _plan_check(cur, sql: str, limits: Limits) -> SafeResult:
    """Wall 2 on an open cursor. Returns a SafeResult (blocked or not, with plan_cost)."""
    try:
        cost = _explain_cost(cur, sql)
    except psycopg2.errors.QueryCanceled:
        return _timeout_block(2, limits)
    except psycopg2.Error as exc:
        raise QueryError(str(exc)) from exc
    if cost > limits.max_plan_cost:
        return SafeResult(blocked=True, wall=2, kind="plan_cost", plan_cost=cost,
                          reason=(f"plan_cost: the estimated cost {cost:.0f} is above the limit "
                                  f"{limits.max_plan_cost:.0f}"))
    return SafeResult(blocked=False, plan_cost=cost)


def precheck(sql: str, limits: Limits | None = None, conn=None) -> SafeResult:
    """Walls 1 and 2 only; the query is never run (EXPLAIN without ANALYZE plans it only).
    Used for the dry run on history. A PostgreSQL error in EXPLAIN raises QueryError."""
    limits = limits or load_limits()
    blocked = check_static(sql)
    if blocked:
        return blocked
    own = conn is None
    conn = conn or connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {int(limits.timeout_ms)}")
            result = _plan_check(cur, sql, limits)
        return result
    finally:
        conn.rollback()
        if own:
            conn.close()


def safe_execute(sql: str, limits: Limits | None = None) -> SafeResult:
    """All four walls. Blocks come back as SafeResult(blocked=True, ...); a PostgreSQL error
    in a query that passed the walls raises QueryError (see the module text)."""
    limits = limits or load_limits()
    blocked = check_static(sql)
    if blocked:
        return blocked

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {int(limits.timeout_ms)}")
            plan = _plan_check(cur, sql, limits)
            if plan.blocked:
                return plan

        start = time.perf_counter()
        try:
            with conn.cursor(name="safe_runner") as cur:  # server-side cursor: rows stay on the server
                cur.execute(sql)
                rows = cur.fetchmany(limits.max_rows + 1)
        except psycopg2.errors.QueryCanceled:
            return _timeout_block(3, limits)
        except psycopg2.Error as exc:
            raise QueryError(str(exc)) from exc
        seconds = round(time.perf_counter() - start, 3)

        if len(rows) > limits.max_rows:
            return SafeResult(blocked=True, wall=3, kind="too_many_rows", plan_cost=plan.plan_cost,
                              seconds=seconds,
                              reason=f"too_many_rows: the query returns more than {limits.max_rows} rows")
        return SafeResult(blocked=False, rows=rows, plan_cost=plan.plan_cost, n_rows=len(rows),
                          seconds=seconds)
    finally:
        conn.rollback()
        conn.close()


BLOCKED_RETRY_TEXT = (
    "This query was blocked: {reason}\n"
    "Write a corrected query. Return only the SQL."
)


# ------------------------------------------------------------------ calibration on the gold set

def calibrate(gold_file: Path | None = None) -> dict:
    """Runs every gold query (the questions that have gold_sql) through the safe runner with
    limits that cannot trigger, and reports the largest plan cost, row count and run time."""
    from loader import load_questions
    questions = [q for q in (load_questions(gold_file) if gold_file else load_questions()) if q.gold_sql]
    open_limits = Limits(max_plan_cost=float("inf"), max_rows=10 ** 9, timeout_ms=120000)
    rows_out = []
    for q in questions:
        res = safe_execute(q.gold_sql, open_limits)
        rows_out.append({"id": q.id, "blocked": res.blocked, "wall": res.wall, "reason": res.reason,
                         "plan_cost": res.plan_cost, "n_rows": res.n_rows, "seconds": res.seconds})
    ok = [r for r in rows_out if not r["blocked"]]
    return {
        "n_queries": len(rows_out),
        "n_pass": len(ok),
        "failures": [r for r in rows_out if r["blocked"]],
        "max_plan_cost": max((r["plan_cost"] for r in ok), default=None),
        "max_plan_cost_id": max(ok, key=lambda r: r["plan_cost"])["id"] if ok else None,
        "max_rows": max((r["n_rows"] for r in ok), default=None),
        "max_rows_id": max(ok, key=lambda r: r["n_rows"])["id"] if ok else None,
        "max_seconds": max((r["seconds"] for r in ok), default=None),
        "max_seconds_id": max(ok, key=lambda r: r["seconds"])["id"] if ok else None,
        "rows": rows_out,
    }


def check_gold_against_limits(limits: Limits | None = None, gold_file: Path | None = None) -> dict:
    """Every gold query through all four walls with the real limits."""
    from loader import load_questions
    limits = limits or load_limits()
    questions = [q for q in (load_questions(gold_file) if gold_file else load_questions()) if q.gold_sql]
    failures = []
    for q in questions:
        res = safe_execute(q.gold_sql, limits)
        if res.blocked:
            failures.append({"id": q.id, "wall": res.wall, "reason": res.reason})
    return {"n": len(questions), "n_pass": len(questions) - len(failures), "failures": failures}


def main() -> int:
    if "--calibrate" in sys.argv:
        rep = calibrate()
        for key in ("n_queries", "n_pass", "max_plan_cost", "max_plan_cost_id", "max_rows",
                    "max_rows_id", "max_seconds", "max_seconds_id"):
            print(f"{key:18s} {rep[key]}")
        for f in rep["failures"]:
            print("BLOCKED", f)
        return 0 if not rep["failures"] else 1
    rep = check_gold_against_limits()
    print(f"{rep['n_pass']}/{rep['n']} pass")
    for f in rep["failures"]:
        print("FAIL", f)
    return 0 if not rep["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
