"""Fake tracers for the tests (D45). No network, no Langfuse."""

from tracing import METHODS


class RecordingStep:
    """A step handed out by model_call / safety_check. Its finish and fail are recorded on the tracer as
    'model_call.finish', 'model_call.fail', 'safety_check.finish', ..."""

    def __init__(self, tracer, method):
        self.tracer, self.method = tracer, method

    def finish(self, *args, **kwargs):
        self.tracer.calls.append((f"{self.method}.finish", args, kwargs))

    def fail(self, exc):
        self.tracer.calls.append((f"{self.method}.fail", (exc,), {}))


class RecordingTracer:
    """Records every call as (method, args, kwargs). start_trace returns 'trace-1', 'trace-2', ..."""

    enabled = True
    status = "tracing on"

    def __init__(self):
        self.calls = []
        self._n = 0

    def of(self, method):
        return [(a, k) for m, a, k in self.calls if m == method]

    def _record(self, method):
        def call(*args, **kwargs):
            self.calls.append((method, args, kwargs))
            if method == "start_trace":
                self._n += 1
                return f"trace-{self._n}"
            if method == "score":
                return True
            if method in ("model_call", "safety_check"):
                return RecordingStep(self, method)
            return None
        return call

    def __getattr__(self, name):
        if name in METHODS:
            return self._record(name)
        raise AttributeError(name)


class RaisingTracer:
    """Every method raises (also the status properties)."""

    @property
    def status(self):
        raise RuntimeError("status")

    @property
    def enabled(self):
        raise RuntimeError("enabled")

    def __getattr__(self, name):
        if name in METHODS:
            def call(*args, **kwargs):
                raise RuntimeError(f"{name} failed")
            return call
        raise AttributeError(name)


class RaisingStepTracer(RecordingTracer):
    """Hands out steps whose finish and fail raise."""

    def _record(self, method):
        inner = super()._record(method)

        def call(*args, **kwargs):
            out = inner(*args, **kwargs)
            if isinstance(out, RecordingStep):
                def boom(*a, **k):
                    raise RuntimeError("step failed")
                out.finish = out.fail = boom
            return out
        return call
