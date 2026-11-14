"""
The core function of the app (D44): answer_question(question) -> AnswerResult.

It runs exactly the configuration grader/configs/r3b_safe.yaml (or another config file)
the way grader/run.py does: same config loading, same prompt builder, same model settings,
same agent_loop.run_question call (all switches and max_attempts from the config). The screen
only draws the AnswerResult; no logic lives there.

Nothing from the grader is copied or edited. Imported from run.py: load_config, prompt_builder,
call_openai, PRICE_INPUT_PER_M, PRICE_OUTPUT_PER_M. Imported from agent_loop: run_question,
decline_reason. Imported from naive_agent: _strip_fences (the loop's own fence rule).
Rows and columns are only filled when the config has the safe_runner switch on (r3b_safe does).

The loop does not return rows or column names. Two small additions outside the loop:
  - the safe_execute= argument that run_question already offers is given a wrapper that calls the
    real safe_runner.safe_execute and keeps its result (the rows of the final attempt);
  - the column names of the final query come from `SELECT * FROM (<final sql>) LIMIT 0` on a
    read-only grader_ro connection (only for a query that already passed all four walls).

No API call is made when model_caller= is given.
"""

import sys
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRADER_DIR = PROJECT_ROOT / "grader"
if str(GRADER_DIR) not in sys.path:
    sys.path.insert(0, str(GRADER_DIR))

import run as grader_run  # noqa: E402  (grader/run.py; needs grader/ on the path)
import safe_runner  # noqa: E402
from agent_loop import decline_reason, run_question  # noqa: E402
from naive_agent import _strip_fences  # noqa: E402

DEFAULT_CONFIG = "grader/configs/r3b_safe.yaml"

STATUSES = ("answered", "no_rows", "declined_model", "declined_system", "blocked", "error")

MSG_REWRITTEN = ("Your first query returned no rows. The model rewrote it. "
                 "Check that the new query still answers your question.")
MSG_NO_ROWS = "No rows match this question."
MSG_DECLINED_MODEL = "The model declined: {reason}"
MSG_BLOCKED = "The query was blocked by safety check (wall {wall}): {reason}"
MSG_ERROR = "The query failed after {n} attempts: {error}"


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


# ---------------------------------------------------------------- helpers

def _resolve_config(config_path) -> Path:
    p = Path(config_path)
    return p if p.is_absolute() or p.exists() else PROJECT_ROOT / p


def _column_names(sql: str, n_cols: int) -> list[str]:
    """Column names of a query that already passed the safe runner (zero rows are read)."""
    try:
        conn = safe_runner.connect()  # grader_ro, READ ONLY
        try:
            with conn.cursor() as cur:
                cur.execute(f"SET LOCAL statement_timeout = {int(safe_runner.load_limits().timeout_ms)}")
                cur.execute("SELECT * FROM (\n" + sql.rstrip().rstrip(";") + "\n) AS q LIMIT 0")
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


# ---------------------------------------------------------------- the function

def answer_question(question: str, config_path=DEFAULT_CONFIG, model_caller=None) -> AnswerResult:
    """Answer one question with the configuration in config_path (default: r3b_safe).

    model_caller: a function messages -> {"raw_model_output", "prompt_tokens", ...} (same shape
    as agent_loop.call_openai). None means the real call_openai with the config's model,
    temperature and seed."""
    cfg, _ = grader_run.load_config(_resolve_config(config_path))
    llm = model_caller or partial(grader_run.call_openai, model=cfg["model"],
                                  temperature=cfg["temperature"], seed=cfg["seed"])

    last_safe = {}

    def keep_safe_result(sql):  # same call the loop would make itself; the result is kept
        res = safe_runner.safe_execute(sql)
        last_safe["result"] = res
        return res

    with grader_run.prompt_builder(cfg["prompt"], cfg["examples"]) as build:
        loop = run_question(question, cfg["switches"], max_attempts=cfg["max_attempts"], llm=llm,
                            prompt_builder=build,
                            safe_execute=keep_safe_result if cfg["switches"]["safe_runner"] else None)

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
    return AnswerResult(
        question=question, status=status, message=message, attempts=attempts,
        final_sql=final_sql, columns=columns, rows=rows, row_count=len(rows),
        rewritten_after_empty=rewritten,
        seconds_total=loop["total_seconds"], seconds_model=loop["latency_seconds"],
        prompt_tokens=loop["prompt_tokens"], completion_tokens=loop["completion_tokens"],
        cost_usd=round(cost, 6), model=loop["model"], system_fingerprint=loop["system_fingerprint"],
    )
