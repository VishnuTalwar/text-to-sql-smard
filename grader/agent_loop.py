"""
Execute-check-refine loop on top of the v2b prompt (section 13 of PROJECT_PROGRESS.md).

run_question() answers one question. Attempt 1 is exactly the v2b setup: the v2b
prompt as one user message, gpt-4o-2024-08-06 (naive_agent.MODEL), temperature 0, seed 0, fences stripped the way
naive_agent.answer() strips them. If attempt 1 is a NO_QUERY decline, or its SQL
runs without error, the loop stops and nothing differs from v2b.

Checks, each with an on/off switch in `switches`:
  error_retry     implemented (row R1). If the SQL fails to run, the SAME conversation
                  continues: the model's reply is appended as an assistant message and
                  a user message gives the PostgreSQL error (ERROR_RETRY_TEXT). At most
                  max_attempts attempts in total; the last attempt is the answer.
  empty_retry     implemented (row R2). If the SQL runs but the result is empty (0 rows,
                  or every value in every row is NULL; a 0 or any other non-NULL value is
                  not empty), the same conversation continues with EMPTY_ROWS_TEXT or
                  EMPTY_NULL_TEXT. Error retry and empty retry share the same limit of
                  max_attempts attempts in total. If the last attempt is still empty,
                  that result is the answer.
  decline_review implemented (row R3), uses date_facts.py. (a) When an attempt replies
                  NO_QUERY, no review has happened yet for this question, fewer than
                  max_attempts attempts have been used, and decline_review_decision(reason)
                  fires (the reason claims a period is missing but the tables have rows for
                  it), the same conversation continues with REVIEW_TEXT: the model's own
                  reason plus one "Fact:" line per period. At most one review per question;
                  a NO_QUERY after the review stands. (b) When the empty-result retry fires
                  and empty_fact_decision(sql) fires too (the SQL asks for a period in which
                  every table has no rows), one "Fact:" line per period goes between the
                  two lines of the empty-result message. Dates are YYYY-MM-DD, the end is
                  the last day inside the period.
  safe_runner     implemented (D41, step 3), default OFF. Every agent query goes through
                  safe_runner.safe_execute (four walls: static sqlglot check, EXPLAIN cost
                  limit, read-only run with timeout and row cap, structured result). A
                  blocked query counts like an SQL error: with error_retry on, the same
                  conversation continues with BLOCKED_RETRY_TEXT. Each attempt then also
                  records blocked, wall and reason. With the switch off nothing here changes
                  and the attempt records have no such keys.
  empty_fact_decline  implemented (row R3b). When an attempt's SQL runs and is empty and
                  empty_fact_decision(sql) fires (the period it asks for has no rows in any
                  table), the loop stops WITHOUT another model call and returns a decline
                  with the reason "No data: the tables have no rows for the period <start>
                  to <end>." This replaces the "Fact:" line of the R3 empty message, which
                  is then never sent. If the result is empty but the period has rows (or
                  no period is found), the R2 retry message is used unchanged.

SQL is run through executor.run_query(): role grader_ro (SELECT only, no TEMP, role
statement_timeout 30 s, the same as the grader), a fresh connection per call, so a
failed statement can never leave an aborted transaction behind.

Nothing here edits an existing file. The model call and the SQL execution can be
replaced (llm=, execute=) so the loop can be tested without the API.
"""

import os
import time
from datetime import timedelta

from naive_agent import MODEL, SEED, _strip_fences
from executor import QueryError, run_query
from prompt_template_v2b import build_prompt as build_v2b_prompt

DECLINE_MARKER = "NO_QUERY"

SWITCH_NAMES = ("error_retry", "empty_retry", "decline_review", "empty_fact_decline",
                "safe_runner")
DEFAULT_SWITCHES = {"error_retry": True, "empty_retry": False, "decline_review": False,
                    "empty_fact_decline": False, "safe_runner": False}

ERROR_RETRY_TEXT = (
    "This query failed with the following error from PostgreSQL:\n"
    "{error}\n"
    "Write a corrected query. Return only the SQL."
)
EMPTY_ROWS_TEXT = (
    "This query ran but returned no rows.\n"
    "Write a corrected query. Return only the SQL."
)
EMPTY_NULL_TEXT = (
    "This query ran but returned only NULL values.\n"
    "Write a corrected query. Return only the SQL."
)
BLOCKED_RETRY_TEXT = (
    "This query was blocked: {reason}\n"
    "Write a corrected query. Return only the SQL."
)
RETRY_TEXTS = {"empty_rows": EMPTY_ROWS_TEXT, "empty_null": EMPTY_NULL_TEXT}
REVIEW_TEXT = (
    'Your reason was: "{reason}"\n'
    "{facts}\n"
    "Reply again following the original instructions."
)
SYSTEM_DECLINE_REASON = "No data: the tables have no rows for the period {start} to {end}."
REVIEW_FACT_LINE = "Fact: the tables have rows for the period {start} to {end}."
EMPTY_FACT_LINE = "Fact: the tables have no rows for the period {start} to {end}."


def is_decline(reply: str) -> bool:
    """Same rule as run_v2b.is_decline: NO_QUERY at the start, any letter case,
    after whitespace and code fences have been stripped."""
    return reply.strip().upper().startswith(DECLINE_MARKER)


def format_pg_error(exc: QueryError) -> str:
    """PostgreSQL primary message, plus a line "HINT: <hint>" only if PostgreSQL gave
    one. No LINE/caret context, no traceback. If the failure has no PostgreSQL
    diagnostics (for example an empty statement), the driver's message is used."""
    cause = exc.__cause__
    diag = getattr(cause, "diag", None)
    primary = getattr(diag, "message_primary", None)
    hint = getattr(diag, "message_hint", None)
    if not primary:
        primary = str(cause if cause is not None else exc).strip().split("\n")[0]
    text = primary.strip()
    if hint:
        text += f"\nHINT: {hint.strip()}"
    return text


def empty_kind(rows) -> str | None:
    """"empty_rows" for 0 rows, "empty_null" if every value in every row is NULL,
    otherwise None. A 0 (or any other non-NULL value) is a result, not empty.
    rows=None (an execute function that returns nothing) is never empty."""
    if rows is None:
        return None
    if len(rows) == 0:
        return "empty_rows"
    if all(v is None for row in rows for v in row):
        return "empty_null"
    return None


def decline_reason(reply: str) -> str:
    """The text after "NO_QUERY:" (the reply has been stripped of fences and spaces)."""
    rest = reply.strip()[len(DECLINE_MARKER):]
    if rest.startswith(":"):
        rest = rest[1:]
    return rest.strip()


def _period_json(p: dict) -> dict:
    """date_facts period -> {"start", "end" (last day inside, inclusive), "rows"}."""
    end = p["end"]
    last = end.date() if end.year >= 9999 else (end - timedelta(microseconds=1)).date()
    return {"start": p["start"].date().isoformat(), "end": last.isoformat(), "rows": p["rows"]}


def call_openai(messages: list[dict], client=None, model: str = MODEL,
                temperature: float = 0, seed: int = SEED) -> dict:
    """One chat completion. The defaults are the fixed settings of every row so far
    (naive_agent.MODEL, temperature 0, seed 0); run.py passes the values of a config."""
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        seed=seed,
    )
    latency = time.perf_counter() - start
    usage = response.usage
    return {
        # Which model snapshot answered; None if the response has no such field.
        "model": getattr(response, "model", None),
        "system_fingerprint": getattr(response, "system_fingerprint", None),
        "raw_model_output": response.choices[0].message.content,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "latency_seconds": round(latency, 3),
    }


def _check_switches(switches: dict | None) -> dict:
    merged = dict(DEFAULT_SWITCHES)
    merged.update(switches or {})
    unknown = set(merged) - set(SWITCH_NAMES)
    if unknown:
        raise ValueError(f"unknown switches: {sorted(unknown)}")
    return merged


class _Blocked(Exception):
    """Raised inside the loop when safe_execute blocks a query (carries the SafeResult)."""

    def __init__(self, result):
        super().__init__(result.reason)
        self.result = result


def run_question(question: str, switches: dict | None = None, max_attempts: int = 3,
                 llm=None, execute=None, prompt_builder=None, safe_execute=None) -> dict:
    """Answer one question. Returns a record (see the keys at the bottom).
    safe_execute= replaces safe_runner.safe_execute (tests); only used with the safe_runner switch."""
    switches = _check_switches(switches)
    llm = llm or call_openai
    execute = execute or run_query
    prompt_builder = prompt_builder or build_v2b_prompt
    use_safe = switches["safe_runner"]
    if use_safe and safe_execute is None:
        import safe_runner  # needs sqlglot and the database; only when the switch is on
        safe_execute = safe_runner.safe_execute

    messages = [{"role": "user", "content": prompt_builder(question)}]
    attempts: list[dict] = []
    cap_hit = False
    check_seconds = 0.0
    review_done = False
    system_decline = None  # set when empty_fact_decline stops the loop: {"periods": [...], "reason": ...}
    if switches["decline_review"] or switches["empty_fact_decline"]:
        import date_facts  # needs sqlglot and the database; only when a date check is on

    for n in range(1, max_attempts + 1):
        call = llm(messages)
        raw = call["raw_model_output"]
        reply = _strip_fences(raw)
        declined = is_decline(reply)
        sql = None if declined else reply
        error = None
        fired = None     # which check asks for another attempt: "error", "empty_rows", "empty_null", "review"
        n_rows = None
        fact = None      # the database fact sent back with the retry message, if any
        reason = None
        block = None     # the SafeResult of a blocked query (safe_runner switch only)

        if sql is not None and (use_safe or switches["error_retry"] or switches["empty_retry"]
                                or switches["empty_fact_decline"]):
            start = time.perf_counter()
            try:
                if use_safe:
                    safe = safe_execute(sql)
                    if safe.blocked:
                        raise _Blocked(safe)
                    rows = safe.rows
                else:
                    rows = execute(sql)
            except _Blocked as exc:
                block = exc.result
                error = f"blocked (wall {block.wall}): {block.reason}"  # counts like an SQL error
                if switches["error_retry"]:
                    fired = "error"
            except QueryError as exc:
                error = format_pg_error(exc)
                if switches["error_retry"]:
                    fired = "error"
            else:
                n_rows = None if rows is None else len(rows)
                kind = empty_kind(rows) if (switches["empty_retry"] or switches["empty_fact_decline"]) else None
                if kind and switches["empty_fact_decline"]:
                    decision = date_facts.empty_fact_decision(sql)
                    if decision["fire"]:
                        periods = [_period_json(p) for p in decision["periods"]]
                        system_decline = {"periods": periods, "reason": " ".join(
                            SYSTEM_DECLINE_REASON.format(start=p["start"], end=p["end"]) for p in periods)}
                        fact = {"kind": "system_decline", "periods": periods}
                        fired = kind
                    elif switches["empty_retry"]:
                        fired = kind  # empty, but the period has rows (or none found): R2 message
                elif kind and switches["empty_retry"]:
                    fired = kind
            check_seconds += time.perf_counter() - start

        if declined and switches["decline_review"] and not review_done and n < max_attempts:
            start = time.perf_counter()
            reason = decline_reason(reply)
            decision = date_facts.decline_review_decision(reason)
            check_seconds += time.perf_counter() - start
            if decision["fire"]:
                fired = "review"
                review_done = True
                fact = {"kind": "review", "reason": reason,
                        "periods": [_period_json(p) for p in decision["periods"]]}
        elif (fired in ("empty_rows", "empty_null") and switches["decline_review"]
              and not switches["empty_fact_decline"] and system_decline is None):
            start = time.perf_counter()
            decision = date_facts.empty_fact_decision(sql)
            check_seconds += time.perf_counter() - start
            if decision["fire"]:
                fact = {"kind": "empty", "periods": [_period_json(p) for p in decision["periods"]]}

        attempts.append({
            "attempt": n,
            "raw_model_output": raw,
            "extracted_sql": sql,
            "declined": declined,
            "error": error,
            "check_fired": fired,    # "error", "empty_rows", "empty_null" or None
            "n_rows": n_rows,
            "fact": fact,            # None, or {"kind": "review" | "empty", "periods": [...]}
            "prompt_tokens": call.get("prompt_tokens"),
            "completion_tokens": call.get("completion_tokens"),
            "latency_seconds": call.get("latency_seconds"),
            "model": call.get("model"),
            "system_fingerprint": call.get("system_fingerprint"),
        })
        if use_safe:
            attempts[-1].update({"blocked": block is not None,
                                 "wall": block.wall if block else None,
                                 "reason": block.reason if block else None})

        if system_decline is not None:
            break  # the period is proven empty: decline without asking the model again
        if fired is None:
            break  # declined, or nothing to fix (or the check is off): this is the answer
        if n == max_attempts:
            cap_hit = True  # used every attempt and the last SQL still fails or is empty
            break
        if fired == "error" and block is not None:
            retry_text = BLOCKED_RETRY_TEXT.format(reason=block.reason)
        elif fired == "error":
            retry_text = ERROR_RETRY_TEXT.format(error=error)
        elif fired == "review":
            facts = "\n".join(REVIEW_FACT_LINE.format(start=p["start"], end=p["end"]) for p in fact["periods"])
            retry_text = REVIEW_TEXT.format(reason=fact["reason"], facts=facts)
        elif fact is not None:  # empty result with a database fact between the two lines
            first, second = RETRY_TEXTS[fired].split("\n", 1)
            facts = "\n".join(EMPTY_FACT_LINE.format(start=p["start"], end=p["end"]) for p in fact["periods"])
            retry_text = f"{first}\n{facts}\n{second}"
        else:
            retry_text = RETRY_TEXTS[fired]
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": retry_text},
        ]

    final = attempts[-1]
    system = system_decline is not None
    declined_final = final["declined"] or system
    before = None if system else (attempts[-2]["check_fired"] if len(attempts) > 1 else None)  # check before the final attempt
    kinds = [a["check_fired"] for a in attempts]
    review_fact = next((a["fact"] for a in attempts if a["fact"] and a["fact"]["kind"] == "review"), None)
    empty_fact = [p for a in attempts if a["fact"] and a["fact"]["kind"] == "empty" for p in a["fact"]["periods"]]
    model_seconds = sum(a["latency_seconds"] or 0 for a in attempts)
    return {
        "final_sql": None if system else final["extracted_sql"],
        "final_reply": ("NO_QUERY: " + system_decline["reason"]) if system else final["raw_model_output"],
        "declined": declined_final,
        "system_declined": system,
        "system_decline_period": system_decline["periods"] if system else [],
        "model": final["model"],                        # of the final attempt
        "system_fingerprint": final["system_fingerprint"],
        "attempts": attempts,
        "n_attempts": len(attempts),
        "retried": len(attempts) > 1,
        "crashed_on_attempt_1": attempts[0]["error"] is not None,
        "declined_after_error": declined_final and before == "error",
        "declined_after_empty": declined_final and before in ("empty_rows", "empty_null"),
        "empty_on_attempt1": attempts[0]["check_fired"] in ("empty_rows", "empty_null"),
        "retried_after_error": "error" in kinds[:-1] if len(kinds) > 1 else False,
        "retried_after_empty": any(k in ("empty_rows", "empty_null") for k in kinds[:-1]),
        "ended_empty": final["check_fired"] in ("empty_rows", "empty_null") and not system,
        "review_fired": review_fact is not None,
        "review_periods": review_fact["periods"] if review_fact else [],
        "declined_after_review": declined_final and before == "review",
        "answered_after_review": review_fact is not None and not declined_final,
        "empty_fact_fired": bool(empty_fact),
        "empty_fact_period": empty_fact,
        "cap_hit": cap_hit,
        "prompt_tokens": sum(a["prompt_tokens"] or 0 for a in attempts),
        "completion_tokens": sum(a["completion_tokens"] or 0 for a in attempts),
        "latency_seconds": round(model_seconds, 3),  # model calls only, comparable to v2b
        "check_seconds": round(check_seconds, 3),    # SQL executions inside the loop
        "total_seconds": round(model_seconds + check_seconds, 3),
    }
