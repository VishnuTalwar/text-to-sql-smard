"""
CLI script: runs the schema-linked agent against all 84 questions, grades
with comparator.py + executor.py, and reports per-tier results alongside
which tables catalog_retriever selected per question.

This produces the ablation table's "+ schema linking" row.

Model, LLM-calling logic (naive_agent.answer), executor, comparator, and
loader are all unchanged from run_baseline.py — only the prompt changes.
The naive_agent module is imported here solely for its answer() function;
that function calls build_prompt() which we patch at import time so it
resolves to prompt_template_schema_linked.build_prompt instead of the
baseline's prompt_template.build_prompt.

Output file is written to results/ with a distinct name so the two logs
can be compared directly.
"""

import importlib
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Redirect naive_agent's prompt builder BEFORE importing naive_agent.
#
# naive_agent does:   from prompt_template import build_prompt
# We want it to use: prompt_template_schema_linked.build_prompt
#
# Strategy: inject a fake "prompt_template" module into sys.modules that
# exposes the schema-linked build_prompt. naive_agent.py is then imported
# and gets the patched version without any modification to the file.
# ---------------------------------------------------------------------------
import prompt_template_schema_linked as _sl

# Create a minimal module shim
import types as _types
_shim = _types.ModuleType("prompt_template")
_shim.build_prompt = _sl.build_prompt
sys.modules["prompt_template"] = _shim

# Now safe to import naive_agent — it will call our build_prompt
import naive_agent  # noqa: E402  (must come after shim)

from catalog_retriever import get_relevant_tables
from result_logging import install_recorder, make_record, write_jsonl
from comparator import compare
from executor import QueryError, run_query
from loader import load_questions

# ---------------------------------------------------------------------------
# Logging: INFO level so retriever decisions are captured in the log file
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)

# Observe-only: records raw output, latency and tokens of each API call for the
# .jsonl log. It forwards every request unchanged (see result_logging.py).
_recorder = install_recorder(naive_agent)

TIER_NAMES = {
    0: "Tier 0 (unanswerable)",
    1: "Tier 1 (single aggregate)",
    2: "Tier 2 (grouping/ranking)",
    3: "Tier 3 (dates/comparisons)",
    4: "Tier 4 (hard)",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def _is_valid_sql(sql: str) -> bool:
    if not sql:
        return False
    try:
        run_query(sql)
        return True
    except QueryError:
        return False


def _gold_tables(gold_sql: str | None) -> set[str]:
    """Tables the gold SQL actually references (empty for tier 0)."""
    if not gold_sql:
        return set()
    return set(re.findall(r"\b(erzeugung|verbrauch|preise)\b", gold_sql.lower()))


def _retrieval_missing(question, tables: list[str]) -> set[str]:
    """Tables the gold SQL needs that the retriever did NOT supply."""
    return _gold_tables(question.gold_sql) - set(tables)


def run(tag: str = "") -> int:
    questions = load_questions()
    results = []
    agent_sqls: dict[str, str] = {}
    retrieved_tables: dict[str, list[str]] = {}
    records = []
    valid_count = 0

    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question.id}...", end=" ", flush=True)

        # Capture retriever decision before the LLM call
        tables = get_relevant_tables(question.frage)
        retrieved_tables[question.id] = tables

        _recorder.begin()
        agent_sql = naive_agent.answer(question.frage)
        call = _recorder.take()
        agent_sqls[question.id] = agent_sql
        print("done", flush=True)
        time.sleep(1)  # stay within OpenAI RPM limits across 84 questions

        if _is_valid_sql(agent_sql):
            valid_count += 1

        try:
            result = compare(question, agent_sql)
        except QueryError as exc:
            print(f"FATAL: gold_sql for {question.id} failed to execute: {exc}")
            return 1
        results.append(result)
        records.append(make_record(question, result, agent_sql, call, retrieved_tables=tables))

    _print_report(results, questions, agent_sqls, retrieved_tables, valid_count)
    _save_log(results, questions, agent_sqls, retrieved_tables, valid_count, tag, records)
    return 0 if all(r.passed for r in results) else 1


def _print_report(results, questions, agent_sqls, retrieved_tables, valid_count) -> None:
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)

    print("\n=== Per-tier results (schema-linked) ===")
    for tier in sorted(by_tier):
        tier_results = by_tier[tier]
        passed = sum(1 for r in tier_results if r.passed)
        total = len(tier_results)
        name = TIER_NAMES.get(tier, f"Tier {tier}")
        print(f"{name:32s} {passed:3d}/{total:<3d}")

    total_passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\n{'Overall':32s} {total_passed:3d}/{total:<3d}")
    print(f"{'Valid-SQL rate':32s} {valid_count:3d}/{total:<3d}")

    # -----------------------------------------------------------------------
    # Retrieval analysis — flag cases where the wrong table(s) were selected.
    #
    # "Wrong" is approximated here: if a question failed AND the retriever
    # did NOT return all three tables, that is a candidate retrieval mistake.
    # (If it returned all three and still failed, the catalog content or the
    # model is to blame, not retrieval.)
    # -----------------------------------------------------------------------
    questions_by_id = {q.id: q for q in questions}
    failures = [r for r in results if not r.passed]

    if failures:
        print(f"\n=== Failures ({len(failures)}) ===")
        for r in failures:
            q = questions_by_id[r.question_id]
            agent_sql = agent_sqls[r.question_id]
            tables = retrieved_tables[r.question_id]
            missing = _retrieval_missing(q, tables)
            narrow = bool(missing)
            retrieval_flag = f" ⚠ RETRIEVAL MISS (missing {sorted(missing)})" if narrow else ""
            print(f"\n--- {r.question_id} (tier {r.tier}){retrieval_flag} ---")
            print(f"Retrieved tables: {tables}")
            print(f"Question:         {q.frage}")
            print(f"Gold SQL:         {q.gold_sql.strip() if q.gold_sql else '(none — tier 0)'}")
            print(f"Agent SQL:        {agent_sql if agent_sql else '(empty)'}")
            print(f"Comparator:       {r.reason}")

    # -----------------------------------------------------------------------
    # Retrieval summary: questions where narrow retrieval coincided with a
    # failure (possible retrieval-caused mistakes) vs. all-tables failures
    # (catalog/model-caused).
    # -----------------------------------------------------------------------
    narrow_failures = [
        r for r in failures
        if _retrieval_missing(questions_by_id[r.question_id], retrieved_tables[r.question_id])
    ]
    wide_failures = [r for r in failures if r not in narrow_failures]

    print("\n=== Retrieval analysis ===")
    print(
        f"  Failed AND retriever missed a gold table: {len(narrow_failures)} "
        f"— retrieval-caused candidates"
    )
    print(
        f"  Failed with all gold tables supplied:     {len(wide_failures)} "
        f"— catalog/model issue, not retrieval"
    )
    all_miss = [
        q.id for q in questions
        if _retrieval_missing(q, retrieved_tables[q.id])
    ]
    print(f"  Retrieval misses overall (pass or fail): {all_miss}")


def _save_log(results, questions, agent_sqls, retrieved_tables, valid_count, tag: str = "", records=None) -> None:
    """Write the same report to a timestamped file in results/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    tag = tag or os.environ.get("RUN_TAG", "")
    path = RESULTS_DIR / f"schema_linked{('_' + tag) if tag else ''}_{timestamp}.log"

    questions_by_id = {q.id: q for q in questions}
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)

    lines: list[str] = []
    lines.append("=== Per-tier results (schema-linked) ===")
    for tier in sorted(by_tier):
        tier_results = by_tier[tier]
        passed = sum(1 for r in tier_results if r.passed)
        total = len(tier_results)
        name = TIER_NAMES.get(tier, f"Tier {tier}")
        lines.append(f"{name:32s} {passed:3d}/{total:<3d}")

    total_passed = sum(1 for r in results if r.passed)
    total = len(results)
    lines.append(f"\n{'Overall':32s} {total_passed:3d}/{total:<3d}")
    lines.append(f"{'Valid-SQL rate':32s} {valid_count:3d}/{total:<3d}")

    lines.append("\n=== Per-question retrieval + outcome ===")
    lines.append(f"{'ID':<12} {'Tier':<6} {'Retrieved':<30} {'Pass'}")
    lines.append("-" * 70)
    for r in results:
        tables = retrieved_tables[r.question_id]
        tables_str = ", ".join(tables)
        pass_str = "PASS" if r.passed else f"FAIL ({r.reason})"
        lines.append(f"{r.question_id:<12} {r.tier:<6} {tables_str:<30} {pass_str}")

    lines.append("\n=== Failures ===")
    failures = [r for r in results if not r.passed]
    if not failures:
        lines.append("(none)")
    for r in failures:
        q = questions_by_id[r.question_id]
        agent_sql = agent_sqls[r.question_id]
        tables = retrieved_tables[r.question_id]
        missing = _retrieval_missing(q, tables)
        flag = f" [RETRIEVAL MISS: {sorted(missing)}]" if missing else ""
        lines.append(f"\n--- {r.question_id} (tier {r.tier}){flag} ---")
        lines.append(f"Retrieved: {tables}")
        lines.append(f"Question:  {q.frage}")
        lines.append(f"Gold SQL:  {q.gold_sql.strip() if q.gold_sql else '(none)'}")
        lines.append(f"Agent SQL: {agent_sql if agent_sql else '(empty)'}")
        lines.append(f"Reason:    {r.reason}")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nLog saved to: {path}")
    if records is not None:
        jsonl_path = path.with_suffix(".jsonl")
        write_jsonl(jsonl_path, records)
        print(f"Per-question records saved to: {jsonl_path}")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1, help="number of repeated full runs")
    ap.add_argument("--tag", default="", help="log filename tag prefix")
    args = ap.parse_args()
    codes = []
    for k in range(1, args.runs + 1):
        tag = f"{args.tag + '_' if args.tag else ''}run{k}" if args.runs > 1 or args.tag else ""
        print(f"\n##### run {k}/{args.runs} (tag={tag or '-'}) #####")
        codes.append(run(tag))
    sys.exit(0 if all(c == 0 for c in codes) else 1)


if __name__ == "__main__":
    main()
