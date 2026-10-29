"""
CLI script: ablation row v2b2 = row v2b with ONE sentence of the catalog changed
(schema_catalog_v2b2.py): in the preise value meanings, the ∅ Anrainer DE/LU entry now
ends "Leave it out when ranking or comparing countries." instead of "... zones.".

Everything else is identical to run_v2b.py: same prompt template (prompt_template_v2b,
no date line), model, temperature, seed, retriever, decline handling, executor,
comparator and loader. This row builds on v2b, NOT on v2c.

How the v2b2 catalog is plugged in: prompt_template_v2b renders tables from its
module-level CATALOG, looked up at call time, so we point that name at
schema_catalog_v2b2.CATALOG. No existing file is edited.

Decline handling: if the reply (whitespace and code fences already stripped by
naive_agent) starts with NO_QUERY, in any letter case, it is a decline = no SQL.
  - tier 0: no SQL passes (comparator, unchanged).
  - tiers 1-4: no SQL fails (comparator, unchanged); only the reason text is
    replaced here with "declined (no SQL)" so wrong declines can be counted.

Logs are written to results/v2b2<_tag>_<date>.log and .jsonl.
"""

import logging
import os
import re
import sys
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import naive_agent
import prompt_template_v2b
import schema_catalog_v2b2

# prompt_template_v2b renders tables from its module-level CATALOG, looked up at
# call time, so this swaps in the v2b2 catalog.
prompt_template_v2b.CATALOG = schema_catalog_v2b2.CATALOG
# naive_agent.answer() looks up build_prompt at call time, so this swaps the prompt.
naive_agent.build_prompt = prompt_template_v2b.build_prompt

from catalog_retriever import get_relevant_tables
from comparator import compare
from executor import QueryError, run_query
from loader import load_questions
from result_logging import install_recorder, make_record, write_jsonl

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)

# Observe-only: records raw output, latency and tokens of each API call for the
# .jsonl log. It forwards every request unchanged (see result_logging.py).
_recorder = install_recorder(naive_agent)

DECLINE_MARKER = "NO_QUERY"
DECLINED_REASON = "declined (no SQL)"

TIER_NAMES = {
    0: "Tier 0 (unanswerable)",
    1: "Tier 1 (single aggregate)",
    2: "Tier 2 (grouping/ranking)",
    3: "Tier 3 (dates/comparisons)",
    4: "Tier 4 (hard)",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def is_decline(reply: str) -> bool:
    """True if the reply is a decline, ignoring case (NO_QUERY, no_query, No_Query...).
    naive_agent.answer() has already stripped whitespace and any code fence, so a
    fenced NO_QUERY is covered too."""
    return reply.strip().upper().startswith(DECLINE_MARKER)


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
    replies: dict[str, str] = {}  # full model reply for declined questions
    retrieved_tables: dict[str, list[str]] = {}
    records = []
    valid_count = 0

    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question.id}...", end=" ", flush=True)

        # Capture retriever decision before the LLM call
        tables = get_relevant_tables(question.frage)
        retrieved_tables[question.id] = tables

        _recorder.begin()
        reply = naive_agent.answer(question.frage)
        call = _recorder.take()
        declined = is_decline(reply)
        agent_sql = "" if declined else reply
        agent_sqls[question.id] = agent_sql
        if declined:
            replies[question.id] = reply
        print("declined" if declined else "done", flush=True)
        time.sleep(1)  # stay within OpenAI RPM limits across 84 questions

        if _is_valid_sql(agent_sql):
            valid_count += 1

        try:
            result = compare(question, agent_sql)
        except QueryError as exc:
            print(f"FATAL: gold_sql for {question.id} failed to execute: {exc}")
            return 1
        if declined and not result.passed:
            result = replace(result, reason=DECLINED_REASON)
        results.append(result)
        records.append(
            make_record(question, result, None if declined else agent_sql, call, retrieved_tables=tables)
        )

    _print_report(results, questions, agent_sqls, replies, retrieved_tables, valid_count)
    _save_log(results, questions, agent_sqls, replies, retrieved_tables, valid_count, tag, records)
    return 0 if all(r.passed for r in results) else 1


def _decline_counts(results, replies) -> tuple[int, int, int]:
    """(tier 0 declined, tier 0 total, tiers 1-4 declined)."""
    t0 = [r for r in results if r.tier == 0]
    t0_declined = sum(1 for r in t0 if r.question_id in replies)
    wrong = sum(1 for r in results if r.tier != 0 and r.question_id in replies)
    return t0_declined, len(t0), wrong


def _print_report(results, questions, agent_sqls, replies, retrieved_tables, valid_count) -> None:
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)

    print("\n=== Per-tier results (v2b2: v2b + Anrainer wording) ===")
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
    t0_declined, t0_total, wrong = _decline_counts(results, replies)
    print(f"{'Declines: tier 0 correct':32s} {t0_declined:3d}/{t0_total:<3d}")
    print(f"{'Declines: tiers 1-4 (wrong)':32s} {wrong:3d}")

    questions_by_id = {q.id: q for q in questions}
    failures = [r for r in results if not r.passed]

    if failures:
        print(f"\n=== Failures ({len(failures)}) ===")
        for r in failures:
            q = questions_by_id[r.question_id]
            agent_sql = agent_sqls[r.question_id]
            tables = retrieved_tables[r.question_id]
            missing = _retrieval_missing(q, tables)
            retrieval_flag = f" ⚠ RETRIEVAL MISS (missing {sorted(missing)})" if missing else ""
            print(f"\n--- {r.question_id} (tier {r.tier}){retrieval_flag} ---")
            print(f"Retrieved tables: {tables}")
            print(f"Question:         {q.frage}")
            print(f"Gold SQL:         {q.gold_sql.strip() if q.gold_sql else '(none — tier 0)'}")
            print(f"Agent SQL:        {agent_sql if agent_sql else '(empty)'}")
            if r.question_id in replies:
                print(f"Model reply:      {replies[r.question_id]}")
            print(f"Comparator:       {r.reason}")

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


def _save_log(results, questions, agent_sqls, replies, retrieved_tables, valid_count,
              tag: str = "", records=None) -> None:
    """Write the same report to a timestamped file in results/ (same layout as
    run_v2b.py)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    tag = tag or os.environ.get("RUN_TAG", "")
    path = RESULTS_DIR / f"v2b2{('_' + tag) if tag else ''}_{timestamp}.log"

    questions_by_id = {q.id: q for q in questions}
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)

    lines: list[str] = []
    lines.append("=== Per-tier results (v2b2: v2b + Anrainer wording) ===")
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
    t0_declined, t0_total, wrong = _decline_counts(results, replies)
    lines.append(f"{'Declines: tier 0 correct':32s} {t0_declined:3d}/{t0_total:<3d}")
    lines.append(f"{'Declines: tiers 1-4 (wrong)':32s} {wrong:3d}")

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
        if r.question_id in replies:
            lines.append(f"Reply:     {replies[r.question_id]}")
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
