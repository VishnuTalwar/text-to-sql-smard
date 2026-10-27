"""
Prompt for ablation row v2b: the decline prompt rendered from catalog v2b.

The table renderer below is the one in prompt_template_schema_linked.py, line for
line, with one addition: after a column's "values:" line it prints a "Value meanings:"
section if the catalog entry has "value_meanings" for that column. Tables without
value_meanings (erzeugung) are therefore rendered byte for byte as before.

The prompt layout (table blocks, question, final instruction) is the decline prompt's:
the final instruction is imported from prompt_template_decline, not copied.
No existing file is modified.
"""

from catalog_retriever import get_relevant_tables
from prompt_template_decline import DECLINE_INSTRUCTION
from schema_catalog_v2b import CATALOG


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
        meanings = entry.get("value_meanings", {}).get(col_name)
        if meanings:
            lines.append("  Value meanings:")
            for m in meanings:
                lines.append(f"    • {m}")

    quirks = entry.get("quirks", [])
    if quirks:
        lines.append("  Data quirks:")
        for q in quirks:
            lines.append(f"    • {q}")

    return "\n".join(lines)


def build_prompt(question: str) -> str:
    tables = get_relevant_tables(question)
    schema_block = "\n\n".join(_render_table(t) for t in tables)

    return (
        f"{schema_block}\n"
        f"\n"
        f"Question: {question}\n"
        f"\n"
        f"{DECLINE_INSTRUCTION}"
    )
