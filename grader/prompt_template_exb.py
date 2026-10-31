"""
Prompt for ablation row ex-b: the v2b prompt plus the 3 few-shot examples most similar
to the question (example_retriever.retrieve, most similar last).

Same as prompt_template_exa.py: same header line, same position (after the schema
section, directly before the "Question: <question>" line), same example format; only
the examples differ per question instead of being the fixed 8. Everything else comes
from prompt_template_v2b.build_prompt, and build_prompt() below fails loudly if its
layout changes.
"""

import example_retriever
import prompt_template_v2b
from prompt_template_exa import EXAMPLES_HEADER


def examples_block(question: str) -> str:
    parts = []
    for item, _score in example_retriever.retrieve(question):
        parts.append(f"Question: {item['frage'].strip()}\nSQL:\n{item['gold_sql'].strip()}")
    return EXAMPLES_HEADER + "\n\n" + "\n\n".join(parts)


def build_prompt(question: str) -> str:
    base = prompt_template_v2b.build_prompt(question)
    marker = f"\n\nQuestion: {question}\n\n"
    if base.count(marker) != 1:
        raise RuntimeError(
            "prompt_template_v2b layout changed: expected exactly one "
            "'Question: <question>' line; update prompt_template_exb.py."
        )
    head, tail = base.split(marker)
    return f"{head}\n\n{examples_block(question)}{marker}{tail}"
