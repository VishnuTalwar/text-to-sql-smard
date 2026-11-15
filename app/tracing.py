"""
Langfuse tracing for the app (D45). Only the app is traced; grader/run.py never imports this file.

  get_tracer()   a LangfuseTracer when LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_BASE_URL
                 (or, if that is not set, the deprecated LANGFUSE_HOST) are set and the client starts,
                 otherwise a NullTracer. Both have the same methods:

      start_trace(name, question, session_id=None, tags=(), metadata=None) -> trace_id or None
      model_call(trace_id, messages, metadata=None) -> step     the step starts NOW ...
          step.finish(output, model, prompt_tokens, completion_tokens, cost_usd, metadata=None)
          step.fail(exc)                                        ... and ends at finish/fail, so it has
      safety_check(trace_id, sql) -> step                       the real duration of the call
          step.finish(output)
          step.fail(exc)
      loop_decision(trace_id, attempt, outcome, details=None)
      summary(trace_id, shown, hidden_reason=None, unknown_numbers=())
      score(trace_id, name, value, comment=None) -> True if it was handed to Langfuse
      end_trace(trace_id, output, tags=None)
      flush()
      status (text)      "tracing on" or "tracing off: <reason>"
      enabled (bool)

Tracing fails open: a LangfuseTracer method never raises. On the first error it logs one warning line
(the exception class and a scrubbed message, never a key) and switches itself off for the rest of the
process. guarded(tracer) gives the same promise for any tracer object (used by answer.py and
summary.py, so even a tracer that raises cannot change an answer).

Langfuse SDK 5.x calls used (see requirements.txt for the pinned version):
  Langfuse(public_key=, secret_key=, base_url=)            client from the three variables
  propagate_attributes(session_id=, tags=, trace_name=, metadata=)   session id, tags, name on every span
  client.start_observation(name=, as_type="span"/"generation"/"event", input=, output=, metadata=,
        model=, usage_details=, cost_details=, trace_context=)       spans and generation steps
  span.start_observation(...) / span.update(...) / span.end()      nested steps, root output
  client.create_score(name=, value=, trace_id=, data_type=)        user feedback
  client.flush()                                                   deliver before the page goes on
"""

import logging
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PUBLIC, ENV_SECRET = "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"
ENV_URL, ENV_URL_OLD = "LANGFUSE_BASE_URL", "LANGFUSE_HOST"  # LANGFUSE_HOST is deprecated, still accepted
SECRET_ENV_NAMES = ("LANGFUSE_SECRET_KEY", "OPENAI_API_KEY")
MAX_REMEMBERED_TRACES = 200

log = logging.getLogger("app.tracing")


class NullStep:
    """The step of a NullTracer: does nothing."""

    def finish(self, *args, **kwargs):
        return None

    def fail(self, exc):
        return None


class NullTracer:
    """Does nothing. The default everywhere."""

    enabled = False

    def __init__(self, reason: str = "no keys"):
        self.status = f"tracing off: {reason}"

    def start_trace(self, name, question, session_id=None, tags=(), metadata=None):
        return None

    def model_call(self, trace_id, messages, metadata=None):
        return NullStep()

    def safety_check(self, trace_id, sql):
        return NullStep()

    def loop_decision(self, trace_id, attempt, outcome, details=None):
        return None

    def summary(self, trace_id, shown, hidden_reason=None, unknown_numbers=()):
        return None

    def score(self, trace_id, name, value, comment=None):
        return False

    def end_trace(self, trace_id, output, tags=None):
        return None

    def flush(self):
        return None


METHODS = ("start_trace", "model_call", "safety_check", "loop_decision", "summary", "score",
           "end_trace", "flush")


class _LangfuseStep:
    """An open Langfuse step. finish() / fail() update it and end it; neither ever raises."""

    def __init__(self, tracer, method, span, kind, metadata):
        self._tracer, self._method, self._span, self._kind, self._metadata = tracer, method, span, kind, metadata

    def finish(self, output, model=None, prompt_tokens=None, completion_tokens=None, cost_usd=None,
               metadata=None):
        try:
            if self._kind == "generation":
                usage = {"input": int(prompt_tokens or 0), "output": int(completion_tokens or 0)}
                usage["total"] = usage["input"] + usage["output"]
                self._span.update(output=output, model=model, usage_details=usage,
                                  cost_details={"total": float(cost_usd or 0.0)},
                                  metadata={**self._metadata, **(metadata or {})})
            else:
                self._span.update(output=output)
            self._span.end()
        except Exception as exc:
            self._tracer._fail(f"{self._method}.finish", exc)

    def fail(self, exc):
        try:
            text = f"{type(exc).__name__}: {self._tracer._scrub(str(exc))}"
            self._span.update(output={"error": text}, level="ERROR", status_message=text)
            self._span.end()
        except Exception as inner:
            self._tracer._fail(f"{self._method}.fail", inner)


class LangfuseTracer:
    """Sends the steps to Langfuse. `client` is a langfuse.Langfuse (or a stand-in with the same calls)."""

    def __init__(self, client, secrets=()):
        self._client = client
        self._secrets = [s for s in secrets if s]
        self._off_reason = None
        self._traces = {}  # trace_id -> {"root": span, "attrs": dict}; the newest MAX_REMEMBERED_TRACES

    # ------------------------------------------------------------ status

    @property
    def enabled(self) -> bool:
        return self._off_reason is None

    @property
    def status(self) -> str:
        return "tracing on" if self.enabled else f"tracing off: {self._off_reason}"

    def _scrub(self, text: str) -> str:
        for s in self._secrets:
            text = text.replace(s, "***")
        return text[:200]

    def _fail(self, method: str, exc: Exception) -> None:
        if self._off_reason is None:  # one warning line, then silent
            log.warning("tracing: %s failed (%s: %s); tracing is switched off for this session",
                        method, type(exc).__name__, self._scrub(str(exc)))
            self._off_reason = f"{method} failed ({type(exc).__name__})"

    # ------------------------------------------------------------ helpers (may raise; callers catch)

    def _propagate(self, attrs: dict, tags=None):
        from langfuse import propagate_attributes
        kwargs = {"trace_name": attrs["name"], "tags": list(tags if tags is not None else attrs["tags"])}
        if attrs.get("session_id"):
            kwargs["session_id"] = attrs["session_id"]
        if attrs.get("metadata"):
            kwargs["metadata"] = attrs["metadata"]
        return propagate_attributes(**kwargs)

    def _parent(self, trace_id):
        st = self._traces.get(trace_id)
        return st["root"] if st else None

    def _child(self, trace_id, **kwargs):
        """A new step under the root span of the trace (also after the root has ended)."""
        st = self._traces.get(trace_id)
        if st is None:
            return None
        with self._propagate(st["attrs"]):
            return st["root"].start_observation(**kwargs)

    # ------------------------------------------------------------ the methods

    def start_trace(self, name, question, session_id=None, tags=(), metadata=None):
        if not self.enabled:
            return None
        try:
            attrs = {"name": name, "tags": list(tags), "session_id": session_id,
                     "metadata": {k: str(v) for k, v in (metadata or {}).items()}}
            with self._propagate(attrs):
                root = self._client.start_observation(name=name, as_type="span", input=question,
                                                      metadata=metadata)
            trace_id = root.trace_id
            self._traces[trace_id] = {"root": root, "attrs": attrs}
            while len(self._traces) > MAX_REMEMBERED_TRACES:
                self._traces.pop(next(iter(self._traces)))
            return trace_id
        except Exception as exc:
            self._fail("start_trace", exc)
            return None

    def model_call(self, trace_id, messages, metadata=None):
        """Starts the generation step now; step.finish(...) / step.fail(exc) ends it."""
        if not self.enabled or trace_id is None:
            return NullStep()
        try:
            span = self._child(trace_id, name="model call", as_type="generation", input=messages,
                               metadata=metadata)
            return NullStep() if span is None else _LangfuseStep(self, "model_call", span, "generation",
                                                                 dict(metadata or {}))
        except Exception as exc:
            self._fail("model_call", exc)
            return NullStep()

    def safety_check(self, trace_id, sql):
        """Starts the safety-check-and-run step now; step.finish(output) / step.fail(exc) ends it."""
        if not self.enabled or trace_id is None:
            return NullStep()
        try:
            span = self._child(trace_id, name="safety check and run", as_type="span", input=sql)
            return NullStep() if span is None else _LangfuseStep(self, "safety_check", span, "span", {})
        except Exception as exc:
            self._fail("safety_check", exc)
            return NullStep()

    def loop_decision(self, trace_id, attempt, outcome, details=None):
        if not self.enabled or trace_id is None:
            return None
        try:
            self._child(trace_id, name=f"loop decision {attempt}", as_type="event",
                               input={"attempt": attempt}, output={"outcome": outcome, **(details or {})})
            # an "event" is ended by the SDK when it is created (calling end() warns), so no step.end() here
        except Exception as exc:
            self._fail("loop_decision", exc)

    def summary(self, trace_id, shown, hidden_reason=None, unknown_numbers=()):
        if not self.enabled or trace_id is None:
            return None
        try:
            step = self._child(trace_id, name="summary number check", as_type="span",
                               output={"shown": bool(shown), "hidden_reason": hidden_reason,
                                       "unknown_numbers": [str(n) for n in unknown_numbers]})
            if step is not None:
                step.end()
        except Exception as exc:
            self._fail("summary", exc)

    def score(self, trace_id, name, value, comment=None):
        if not self.enabled or trace_id is None:
            return False
        try:
            self._client.create_score(name=name, value=float(value), trace_id=trace_id,
                                      data_type="NUMERIC", comment=comment)
            return True
        except Exception as exc:
            self._fail("score", exc)
            return False

    def end_trace(self, trace_id, output, tags=None):
        if not self.enabled or trace_id is None:
            return None
        try:
            st = self._traces.get(trace_id)
            if st is None:
                return None
            root = st["root"]
            root.update(output=output)
            if tags:
                # the final tags (status, config name) go on a closing step; propagate_attributes only
                # reaches spans created after it, so the root keeps the tags it was started with
                st["attrs"]["tags"] = list(tags)
                with self._propagate(st["attrs"], tags=tags):
                    root.start_observation(name="trace result", as_type="event",
                                           output={"tags": list(tags)})  # events end themselves
            root.end()
        except Exception as exc:
            self._fail("end_trace", exc)

    def flush(self):
        if not self.enabled:
            return None
        try:
            self._client.flush()
        except Exception as exc:
            self._fail("flush", exc)


class _GuardedStep:
    def __init__(self, step):
        self._step = step

    def finish(self, *args, **kwargs):
        try:
            return self._step.finish(*args, **kwargs)
        except Exception as exc:
            log.warning("tracing: step.finish raised %s; ignored", type(exc).__name__)

    def fail(self, exc):
        try:
            return self._step.fail(exc)
        except Exception as inner:
            log.warning("tracing: step.fail raised %s; ignored", type(inner).__name__)


class _Guarded:
    """Wraps any tracer object so that no method can raise (a failing method returns None/False)."""

    def __init__(self, tracer):
        self._tracer = tracer

    @property
    def status(self) -> str:
        try:
            return str(self._tracer.status)
        except Exception:
            return "tracing off: tracer failed"

    @property
    def enabled(self) -> bool:
        try:
            return bool(self._tracer.enabled)
        except Exception:
            return False

    def __getattr__(self, name):
        if name not in METHODS:
            raise AttributeError(name)

        def call(*args, **kwargs):
            try:
                out = getattr(self._tracer, name)(*args, **kwargs)
                return _GuardedStep(out) if name in ("model_call", "safety_check") else out
            except Exception as exc:
                log.warning("tracing: %s raised %s; ignored", name, type(exc).__name__)
                if name in ("model_call", "safety_check"):
                    return NullStep()
                return False if name == "score" else None
        return call


def guarded(tracer) -> _Guarded:
    """tracer=None means NullTracer. The result never raises."""
    return _Guarded(tracer if tracer is not None else NullTracer())


def get_tracer(environ=None, client_factory=None):
    """LangfuseTracer if all three variables are set and the client starts, else NullTracer.

    environ / client_factory are for tests. The client is created from the variables; nothing is sent
    here (the SDK sends in the background). The keys are never logged."""
    if environ is None:
        try:
            from dotenv import load_dotenv
            load_dotenv(PROJECT_ROOT / ".env")
        except Exception:
            pass
        environ = os.environ
    public, secret = environ.get(ENV_PUBLIC), environ.get(ENV_SECRET)
    url = environ.get(ENV_URL) or environ.get(ENV_URL_OLD)  # LANGFUSE_HOST: deprecated name, still accepted
    if not (public and secret and url):
        return NullTracer("no keys")
    try:
        if client_factory is None:
            from langfuse import Langfuse
            client_factory = Langfuse
        client = client_factory(public_key=public, secret_key=secret, base_url=url)
    except Exception as exc:
        log.warning("tracing: the Langfuse client failed to start (%s)", type(exc).__name__)
        return NullTracer("client failed to start")
    return LangfuseTracer(client, secrets=[environ.get(n) or os.environ.get(n) for n in SECRET_ENV_NAMES])
