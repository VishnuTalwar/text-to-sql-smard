"""
CLI grading script for the 84-question SMARD benchmark.

The actual agent doesn't exist yet (see PROJECT.md build order) — the only
mode that makes sense right now is --self-test, which feeds gold_sql back in
as if it were the agent's answer. It must score 84/84; any failure here is a
grader bug, not an agent failure (see README/PROJECT.md section 8).
"""

import argparse
import sys
from pathlib import Path

from comparator import compare
from executor import QueryError
from loader import load_questions

TIER_NAMES = {
    0: "Tier 0 (unanswerable)",
    1: "Tier 1 (single aggregate)",
    2: "Tier 2 (grouping/ranking)",
    3: "Tier 3 (dates/comparisons)",
    4: "Tier 4 (hard)",
}


def run(self_test: bool, gold_file: Path | None = None) -> int:
    if not self_test:
        print("No agent is wired up yet — run with --self-test to grade the grader against itself.")
        return 2

    # No --gold-file: load_questions() with no argument, exactly as before.
    questions = load_questions() if gold_file is None else load_questions(path=gold_file)
    results = []

    for question in questions:
        agent_sql = question.gold_sql  # self-test: pretend the agent wrote the gold SQL
        try:
            result = compare(question, agent_sql)
        except QueryError as exc:
            print(f"FATAL: gold_sql for {question.id} failed to execute: {exc}")
            return 1
        results.append(result)

    _print_report(results)

    return 0 if all(r.passed for r in results) else 1


def _print_report(results: list) -> None:
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

    failures = [r for r in results if not r.passed]
    if failures:
        print("\n=== Failures ===")
        for r in failures:
            print(f"  {r.question_id:8s} (tier {r.tier}): {r.reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade text-to-SQL agent answers against the SMARD gold set.")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Feed gold_sql back in as if it were the agent's answer. Must score 84/84.",
    )
    parser.add_argument(
        "--gold-file",
        metavar="PATH",
        type=Path,
        default=None,
        help="Load questions from this YAML instead of gold_set_smard.yaml.",
    )
    args = parser.parse_args()
    if args.gold_file is not None and not args.gold_file.is_file():
        parser.error(f"--gold-file: no such file: {args.gold_file}")

    sys.exit(run(self_test=args.self_test, gold_file=args.gold_file))


if __name__ == "__main__":
    main()
