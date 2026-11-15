"""
The optional "AI summary" sentence (D44, part 3). Outside the measured path: it is made after
answer_question() has finished, never in exam runs, and it fails closed (hidden unless it passes
every check).

  summarize(result)          one extra model call (same model, temperature, seed and prices as the
                             r3b_safe config) for an answered result with 1 to 50 rows. The model sees
                             only the question, the column names and the formatted table (app/format.py).
  extract_numbers(text)      the numbers in a text, as Decimals
  number_check(...)          every number in the sentence must appear in the table, the column names
                             or the question; banned words (number words, "twice", "half", ...) fail
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from functools import partial

import tracing
from answer import DEFAULT_CONFIG, AnswerResult, _resolve_config, grader_run, traced_model_caller
from format import format_table

MAX_ROWS = 50
MAX_SENTENCES = 2
MAX_WORDS = 60

INSTRUCTIONS = (
    "Write one sentence that answers the question using only the table below. "
    "Copy every number exactly as it is written in the table, with the same digits, commas and "
    "decimals. Do not round, convert, add, subtract or compare numbers. Do not write numbers as "
    "words. Do not mention units. If the table cannot answer the question, write: "
    "The table does not answer this question directly. Reply in the language of the question."
)

BANNED_WORDS = (
    # quantity words that hide a calculation (English, German)
    "twice", "double", "half", "triple", "thrice", "dozen", "hundred", "thousand",
    "million", "billion", "doppelt", "halb", "hälfte", "haelfte", "dreimal", "hundert", "tausend",
    "millionen", "milliarde", "milliarden",
    # number words one to twelve
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "eins", "zwei", "drei", "vier", "fünf", "fuenf", "sechs", "sieben", "acht", "neun",
    "zehn", "elf", "zwölf", "zwoelf",
)
_BANNED_RE = re.compile(r"(?<!\w)(" + "|".join(sorted(set(BANNED_WORDS), key=len, reverse=True)) + r")(?!\w)",
                        re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
_MINUS = "-−"


# ---------------------------------------------------------------- numbers

def extract_numbers(text: str) -> list[Decimal]:
    """Numbers in the text: digits with optional ",ddd" groups and an optional ".d+" part. Commas are
    removed and leading zeros do not matter ("07" == 7). A "-" or "−" directly before a number makes
    it negative only if the character before the minus is not a digit (so "2025-07-01" is 2025, 7, 1).
    A "%" is ignored."""
    out = []
    for m in _NUMBER_RE.finditer(text):
        try:
            value = Decimal(m.group(0).replace(",", ""))
        except InvalidOperation:
            continue
        i = m.start()
        if i >= 1 and text[i - 1] in _MINUS and not (i >= 2 and text[i - 2].isdigit()):
            value = -value
        out.append(value)
    return out


def banned_words(sentence: str, question: str = "") -> list[str]:
    """Banned words found in the sentence (whole words, any letter case), in order of appearance.
    A banned word that the question itself contains (same whole-word rule) is allowed."""
    in_question = {m.group(0).lower() for m in _BANNED_RE.finditer(question)}
    return [m.group(0) for m in _BANNED_RE.finditer(sentence) if m.group(0).lower() not in in_question]


def number_check(sentence: str, table_strings, question: str, columns=()) -> tuple[bool, list]:
    """(ok, unknown). ok only if the sentence has no banned word and every number in it appears among
    the numbers of the formatted table cells (table_strings: strings or lists of strings), the
    column names (columns) or the question. unknown lists the banned words (as text) and the
    numbers (as Decimals) that failed."""
    known: set[Decimal] = set()
    flat = []
    for item in table_strings:
        flat.extend(item if isinstance(item, (list, tuple)) else [item])
    for text in [*flat, *columns, question]:
        known.update(extract_numbers(str(text)))
    unknown: list = banned_words(sentence, question)
    unknown += [n for n in extract_numbers(sentence) if n not in known]
    return (not unknown), unknown


# ---------------------------------------------------------------- the summary

@dataclass
class Summary:
    text: str | None
    shown: bool
    hidden_reason: str | None = None   # not_answered | too_many_rows | number_check | banned_word | too_long | model_error
    unknown_numbers: list = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


def _table_text(columns, formatted) -> str:
    lines = [" | ".join(columns)] + [" | ".join(row) for row in formatted]
    return "\n".join(lines)


def build_messages(question: str, columns, formatted) -> list[dict]:
    content = (f"{INSTRUCTIONS}\n\nQuestion: {question}\n\nTable:\n{_table_text(columns, formatted)}")
    return [{"role": "user", "content": content}]


def _too_long(text: str) -> bool:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return len(sentences) > MAX_SENTENCES or len(text.split()) > MAX_WORDS


def summarize(result: AnswerResult, model_caller=None, tracer=None) -> Summary:
    """One summary sentence for an answered result, or a Summary with shown=False and the reason.

    tracer (D45): the model call and the number check are recorded as steps on the SAME trace as the
    answer (result.trace_id), then the tracer is flushed. Guarded: a failing tracer changes nothing."""
    t = tracing.guarded(tracer)
    trace_id = result.trace_id

    summ = _summarize(result, model_caller,
                      lambda llm: traced_model_caller(llm, t, trace_id, {"step": "summary"}))
    t.summary(trace_id, summ.shown, summ.hidden_reason, summ.unknown_numbers)
    t.flush()
    return summ


def _summarize(result: AnswerResult, model_caller=None, wrap=None) -> Summary:
    if result.status != "answered":
        return Summary(None, False, "not_answered")
    if not (1 <= result.row_count <= MAX_ROWS):
        return Summary(None, False, "too_many_rows")

    cfg, _ = grader_run.load_config(_resolve_config(DEFAULT_CONFIG))
    llm = model_caller or partial(grader_run.call_openai, model=cfg["model"],
                                  temperature=cfg["temperature"], seed=cfg["seed"])
    if wrap is not None:
        llm = wrap(llm)  # the model call becomes a traced step (D45); nothing else changes
    formatted = format_table(result.columns, result.rows)
    prompt_tokens = completion_tokens = 0
    cost = 0.0

    def tally(call):
        nonlocal prompt_tokens, completion_tokens, cost
        prompt_tokens = call.get("prompt_tokens") or 0
        completion_tokens = call.get("completion_tokens") or 0
        cost = round((prompt_tokens * grader_run.PRICE_INPUT_PER_M
                      + completion_tokens * grader_run.PRICE_OUTPUT_PER_M) / 1_000_000, 6)

    try:
        call = llm(build_messages(result.question, result.columns, formatted))
        tally(call)
        text = call["raw_model_output"].strip()
        if not text:
            raise ValueError("empty reply")
    except Exception:
        return Summary(None, False, "model_error", [], prompt_tokens, completion_tokens, cost)

    def hide(reason, unknown=()):
        return Summary(None, False, reason, list(unknown), prompt_tokens, completion_tokens, cost)

    if _too_long(text):
        return hide("too_long")
    banned = banned_words(text, result.question)
    if banned:
        return hide("banned_word", banned)
    ok, unknown = number_check(text, formatted, result.question, result.columns)
    if not ok:
        return hide("number_check", unknown)
    return Summary(text, True, None, [], prompt_tokens, completion_tokens, cost)
