"""
CLI script: loop row R2 = row v2b plus error retry AND empty-result retry
(agent_loop.run_question with error_retry and empty_retry on; decline_review off).

Attempt 1 is exactly the v2b setup (same prompt, gpt-4o-2024-08-06 as pinned in D36,
temperature 0, seed 0, same NO_QUERY detection). A question whose SQL fails to run, or
runs but returns an empty result (0 rows, or only NULLs), gets another attempt; both
checks share the limit of 3 attempts in total. The final attempt is graded by the
existing comparator.

Decline handling is as in run_v2b.py: a final reply starting with NO_QUERY (any letter
case) is a decline = no SQL.
  - tier 0: no SQL passes (comparator, unchanged).
  - tiers 1-4: no SQL fails (comparator, unchanged); only the reason text is
    replaced here with "declined (no SQL)" so wrong declines can be counted.

Logs are written to results/r2<_tag>_<date>.log and .jsonl. Run
`python run_r2.py --runs 3` (from the grader folder) to get
results/r2_run{1,2,3}_<date>.log/.jsonl. The .jsonl has the same fields as the R1
records, plus empty_on_attempt1, fixed_after_empty, declined_after_empty and, per
attempt, which check fired.

Optional --gold-file PATH loads the questions from another YAML instead of
gold_set_smard.yaml. The gold file's stem is then put into the log tag, so results for
a different gold file never share a file name with the exam results.
"""

import argparse
import logging
import os
import re
import sys
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from agent_loop import run_question
from catalog_retriever import get_relevant_tables
from comparator import compare
from executor import QueryError, run_query
from loader import load_questions
from result_logging import make_record, write_jsonl

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)

# gpt-4o prices in US dollars per 1M tokens. Check them against the current OpenAI
# price page before quoting any cost figure; they are not read from the API.
PRICE_INPUT_PER_M = 2.50
PRICE_OUTPUT_PER_M = 10.00

SWITCHES = {"error_retry": True, "empty_retry": True, "decline_review": False}
MAX_ATTEMPTS = 3

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


def _percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0, 100]."""
    if not values:
        return 0.0
    xs = sorted(values)
    pos = (len(xs) - 1) * q / 100
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def run(tag: str = "", gold_file: Path | None = None, llm=None,
        results_dir: Path | None = None, pause: float | None = None) -> int:
    """llm, results_dir and pause exist so the whole pipeline can be tested without
    the API; a normal run leaves them at None."""
    if gold_file is None:
        questions = load_questions()
    else:
        print(f"Gold file: {gold_file}")
        questions = load_questions(path=gold_file)
    if pause is None:
        pause = 1.0 if llm is None else 0.0
    results = []
    agent_sqls: dict[str, str] = {}
    replies: dict[str, str] = {}  # final reply for declined questions
    retrieved_tables: dict[str, list[str]] = {}
    records = []
    loops: dict[str, dict] = {}
    valid_count = 0

    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question.id}...", end=" ", flush=True)

        tables = get_relevant_tables(question.frage)
        retrieved_tables[question.id] = tables

        loop = run_question(question.frage, SWITCHES, max_attempts=MAX_ATTEMPTS, llm=llm)
        loops[question.id] = loop
        declined = loop["declined"]
        agent_sql = "" if declined else loop["final_sql"]
        agent_sqls[question.id] = agent_sql
        if declined:
            replies[question.id] = loop["final_reply"]
        note = "declined" if declined else "done"
        if loop["retried"]:
            note += f" (attempts: {loop['n_attempts']})"
        print(note, flush=True)
        time.sleep(pause)  # stay within OpenAI RPM limits across 84 questions

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

        call = {
            "raw_model_output": loop["final_reply"],
            "latency_seconds": loop["latency_seconds"],
            "prompt_tokens": loop["prompt_tokens"],
            "completion_tokens": loop["completion_tokens"],
            "model": loop["model"],
            "system_fingerprint": loop["system_fingerprint"],
        }
        record = make_record(question, result, None if declined else agent_sql, call,
                             retrieved_tables=tables)
        cost = (loop["prompt_tokens"] * PRICE_INPUT_PER_M
                + loop["completion_tokens"] * PRICE_OUTPUT_PER_M) / 1_000_000
        record.update({
            "n_attempts": loop["n_attempts"],
            "retried": loop["retried"],
            "crashed_on_attempt_1": loop["crashed_on_attempt_1"],
            "declined_after_error": loop["declined_after_error"],
            "retried_after_error": loop["retried_after_error"],
            "cap_hit": loop["cap_hit"],
            "empty_on_attempt1": loop["empty_on_attempt1"],
            "retried_after_empty": loop["retried_after_empty"],
            "fixed_after_empty": loop["retried_after_empty"] and result.passed,
            "declined_after_empty": loop["declined_after_empty"],
            "ended_empty": loop["ended_empty"],
            "check_seconds": loop["check_seconds"],
            "total_seconds": loop["total_seconds"],
            "cost_usd": round(cost, 6),
            "attempts": loop["attempts"],
        })
        records.append(record)

    report = _build_report(results, questions, agent_sqls, replies, retrieved_tables,
                           valid_count, loops, records)
    print("\n" + report)
    _save_log(report, tag, records, results_dir)
    return 0 if all(r.passed for r in results) else 1


def _decline_counts(results, replies) -> tuple[int, int, int]:
    """(tier 0 declined, tier 0 total, tiers 1-4 declined)."""
    t0 = [r for r in results if r.tier == 0]
    t0_declined = sum(1 for r in t0 if r.question_id in replies)
    wrong = sum(1 for r in results if r.tier != 0 and r.question_id in replies)
    return t0_declined, len(t0), wrong


def _loop_stats(results, loops, records) -> list[str]:
    n = len(results)
    passed = {r.question_id: r.passed for r in results}
    attempts = [loops[r.question_id]["n_attempts"] for r in results]
    retried = sum(1 for r in results if loops[r.question_id]["retried"])
    crashed = [r.question_id for r in results if loops[r.question_id]["crashed_on_attempt_1"]]
    fixed = [q for q in crashed if passed[q]]
    ran_ok = [q for q in crashed
              if not loops[q]["declined"] and loops[q]["attempts"][-1]["error"] is None]
    dae = [r.question_id for r in results if loops[r.question_id]["declined_after_error"]]
    cap = [r.question_id for r in results if loops[r.question_id]["cap_hit"]]
    totals = [loops[r.question_id]["total_seconds"] for r in results]
    model_only = [loops[r.question_id]["latency_seconds"] for r in results]
    pt = [loops[r.question_id]["prompt_tokens"] for r in results]
    ct = [loops[r.question_id]["completion_tokens"] for r in results]
    cost = [rec["cost_usd"] for rec in records]
    ids = [r.question_id for r in results]
    empty1 = [q for q in ids if loops[q]["empty_on_attempt1"]]
    empty1_txt = [f"{q}:{loops[q]['attempts'][0]['check_fired'][6:]}" for q in empty1]
    empty_retried = [q for q in ids if loops[q]["retried_after_empty"]]
    fixed_empty = [q for q in empty_retried if passed[q]]
    dae_empty = [q for q in ids if loops[q]["declined_after_empty"]]
    ended_empty = [q for q in ids if loops[q]["ended_empty"]]
    err_retried = [q for q in ids if loops[q]["retried_after_error"]]
    both = [q for q in err_retried if q in empty_retried]
    if "u_08" in loops:
        l = loops["u_08"]
        u08 = ("declined" if l["declined"] else "answered with SQL") + \
              f" after {l['n_attempts']} attempt(s); checks fired: {[a['check_fired'] for a in l['attempts']]}"
    else:
        u08 = "not in this gold file"

    def w(label, value):
        return f"{label:44s} {value}"

    return [
        "=== Loop statistics (R2: error retry + empty-result retry) ===",
        w("Retry rate (questions with >1 attempt)", f"{retried}/{n} ({retried / n:.1%})"),
        w("Mean attempts per question", f"{sum(attempts) / n:.3f}"),
        w("Crashed on attempt 1", f"{len(crashed)} {crashed}"),
        w("  of those, pass after retry (fixed)", f"{len(fixed)} {fixed}"),
        w("  of those, SQL runs without error at the end", f"{len(ran_ok)} {ran_ok}"),
        w("Declined after an error", f"{len(dae)} {dae}"),
        w("Hit the attempt cap, still failing or empty", f"{len(cap)} {cap}"),
        "--- empty-result retry ---",
        w("Empty on attempt 1 (0 rows / only NULL)", f"{len(empty1)} {empty1_txt}"),
        w("Retried after an empty result", f"{len(empty_retried)} {empty_retried}"),
        w("  of those, pass after empty retry (fixed)", f"{len(fixed_empty)} {fixed_empty}"),
        w("  of those, ended with a decline", f"{len(dae_empty)} {dae_empty}"),
        w("Final answer still empty", f"{len(ended_empty)} {ended_empty}"),
        w("u_08 (July 2026)", u08),
        w("Share with an error retry", f"{len(err_retried)}/{n} ({len(err_retried) / n:.1%})"),
        w("Share with an empty-result retry", f"{len(empty_retried)}/{n} ({len(empty_retried) / n:.1%})"),
        w("Share with both kinds of retry", f"{len(both)}/{n} ({len(both) / n:.1%})"),
        "--- cost and time ---",
        w("Latency p50 / p95 (model + checks, s)", f"{_percentile(totals, 50):.3f} / {_percentile(totals, 95):.3f}"),
        w("Latency p50 / p95 (model calls only, s)", f"{_percentile(model_only, 50):.3f} / {_percentile(model_only, 95):.3f}"),
        w("Mean latency, model calls only (s)", f"{sum(model_only) / n:.3f}"),
        w("Mean prompt tokens per question", f"{sum(pt) / n:.1f}"),
        w("Mean completion tokens per question", f"{sum(ct) / n:.1f}"),
        w("Cost per question (USD)", f"{sum(cost) / n:.5f}  (run total {sum(cost):.4f}; "
                                     f"prices ${PRICE_INPUT_PER_M}/${PRICE_OUTPUT_PER_M} per 1M in/out)"),
    ]


def _build_report(results, questions, agent_sqls, replies, retrieved_tables,
                  valid_count, loops, records) -> str:
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)

    lines: list[str] = []
    lines.append("=== Per-tier results (R2: v2b + error retry + empty-result retry) ===")
    for tier in sorted(by_tier):
        tier_results = by_tier[tier]
        passed = sum(1 for r in tier_results if r.passed)
        name = TIER_NAMES.get(tier, f"Tier {tier}")
        lines.append(f"{name:32s} {passed:3d}/{len(tier_results):<3d}")

    total_passed = sum(1 for r in results if r.passed)
    total = len(results)
    lines.append(f"\n{'Overall':32s} {total_passed:3d}/{total:<3d}")
    lines.append(f"{'Valid-SQL rate':32s} {valid_count:3d}/{total:<3d}")
    t0_declined, t0_total, wrong = _decline_counts(results, replies)
    lines.append(f"{'Declines: tier 0 correct':32s} {t0_declined:3d}/{t0_total:<3d}")
    lines.append(f"{'Declines: tiers 1-4 (wrong)':32s} {wrong:3d}")
    lines.append("")
    lines.extend(_loop_stats(results, loops, records))

    lines.append("\n=== Per-question retrieval + outcome ===")
    lines.append(f"{'ID':<12} {'Tier':<6} {'Att':<4} {'Retrieved':<30} {'Pass'}")
    lines.append("-" * 74)
    for r in results:
        tables_str = ", ".join(retrieved_tables[r.question_id])
        pass_str = "PASS" if r.passed else f"FAIL ({r.reason})"
        lines.append(f"{r.question_id:<12} {r.tier:<6} {loops[r.question_id]['n_attempts']:<4} "
                     f"{tables_str:<30} {pass_str}")

    questions_by_id = {q.id: q for q in questions}
    failures = [r for r in results if not r.passed]
    lines.append("\n=== Failures ===")
    if not failures:
        lines.append("(none)")
    for r in failures:
        q = questions_by_id[r.question_id]
        tables = retrieved_tables[r.question_id]
        missing = _retrieval_missing(q, tables)
        flag = f" [RETRIEVAL MISS: {sorted(missing)}]" if missing else ""
        agent_sql = agent_sqls[r.question_id]
        lines.append(f"\n--- {r.question_id} (tier {r.tier}){flag} ---")
        lines.append(f"Retrieved: {tables}")
        lines.append(f"Question:  {q.frage}")
        lines.append(f"Gold SQL:  {q.gold_sql.strip() if q.gold_sql else '(none)'}")
        lines.append(f"Agent SQL: {agent_sql if agent_sql else '(empty)'}")
        if r.question_id in replies:
            lines.append(f"Reply:     {replies[r.question_id]}")
        loop = loops[r.question_id]
        if loop["retried"]:
            lines.append(f"Attempts:  {loop['n_attempts']} (errors: "
                         f"{[a['error'] for a in loop['attempts']]})")
        lines.append(f"Reason:    {r.reason}")

    narrow = [r for r in failures
              if _retrieval_missing(questions_by_id[r.question_id], retrieved_tables[r.question_id])]
    lines.append("\n=== Retrieval analysis ===")
    lines.append(f"  Failed AND retriever missed a gold table: {len(narrow)} — retrieval-caused candidates")
    lines.append(f"  Failed with all gold tables supplied:     {len(failures) - len(narrow)} — catalog/model issue, not retrieval")
    return "\n".join(lines)


def _save_log(report: str, tag: str, records, results_dir: Path | None = None) -> None:
    out_dir = results_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    tag = tag or os.environ.get("RUN_TAG", "")
    path = out_dir / f"r2{('_' + tag) if tag else ''}_{timestamp}.log"
    path.write_text(report, encoding="utf-8")
    print(f"\nLog saved to: {path}")
    jsonl_path = path.with_suffix(".jsonl")
    write_jsonl(jsonl_path, records)
    print(f"Per-question records saved to: {jsonl_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1, help="number of repeated full runs")
    ap.add_argument("--tag", default="", help="log filename tag prefix")
    ap.add_argument(
        "--gold-file",
        metavar="PATH",
        type=Path,
        default=None,
        help="load questions from this YAML instead of gold_set_smard.yaml; "
             "its name is added to the log/jsonl file names",
    )
    args = ap.parse_args()
    base_tag = args.tag
    if args.gold_file is not None:
        if not args.gold_file.is_file():
            ap.error(f"--gold-file: no such file: {args.gold_file}")
        gold_label = re.sub(r"[^A-Za-z0-9]+", "_", args.gold_file.stem).strip("_")
        base_tag = f"{gold_label}_{args.tag}" if args.tag else gold_label
    codes = []
    for k in range(1, args.runs + 1):
        tag = f"{base_tag + '_' if base_tag else ''}run{k}" if args.runs > 1 or base_tag else ""
        print(f"\n##### run {k}/{args.runs} (tag={tag or '-'}) #####")
        codes.append(run(tag, args.gold_file))
    sys.exit(0 if all(c == 0 for c in codes) else 1)


if __name__ == "__main__":
    main()
