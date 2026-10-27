"""
Per-question .jsonl records for run_baseline.py and run_schema_linked.py.

Observation only: install_recorder() wraps the OpenAI client's create() so that
the raw model output, latency and token counts of each call can be read back
afterwards. The wrapper forwards every argument unchanged and returns the
unmodified response, so prompts, model, temperature and seed are untouched.
"""

import json
import time
from pathlib import Path


def _safe(read):
    """Return read(), or None if reading raises. Logging must never break a run."""
    try:
        return read()
    except Exception:
        return None


class CallRecorder:
    """Holds the details of the most recent API call."""

    def __init__(self):
        self._last = None

    def begin(self) -> None:
        self._last = None

    def take(self) -> dict:
        call, self._last = self._last, None
        return call or {}


def install_recorder(agent_module) -> CallRecorder:
    """Wrap agent_module.OpenAI once; later calls return the same recorder."""
    existing = getattr(agent_module, "_call_recorder", None)
    if existing is not None:
        return existing

    recorder = CallRecorder()
    real_openai = agent_module.OpenAI

    def recording_openai(*args, **kwargs):
        client = real_openai(*args, **kwargs)
        real_create = client.chat.completions.create

        def create(*a, **kw):
            start = time.perf_counter()
            response = real_create(*a, **kw)  # errors here are the agent's own, never swallowed
            latency = time.perf_counter() - start
            # Fail-safe: a field that can't be read is recorded as None; the run goes on.
            recorder._last = {
                "raw_model_output": _safe(lambda: response.choices[0].message.content),
                "latency_seconds": _safe(lambda: round(latency, 3)),
                "prompt_tokens": _safe(lambda: response.usage.prompt_tokens),
                "completion_tokens": _safe(lambda: response.usage.completion_tokens),
            }
            return response

        client.chat.completions.create = create
        return client

    agent_module.OpenAI = recording_openai
    agent_module._call_recorder = recorder
    return recorder


def make_record(question, result, agent_sql, call: dict, retrieved_tables=None) -> dict:
    return {
        "id": question.id,
        "tier": question.tier,
        "question": question.frage,
        "retrieved_tables": retrieved_tables,
        "raw_model_output": call.get("raw_model_output"),
        "extracted_sql": agent_sql,
        "passed": result.passed,
        "comparator_reason": result.reason,
        "latency_seconds": call.get("latency_seconds"),
        "prompt_tokens": call.get("prompt_tokens"),
        "completion_tokens": call.get("completion_tokens"),
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
