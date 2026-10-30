"""
Prompt for ablation row ex-a: the v2b prompt plus a block of few-shot examples.

The prompt is prompt_template_v2b.build_prompt with exactly one insertion: the
examples block goes after the schema/catalog section and directly before the
"Question: <question>" line (so the real question and the final decline instruction
stay together at the end). Everything else is produced by the v2b builder itself, so
it cannot drift; if the v2b layout changes, build_prompt() below fails loudly.

The examples are read from example_bank.yaml at runtime, in the order EXAMPLE_IDS.
A missing id, or an example without gold_sql, raises.
"""

from pathlib import Path

import yaml

import prompt_template_v2b

EXAMPLE_BANK = Path(__file__).resolve().parent.parent / "example_bank.yaml"
EXAMPLE_IDS = ["ex_06", "ex_07", "ex_11", "ex_13", "ex_16", "ex_20", "ex_24", "ex_26"]
EXAMPLES_HEADER = "Examples (they show the expected answer style; the notes above still apply):"


def _load_examples_block() -> str:
    with open(EXAMPLE_BANK, "r", encoding="utf-8") as f:
        items = {it["id"]: it for it in yaml.safe_load(f)["fragen"]}
    missing = [i for i in EXAMPLE_IDS if i not in items]
    if missing:
        raise RuntimeError(f"{EXAMPLE_BANK.name}: example id(s) not found: {missing}")
    parts = []
    for i in EXAMPLE_IDS:
        sql = items[i].get("gold_sql")
        if not (isinstance(sql, str) and sql.strip()):
            raise RuntimeError(f"{EXAMPLE_BANK.name}: {i} has no gold_sql")
        parts.append(f"Question: {items[i]['frage'].strip()}\nSQL:\n{sql.strip()}")
    return EXAMPLES_HEADER + "\n\n" + "\n\n".join(parts)


EXAMPLES_BLOCK = _load_examples_block()


def build_prompt(question: str) -> str:
    base = prompt_template_v2b.build_prompt(question)
    marker = f"\n\nQuestion: {question}\n\n"
    if base.count(marker) != 1:
        raise RuntimeError(
            "prompt_template_v2b layout changed: expected exactly one "
            "'Question: <question>' line; update prompt_template_exa.py."
        )
    head, tail = base.split(marker)
    return f"{head}\n\n{EXAMPLES_BLOCK}{marker}{tail}"
