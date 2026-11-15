"""
Local copy of every Yes / No click (D45): one JSON line per click in app_data/feedback.jsonl (the folder is in
.gitignore). It fails open: a write error is logged as one warning line and never raises, so it can never
break the page. The Langfuse score is separate (tracing.py); this file also records clicks when tracing is off.

Fields: timestamp (UTC, ISO), session_id, trace_id (or null), status, question, value (1 or 0).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_PATH = PROJECT_ROOT / "app_data" / "feedback.jsonl"

log = logging.getLogger("app.feedback")


def append_feedback(session_id, trace_id, status, question, value, path=None) -> bool:
    """Append one line. True if it was written, False if not (never raises)."""
    try:
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "session_id": session_id,
                  "trace_id": trace_id, "status": status, "question": question, "value": int(value)}
        target = Path(path if path is not None else FEEDBACK_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception as exc:
        log.warning("feedback: could not write %s (%s)", path or FEEDBACK_PATH, type(exc).__name__)
        return False
