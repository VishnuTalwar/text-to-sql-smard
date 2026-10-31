"""
Prompt for ablation row df (decline fix): the v2b prompt with a new final instruction.

Everything before the final instruction (table blocks, value meanings, quirks, the
question) is produced by prompt_template_v2b.build_prompt itself, so it cannot drift
from v2b. The only change is DF_INSTRUCTION replacing the decline prompt's
DECLINE_INSTRUCTION. If v2b ever stops ending with that instruction, build_prompt()
fails loudly instead of silently building a different prompt.

No existing file is modified.
"""

from prompt_template_decline import DECLINE_INSTRUCTION as _V2B_INSTRUCTION
from prompt_template_v2b import build_prompt as _build_v2b_prompt

DF_INSTRUCTION = (
    "If the information the question needs is not in the tables above at all, "
    "or a note above says those values are missing, "
    "do not guess and do not write a query. "
    "Instead reply with exactly: NO_QUERY: <one short sentence saying what information is missing>. "
    "Anything that can be worked out from the tables counts as available, "
    "including parts of zeitpunkt (year, month, day, weekday, hour) "
    "and results of grouping, counting, sorting, comparing or combining tables. "
    "If the question leaves a detail open, such as the time period, "
    "use the most natural reading (for example, all the data) instead of declining. "
    "Otherwise, return exactly one PostgreSQL SELECT statement that answers the question. "
    "Return only the SQL — no markdown code fences, no explanation, no other text."
)


def build_prompt(question: str) -> str:
    base = _build_v2b_prompt(question)
    if not base.endswith(_V2B_INSTRUCTION):
        raise RuntimeError(
            "prompt_template_v2b no longer ends with the decline instruction; "
            "update _V2B_INSTRUCTION here."
        )
    return base[: -len(_V2B_INSTRUCTION)] + DF_INSTRUCTION
