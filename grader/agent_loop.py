"""
Execute-check-refine loop on top of the v2b prompt (section 13 of PROJECT_PROGRESS.md).

run_question() answers one question. Attempt 1 is exactly the v2b setup: the v2b
prompt as one user message, gpt-4o, temperature 0, seed 0, fences stripped the way
naive_agent.answer() strips them. If attempt 1 is a NO_QUERY decline, or its SQL
runs without error, the loop stops and nothing differs from v2b.

Checks, each with an on/off switch in `switches`:
  error_retry     implemented (row R1). If the SQL fails to run, the SAME conversation
                  continues: the model's reply is appended as an assistant message and
                  a user message gives the PostgreSQL error (ERROR_RETRY_TEXT). At most
                  max_attempts attempts in total; the last attempt is the answer.
  empty_retry     not implemented yet (row R2); True raises NotImplementedError.
  decline_review  not implemented yet (row R3); True raises NotImplementedError.

SQL is run through executor.run_query(): role grader_ro (SELECT only, no TEMP, role
statement_timeout 30 s, the same as the grader), a fresh connection per call, so a
failed statement can never leave an aborted transaction behind.

Nothing here edits an existing file. The model call and the SQL execution can be
replaced (llm=, execute=) so the loop can be tested without the API.
"""

import os
import time

from naive_agent import MODEL, SEED, _strip_fences
from executor import QueryError, run_query
from prompt_template_v2b import build_prompt as build_v2b_prompt

DECLINE_MARKER = "NO_QUERY"

SWITCH_NAMES = ("error_retry", "empty_retry", "decline_review")
DEFAULT_SWITCHES = {"error_retry": True, "empty_retry": False, "decline_review": False}

ERROR_RETRY_TEXT = (
    "This query failed with the following error from PostgreSQL:\n"
    "{error}\n"
    "Write a corrected query. Return only the SQL."
)


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


def call_openai(messages: list[dict], client=None) -> dict:
    """One chat completion with the fixed settings (gpt-4o, temperature 0, seed 0)."""
    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        seed=SEED,
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
    for name in ("empty_retry", "decline_review"):
        if merged[name]:
            raise NotImplementedError(f"switch {name!r} is not implemented yet")
    return merged


def run_question(question: str, switches: dict | None = None, max_attempts: int = 3,
                 llm=None, execute=None, prompt_builder=None) -> dict:
    """Answer one question. Returns a record (see the keys at the bottom)."""
    switches = _check_switches(switches)
    llm = llm or call_openai
    execute = execute or run_query
    prompt_builder = prompt_builder or build_v2b_prompt

    messages = [{"role": "user", "content": prompt_builder(question)}]
    attempts: list[dict] = []
    cap_hit = False
    check_seconds = 0.0

    for n in range(1, max_attempts + 1):
        call = llm(messages)
        raw = call["raw_model_output"]
        reply = _strip_fences(raw)
        declined = is_decline(reply)
        sql = None if declined else reply
        error = None

        if sql is not None and switches["error_retry"]:
            start = time.perf_counter()
            try:
                execute(sql)
            except QueryError as exc:
                error = format_pg_error(exc)
            check_seconds += time.perf_counter() - start

        attempts.append({
            "attempt": n,
            "raw_model_output": raw,
            "extracted_sql": sql,
            "declined": declined,
            "error": error,
            "prompt_tokens": call.get("prompt_tokens"),
            "completion_tokens": call.get("completion_tokens"),
            "latency_seconds": call.get("latency_seconds"),
            "model": call.get("model"),
            "system_fingerprint": call.get("system_fingerprint"),
        })

        if error is None:
            break  # declined, or the SQL ran (or error_retry is off): this is the answer
        if n == max_attempts:
            cap_hit = True  # used every attempt and the last SQL still fails
            break
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": ERROR_RETRY_TEXT.format(error=error)},
        ]

    final = attempts[-1]
    model_seconds = sum(a["latency_seconds"] or 0 for a in attempts)
    return {
        "final_sql": final["extracted_sql"],
        "final_reply": final["raw_model_output"],
        "declined": final["declined"],
        "model": final["model"],                        # of the final attempt
        "system_fingerprint": final["system_fingerprint"],
        "attempts": attempts,
        "n_attempts": len(attempts),
        "retried": len(attempts) > 1,
        "crashed_on_attempt_1": attempts[0]["error"] is not None,
        "declined_after_error": final["declined"] and len(attempts) > 1,
        "cap_hit": cap_hit,
        "prompt_tokens": sum(a["prompt_tokens"] or 0 for a in attempts),
        "completion_tokens": sum(a["completion_tokens"] or 0 for a in attempts),
        "latency_seconds": round(model_seconds, 3),  # model calls only, comparable to v2b
        "check_seconds": round(check_seconds, 3),    # SQL executions inside the loop
        "total_seconds": round(model_seconds + check_seconds, 3),
    }
