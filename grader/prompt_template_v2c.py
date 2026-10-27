"""
Prompt for ablation row v2c: the v2b prompt with ONE line added at the very top,
stating the date range of the data.

The line (plus one blank line after it) comes before the first table block.
Everything else is produced by prompt_template_v2b.build_prompt, unchanged, so the
v2c prompt is the v2b prompt with only that line in front of it.

No existing file is modified.
"""

from prompt_template_v2b import build_prompt as _build_v2b_prompt

COVERAGE_LINE = (
    "Data coverage: all three tables cover 2023-06-01 00:00 to 2026-06-01 23:45 in 15-minute steps. "
    "There is no data before 2023-06-01 or after 2026-06-01, and June 2026 has only one day (2026-06-01)."
)


def build_prompt(question: str) -> str:
    return f"{COVERAGE_LINE}\n\n{_build_v2b_prompt(question)}"
