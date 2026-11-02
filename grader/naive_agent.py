"""
Naive baseline agent: one LLM call, no retry, no validation, no repair.

Model is fixed at gpt-4o for every future ablation stage (schema linking,
few-shot, validation/retry) so the ablation table measures the pipeline
changing, not the model changing — see PROJECT.md sections 8 and 11.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from prompt_template import build_prompt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL = "gpt-4o-2024-08-06"  # dated snapshot, pinned in D36 (the alias "gpt-4o" can move)
SEED = 0  # best-effort determinism; OpenAI treats seed as non-guaranteed


def _strip_fences(text: str) -> str:
    """Strip a leading/trailing markdown code fence if the model added one
    despite being told not to. Does not otherwise touch the SQL."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        lines = lines[1:]  # drop the opening ``` or ```sql line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def answer(question: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": build_prompt(question)}],
        temperature=0,
        seed=SEED,
    )
    raw = response.choices[0].message.content
    return _strip_fences(raw)
