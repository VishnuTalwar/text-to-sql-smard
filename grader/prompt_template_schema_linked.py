"""
Schema-linked prompt: injects only the catalog entries for tables that
catalog_retriever deems relevant to this question.

This is the "+ schema linking" ablation row in PROJECT.md section 8.

Differences from prompt_template.py (the naive baseline):
- Schema is per-table and selective (only relevant tables included).
- Each table block carries: purpose sentence, column types + examples,
  closed categorical values, and explicit data quirks.
- Prompt wording for the output instruction is identical to the naive
  version so that difference cannot explain score differences.

naive_agent.py is not modified — it calls build_prompt() by name, and
run_schema_linked.py imports this module's build_prompt() instead.
"""

from schema_catalog import CATALOG
from catalog_retriever import get_relevant_tables


def _render_table(table_name: str) -> str:
    """Render one table's catalog entry as a self-contained text block."""
    entry = CATALOG[table_name]
    lines: list[str] = []

    lines.append(f"Table: {table_name}")
    lines.append(f"  Purpose: {entry['purpose']}")

    lines.append("  Columns:")
    for col in entry["columns"]:
        examples_str = ", ".join(col["examples"])
        lines.append(f"    {col['name']}  ({col['type']})  — e.g. {examples_str}")

    for col_name, vals in entry.get("values", {}).items():
        vals_str = ", ".join(vals)
        lines.append(f"  {table_name}.{col_name} values: {vals_str}")

    quirks = entry.get("quirks", [])
    if quirks:
        lines.append("  Data quirks:")
        for q in quirks:
            lines.append(f"    • {q}")

    return "\n".join(lines)


def build_prompt(question: str) -> str:
    """Build a schema-linked prompt for *question*.

    Only the catalog entries for the tables returned by catalog_retriever
    are included. If the retriever returns all three tables the prompt is
    complete; if it returns one or two it is smaller and more focused.
    """
    tables = get_relevant_tables(question)
    schema_block = "\n\n".join(_render_table(t) for t in tables)

    return (
        f"{schema_block}\n"
        f"\n"
        f"Question: {question}\n"
        f"\n"
        f"Return exactly one PostgreSQL SELECT statement that answers the question. "
        f"Return only the SQL — no markdown code fences, no explanation, no other text."
    )
