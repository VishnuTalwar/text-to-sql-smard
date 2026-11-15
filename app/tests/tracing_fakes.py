"""Fake tracers for the tests (D45). No network, no Langfuse."""

from tracing import METHODS


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
