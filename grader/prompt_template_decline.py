"""
Decline variant of the schema-linked prompt.

This is the "+ decline option" ablation row. The prompt is the schema-linked
prompt (prompt_template_schema_linked.build_prompt) with exactly one change:
the final instruction, which now starts with a decline option and then repeats
the schema-linked instruction word for word (only "Return" becomes "return"
after "Otherwise,"). Everything before that instruction (table blocks,
notes, the question) is produced by the schema-linked builder itself, so it
cannot drift from the schema-linked setup.

prompt_template_schema_linked.py is not modified.
"""

from prompt_template_schema_linked import build_prompt as _build_schema_linked_prompt

# The schema-linked final instruction, copied verbatim so it can be swapped out.
# If prompt_template_schema_linked.py ever changes it, build_prompt() below fails
# loudly instead of silently building a different prompt.
_SCHEMA_LINKED_INSTRUCTION = (
    "Return exactly one PostgreSQL SELECT statement that answers the question. "
    "Return only the SQL — no markdown code fences, no explanation, no other text."
)

DECLINE_INSTRUCTION = (
    "If the question cannot be answered using the tables and columns above, "
    "do not guess and do not write a query. "
    "Instead reply with exactly: NO_QUERY: <one short sentence saying what information is missing>. "
    "Otherwise, return exactly one PostgreSQL SELECT statement that answers the question. "
    "Return only the SQL — no markdown code fences, no explanation, no other text."
)


def build_prompt(question: str) -> str:
    base = _build_schema_linked_prompt(question)
    if not base.endswith(_SCHEMA_LINKED_INSTRUCTION):
        raise RuntimeError(
            "prompt_template_schema_linked no longer ends with the expected final "
            "instruction; update _SCHEMA_LINKED_INSTRUCTION here."
        )
    return base[: -len(_SCHEMA_LINKED_INSTRUCTION)] + DECLINE_INSTRUCTION
