"""
The core function of the app (D44): answer_question(question) -> AnswerResult.

It runs exactly the configuration grader/configs/r3b_safe.yaml (or another config file)
the way grader/run.py does: same config loading, same prompt builder, same model settings,
same agent_loop.run_question call (all switches and max_attempts from the config). The screen
only draws the AnswerResult; no logic lives there.

Nothing from the grader is copied or edited. Imported from run.py: load_config, prompt_builder,
call_openai, PRICE_INPUT_PER_M, PRICE_OUTPUT_PER_M. Imported from agent_loop: run_question,
decline_reason. Imported from naive_agent: _strip_fences (the loop's own fence rule).
A config without the safe_runner switch is refused (ValueError): the app never runs a query
outside the four walls, and the rows of the final attempt come from the safe runner.

The loop does not return rows or column names. Two small additions outside the loop:
  - the safe_execute= argument that run_question already offers is given a wrapper that calls the
    real safe_runner.safe_execute and keeps its result (the rows of the final attempt);
  - the column names of the final query come from `SELECT * FROM (<final sql>) LIMIT 0` on a
    read-only grader_ro connection (only for a query that already passed all four walls).

No API call is made when model_caller= is given.
"""

import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache, partial
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
GRADER_DIR = PROJECT_ROOT / "grader"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(GRADER_DIR) not in sys.path:
    sys.path.insert(0, str(GRADER_DIR))

import run as grader_run  # noqa: E402  (grader/run.py; needs grader/ on the path)
import safe_runner  # noqa: E402
from agent_loop import decline_reason, run_question  # noqa: E402
from naive_agent import _strip_fences  # noqa: E402

import tracing  # noqa: E402  (app/tracing.py; the app folder is on the path when this file is imported)

DEFAULT_CONFIG = "grader/configs/r3b_safe.yaml"

STATUSES = ("answered", "no_rows", "declined_model", "declined_system", "blocked", "error")

MSG_REWRITTEN = ("Your first query returned no rows. The model rewrote it. "
                 "Check that the new query still answers your question.")
MSG_NO_ROWS = "No rows match this question."
MSG_DECLINED_MODEL = "The model declined: {reason}"
MSG_BLOCKED = "The query was blocked by safety check (wall {wall}): {reason}"
MSG_ERROR = "The query failed after {n} attempts: {error}"

TRACE_NAME = "answer_question"
MAX_TRACE_ROWS = 50  # result rows that go into a trace (D45)


@dataclass
class Attempt:
    number: int
    sql: str | None            # None when the model replied NO_QUERY
    outcome: str               # ok | empty_rows | empty_null | error | blocked | declined_model | declined_system
    reason: str | None         # error text, block reason, decline reason, or a short note for empty results
    row_count: int | None
    wall: int | None = None    # only for blocked attempts


@dataclass
class AnswerResult:
    question: str
    status: str                # one of STATUSES
    message: str
    attempts: list[Attempt] = field(default_factory=list)
    final_sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list = field(default_factory=list)
    row_count: int = 0
    rewritten_after_empty: bool = False
    seconds_total: float = 0.0    # model calls + SQL checks (the loop's total_seconds)
    seconds_model: float = 0.0    # model calls only (the loop's latency_seconds)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    model: str | None = None
    system_fingerprint: str | None = None
    trace_id: str | None = None                 # None when tracing is off (D45)
    tracing_status: str = "tracing off"         # "tracing on" or "tracing off: <reason>"


# ---------------------------------------------------------------- helpers

def _resolve_config(config_path) -> Path:
    p = Path(config_path)
    return p if p.is_absolute() or p.exists() else PROJECT_ROOT / p


def _column_names(sql: str, n_cols: int) -> list[str]:
    """Column names of a query that already passed the safe runner (zero rows are read)."""
    inner = sql.strip()
    if inner.endswith(";"):
        inner = inner[:-1].rstrip()  # one trailing semicolon, and the spaces before it
    try:
        # safe_runner.connect(): role grader_ro (GRADER_DB_USER), session READ ONLY, no autocommit
        conn = safe_runner.connect()
        try:
            with conn.cursor() as cur:
                # same timeout as every query of the safe runner (limits.yaml)
                cur.execute(f"SET LOCAL statement_timeout = {int(safe_runner.load_limits().timeout_ms)}")
                cur.execute("SELECT * FROM (\n" + inner + "\n) AS q LIMIT 0")
                return [d[0] for d in cur.description]
        finally:
            conn.rollback()
            conn.close()
    except Exception:  # names are a convenience; never fail the answer because of them
        return [f"column_{i + 1}" for i in range(n_cols)]


def _attempt_from_loop(a: dict, system_declined_last: bool) -> Attempt:
    n, sql, kind = a["attempt"], a["extracted_sql"], a["check_fired"]
    if a["declined"]:
        reason = decline_reason(_strip_fences(a["raw_model_output"]))
        return Attempt(n, None, "declined_model", reason, None)
    if a.get("blocked"):
        return Attempt(n, sql, "blocked", a["reason"], None, wall=a["wall"])
    if a["error"] is not None:
        return Attempt(n, sql, "error", a["error"], None)
    if system_declined_last:
        return Attempt(n, sql, "declined_system", None, a["n_rows"])
    if kind == "empty_rows":
        return Attempt(n, sql, "empty_rows", "the query returned no rows", a["n_rows"])
    if kind == "empty_null":
        return Attempt(n, sql, "empty_null", "the query returned only NULL values", a["n_rows"])
    return Attempt(n, sql, "ok", None, a["n_rows"])


def call_cost(prompt_tokens, completion_tokens) -> float:
    """USD for one model call, same prices as the loop totals."""
    return round(((prompt_tokens or 0) * grader_run.PRICE_INPUT_PER_M
                  + (completion_tokens or 0) * grader_run.PRICE_OUTPUT_PER_M) / 1_000_000, 6)


@lru_cache(maxsize=1)
def git_commit() -> str:
    """Short hash of the code that is running, or "unknown"."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                             text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else "unknown"
    except Exception:
        return "unknown"


def _jsonable(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def trace_output(result: AnswerResult) -> dict:
    """What goes into the trace as its output: status, message, final SQL and at most 50 rows."""
    rows = [[_jsonable(v) for v in row] for row in result.rows[:MAX_TRACE_ROWS]]
    return {"status": result.status, "message": result.message, "final_sql": result.final_sql,
            "columns": list(result.columns), "rows": rows, "row_count": result.row_count,
            "rows_truncated": result.row_count > MAX_TRACE_ROWS}


def sql_to_show(result: AnswerResult) -> str | None:
    """The SQL the screen shows (D10: never hidden): the final SQL, or, when there is none (blocked,
    error, system decline), the SQL of the last attempt that had one. None if the model never wrote any."""
    if result.final_sql:
        return result.final_sql
    for a in reversed(result.attempts):
        if a.sql:
            return a.sql
    return None


# ---------------------------------------------------------------- the function

def answer_question(question: str, config_path=DEFAULT_CONFIG, model_caller=None,
                    tracer=None, session_id=None) -> AnswerResult:
    """Answer one question with the configuration in config_path (default: r3b_safe).

    model_caller: a function messages -> {"raw_model_output", "prompt_tokens", ...} (same shape
    as agent_loop.call_openai). None means the real call_openai with the config's model,
    temperature and seed.

    tracer: a tracing.LangfuseTracer / NullTracer / any object with the same methods (D45). None means
    NullTracer. Tracing never changes the answer: the two functions handed to the loop only report
    what they already did, and every tracer call is guarded (a tracer that raises is ignored)."""
    cfg, _ = grader_run.load_config(_resolve_config(config_path))
    if not cfg["switches"]["safe_runner"]:
        raise ValueError(f"{config_path}: the safe_runner switch is off. The app only runs configs "
                         "where every query goes through the safe runner (D41, D44).")
    llm = model_caller or partial(grader_run.call_openai, model=cfg["model"],
                                  temperature=cfg["temperature"], seed=cfg["seed"])

    t = tracing.guarded(tracer)
    config_name = Path(str(config_path)).stem
    trace_id = t.start_trace(TRACE_NAME, question, session_id=session_id, tags=[config_name],
                             metadata={"config": str(config_path), "model": cfg["model"],
                                       "git_commit": git_commit()})

    last_safe = {}
    n_calls = 0

    def traced_llm(messages):  # reports each model call; the call itself is unchanged
        nonlocal n_calls
        call = llm(messages)
        n_calls += 1
        t.model_call(trace_id, list(messages), call.get("raw_model_output"), call.get("model"),
                     call.get("prompt_tokens"), call.get("completion_tokens"),
                     call_cost(call.get("prompt_tokens"), call.get("completion_tokens")),
                     metadata={"attempt": n_calls, "system_fingerprint": call.get("system_fingerprint"),
                               "latency_seconds": call.get("latency_seconds")})
        return call

    def keep_safe_result(sql):  # same call the loop would make itself; the result is kept
        start = time.perf_counter()
        try:
            res = safe_runner.safe_execute(sql)
        except Exception as exc:  # an SQL error: the loop turns it into the retry text; report it, then re-raise
            t.safety_check(trace_id, sql, {"blocked": False, "error": f"{type(exc).__name__}: {str(exc)[:500]}"},
                           seconds=time.perf_counter() - start)
            raise
        last_safe["result"] = res
        t.safety_check(trace_id, sql,
                       {"blocked": res.blocked, "wall": res.wall, "reason": res.reason, "kind": res.kind,
                        "n_rows": res.n_rows},
                       seconds=res.seconds if res.seconds is not None else time.perf_counter() - start)
        return res

    try:
        with grader_run.prompt_builder(cfg["prompt"], cfg["examples"]) as build:
            loop = run_question(question, cfg["switches"], max_attempts=cfg["max_attempts"], llm=traced_llm,
                                prompt_builder=build,
                                safe_execute=keep_safe_result)
    except Exception as exc:  # close the trace, then fail exactly as without tracing
        t.end_trace(trace_id, {"status": "exception", "error": type(exc).__name__}, tags=["exception", config_name])
        t.flush()
        raise

    raw_attempts = loop["attempts"]
    system = loop["system_declined"]
    attempts = [_attempt_from_loop(a, system and i == len(raw_attempts) - 1)
                for i, a in enumerate(raw_attempts)]
    final = attempts[-1]

    if system:
        status = "declined_system"
        message = decline_reason(loop["final_reply"])  # "No data: the tables have no rows for the period X to Y."
    elif final.outcome == "declined_model":
        status, message = "declined_model", MSG_DECLINED_MODEL.format(reason=final.reason)
    elif final.outcome == "blocked":
        status, message = "blocked", MSG_BLOCKED.format(wall=final.wall, reason=final.reason)
    elif final.outcome == "error":
        status, message = "error", MSG_ERROR.format(n=len(attempts), error=final.reason)
    elif final.outcome in ("empty_rows", "empty_null"):
        status, message = "no_rows", MSG_NO_ROWS
    else:
        status, message = "answered", ""

    rewritten = (status == "answered"
                 and any(a.outcome in ("empty_rows", "empty_null") for a in attempts[:-1]))
    if rewritten:
        message = MSG_REWRITTEN

    final_sql, columns, rows = None, [], []
    if status in ("answered", "no_rows"):
        final_sql = loop["final_sql"]
        res = last_safe.get("result")
        rows = list(res.rows) if res is not None and res.rows is not None else []
        columns = _column_names(final_sql, len(rows[0]) if rows else 1)

    cost = (loop["prompt_tokens"] * grader_run.PRICE_INPUT_PER_M
            + loop["completion_tokens"] * grader_run.PRICE_OUTPUT_PER_M) / 1_000_000
    result = AnswerResult(
        question=question, status=status, message=message, attempts=attempts,
        final_sql=final_sql, columns=columns, rows=rows, row_count=len(rows),
        rewritten_after_empty=rewritten,
        seconds_total=loop["total_seconds"], seconds_model=loop["latency_seconds"],
        prompt_tokens=loop["prompt_tokens"], completion_tokens=loop["completion_tokens"],
        cost_usd=round(cost, 6), model=loop["model"], system_fingerprint=loop["system_fingerprint"],
        trace_id=trace_id, tracing_status=t.status,
    )

    for mine, raw in zip(attempts, raw_attempts):  # one loop decision per attempt
        review = raw["check_fired"] == "review"
        t.loop_decision(trace_id, mine.number, "decline_review_fired" if review else mine.outcome,
                        {"attempt_outcome": mine.outcome, "reason": mine.reason, "n_rows": mine.row_count,
                         "wall": mine.wall, "check_fired": raw["check_fired"],
                         "fact": raw.get("fact")})
    t.end_trace(trace_id, trace_output(result), tags=[status, config_name])
    result.tracing_status = t.status  # after the last call: "tracing off: ..." if tracing broke on the way
    return result
