"""
CLI script: runs the naive baseline agent (one LLM call, no retry, no
validation) against all 84 questions, grades with comparator.py, and reports
per-tier results, valid-SQL rate, and a readable failure dump.

This produces exactly one number for the ablation table's first row —
naive execution accuracy — per PROJECT.md sections 8 and 11.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from comparator import compare
from executor import QueryError, run_query
from loader import load_questions
import naive_agent
from naive_agent import answer
from result_logging import install_recorder, make_record, write_jsonl

TIER_NAMES = {
    0: "Tier 0 (unanswerable)",
    1: "Tier 1 (single aggregate)",
    2: "Tier 2 (grouping/ranking)",
    3: "Tier 3 (dates/comparisons)",
    4: "Tier 4 (hard)",
}


def _is_valid_sql(sql: str) -> bool:
    """Did it execute at all, regardless of whether the answer was correct?
    A tier-0 question correctly answered with no SQL counts as not-valid-SQL
    here (there's nothing to execute), which is expected and fine — this
    metric is orthogonal to pass/fail, per PROJECT.md section 8."""
    if not sql:
        return False
    try:
        run_query(sql)
        return True
    except QueryError:
        return False


# Observe-only: records raw output, latency and tokens of each API call for the
# .jsonl log. It forwards every request unchanged (see result_logging.py).
_recorder = install_recorder(naive_agent)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def run(tag: str = "") -> int:
    questions = load_questions()
    results = []
    agent_sqls = {}
    records = []
    valid_count = 0

    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question.id}...", end=" ", flush=True)
        _recorder.begin()
        agent_sql = answer(question.frage)
        call = _recorder.take()
        agent_sqls[question.id] = agent_sql
        print("done", flush=True)

        if _is_valid_sql(agent_sql):
            valid_count += 1

        try:
            result = compare(question, agent_sql)
        except QueryError as exc:
            print(f"FATAL: gold_sql for {question.id} failed to execute: {exc}")
            return 1
        results.append(result)
        records.append(make_record(question, result, agent_sql, call))

    _print_report(results, questions, agent_sqls, valid_count)
    _save_log(results, questions, agent_sqls, valid_count, tag, records)
    return 0 if all(r.passed for r in results) else 1


def _save_log(results, questions, agent_sqls, valid_count, tag: str = "", records=None) -> None:
    """Write per-tier scores, per-question outcome and failures to results/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    path = RESULTS_DIR / f"baseline_naive{('_' + tag) if tag else ''}_{date}.log"
    questions_by_id = {q.id: q for q in questions}
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)

    lines = ["=== Per-tier results ==="]
    for tier in sorted(by_tier):
        passed = sum(1 for r in by_tier[tier] if r.passed)
        lines.append(f"{TIER_NAMES.get(tier, f'Tier {tier}'):32s} {passed:3d}/{len(by_tier[tier]):<3d}")
    total_passed = sum(1 for r in results if r.passed)
    lines.append(f"\n{'Overall':32s} {total_passed:3d}/{len(results):<3d}")
    lines.append(f"{'Valid-SQL rate':32s} {valid_count:3d}/{len(results):<3d}")

    lines.append("\n=== Per-question outcome ===")
    for r in results:
        lines.append(f"{r.question_id:<12} {r.tier:<6} {'PASS' if r.passed else 'FAIL (' + r.reason + ')'}")

    lines.append("\n=== Failures ===")
    for r in (r for r in results if not r.passed):
        q = questions_by_id[r.question_id]
        lines.append(f"\n--- {r.question_id} (tier {r.tier}) ---")
        lines.append(f"Question:  {q.frage}")
        lines.append(f"Gold SQL:  {q.gold_sql.strip() if q.gold_sql else '(none)'}")
        lines.append(f"Agent SQL: {agent_sqls[r.question_id] or '(empty)'}")
        lines.append(f"Reason:    {r.reason}")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nLog saved to: {path}")
    if records is not None:
        jsonl_path = path.with_suffix(".jsonl")
        write_jsonl(jsonl_path, records)
        print(f"Per-question records saved to: {jsonl_path}")


def _print_report(results, questions, agent_sqls, valid_count) -> None:
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)

    print("\n=== Per-tier results ===")
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

    questions_by_id = {q.id: q for q in questions}
    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\n=== Failures ({len(failures)}) ===")
        for r in failures:
            q = questions_by_id[r.question_id]
            agent_sql = agent_sqls[r.question_id]
            print(f"\n--- {r.question_id} (tier {r.tier}) ---")
            print(f"Question:  {q.frage}")
            print(f"Gold SQL:  {q.gold_sql.strip() if q.gold_sql else '(none — tier 0, unanswerable)'}")
            print(f"Agent SQL: {agent_sql if agent_sql else '(empty)'}")
            print(f"Comparator: {r.reason}")


def main() -> None:
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
