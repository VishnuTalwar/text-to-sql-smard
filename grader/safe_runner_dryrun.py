"""
Dry run of the safe runner on history (D41, step 3 of D40). No API call, and no agent query is
run: every agent SQL in every results/*.jsonl (all rows, all runs, all attempts) goes through
walls 1 and 2 only (the static check, and EXPLAIN without ANALYZE for the cost).

Held-out result files are never opened: any file whose name contains "heldout" is skipped by
name. Result files are only read, never changed.

    python safe_runner_dryrun.py [--out ../results/safe_runner_dryrun_<date>.md]
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import safe_runner
from executor import QueryError

RESULTS = Path(__file__).resolve().parent.parent / "results"
FILE_RE = re.compile(r"^(?P<row>.+)_run(?P<run>\d+)_(?P<date>\d{4}-\d{2}-\d{2})\.jsonl$")


def reason_class(reason: str) -> str:
    """The reason with its details removed, so that blocks can be counted by kind."""
    if reason.startswith("table "):
        return "table not allowed (only erzeugung, verbrauch, preise)"
    if reason.startswith("function "):
        return "function on the deny list"
    if reason.startswith("plan_cost"):
        return "estimated plan cost above the limit"
    if reason.startswith("the text could not be parsed"):
        return "could not be parsed as one SELECT"
    if "statements (or text after the semicolon)" in reason:
        return "more than one statement / text after the semicolon"
    return re.sub(r"\d+", "N", reason)


def collect(results_dir: Path):
    """[(row, run, id, attempt|None, sql, is_final, passed)] and the skipped file names."""
    queries, files, skipped = [], [], []
    for path in sorted(results_dir.glob("*.jsonl")):
        if "heldout" in path.name.lower():
            skipped.append(path.name)   # never opened
            continue
        m = FILE_RE.match(path.name)
        row, run = (m["row"], int(m["run"])) if m else (path.stem, 0)
        files.append(path.name)
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                passed = bool(rec.get("passed"))
                if rec.get("attempts"):
                    n = len(rec["attempts"])
                    for a in rec["attempts"]:
                        if a.get("extracted_sql"):
                            queries.append((row, run, rec["id"], a["attempt"], a["extracted_sql"],
                                            a["attempt"] == n and not rec.get("system_declined"), passed))
                elif rec.get("extracted_sql"):
                    queries.append((row, run, rec["id"], None, rec["extracted_sql"], True, passed))
    return queries, files, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=RESULTS / f"safe_runner_dryrun_{date.today().isoformat()}.md")
    args = ap.parse_args()

    limits = safe_runner.load_limits()
    queries, files, skipped = collect(RESULTS)
    verdicts = {}   # sql -> ("ok", cost) | ("blocked", wall, reason) | ("pg_error", message)
    conn = safe_runner.connect()
    try:
        for sql in sorted({q[4] for q in queries}):
            res = safe_runner.check_static(sql)
            if res is None:
                try:
                    res = safe_runner.precheck(sql, limits, conn)
                except QueryError as exc:
                    conn.rollback()
                    verdicts[sql] = ("pg_error", str(exc).splitlines()[0])
                    continue
            verdicts[sql] = ("blocked", res.wall, res.reason) if res.blocked else ("ok", res.plan_cost)
    finally:
        conn.rollback()
        conn.close()

    total = len(queries)
    blocked = [(q, verdicts[q[4]]) for q in queries if verdicts[q[4]][0] == "blocked"]
    pg_err = [q for q in queries if verdicts[q[4]][0] == "pg_error"]
    costs = [verdicts[q[4]][1] for q in queries if verdicts[q[4]][0] == "ok"]
    by_wall = Counter(v[1] for _, v in blocked)
    by_reason = Counter((v[1], reason_class(v[2])) for _, v in blocked)
    final_blocked = [(q, v) for q, v in blocked if q[5]]
    lost = [(q, v) for q, v in final_blocked if q[6]]

    out = []
    w = out.append
    w(f"# Safe runner: dry run on history ({date.today().isoformat()})")
    w("")
    w("Every agent SQL in every `results/*.jsonl` (all rows, all runs, all attempts) went through "
      "wall 1 (static check) and wall 2 (EXPLAIN, no ANALYZE) of `grader/safe_runner.py`. No query was run, "
      "no API call was made, no result file was changed. Script: `grader/safe_runner_dryrun.py`.")
    w("")
    w(f"Limits used: max_plan_cost {limits.max_plan_cost:.1f}, max_rows {limits.max_rows}, "
      f"timeout_ms {limits.timeout_ms} (grader/limits.yaml). Walls 3 (row cap, timeout) are not part of a dry run.")
    w("")
    w("## Scope")
    w("")
    w(f"- Result files read: {len(files)} `.jsonl` files. Files with \"heldout\" in the name were skipped by "
      f"name and never opened: {len(skipped)} ({', '.join(skipped)}).")
    w("- Rows without a `.jsonl` file (the earliest `.log`-only runs) have no stored SQL and are not covered.")
    w(f"- Agent queries checked: **{total}** ({len({q[4] for q in queries})} distinct SQL texts). "
      "A query is every non-empty `extracted_sql` of every attempt (loop rows) or of the answer (single-call rows). "
      "Declines contain no SQL and are not counted.")
    w("")
    w("## Summary")
    w("")
    w(f"- Would be blocked: **{len(blocked)}** of {total} ({len(blocked) / total:.2%}).")
    w(f"- Passed walls 1 and 2: {total - len(blocked) - len(pg_err)}. "
      f"Of these, largest estimated plan cost {max(costs):.1f} "
      f"(limit {limits.max_plan_cost:.1f}).")
    w(f"- PostgreSQL error already at EXPLAIN (the query was broken before the walls could judge it, "
      f"e.g. unknown column): {len(pg_err)}. These are not blocks; the loop handles them as before.")
    w(f"- Blocked queries that were the final answer of their question-run: {len(final_blocked)}; "
      f"of these, the answer had **passed** in history: **{len(lost)}**.")
    w("")
    w("### Blocked, by wall")
    w("")
    w("| Wall | Count |")
    w("|---|---|")
    for wall in (1, 2):
        w(f"| {wall} | {by_wall.get(wall, 0)} |")
    w("")
    w("### Blocked, by wall and reason")
    w("")
    if by_reason:
        w("| Wall | Reason | Count |")
        w("|---|---|---|")
        for (wall, reason), n in sorted(by_reason.items()):
            w(f"| {wall} | {reason} | {n} |")
    else:
        w("(none)")
    w("")
    w("## Blocked queries")
    w("")
    if blocked:
        w("`final` = this query was the answer the row was graded on; `passed` = that answer passed in history "
          "(for an earlier attempt it is the outcome of the question-run).")
        w("")
        w("| Row | Run | Id | Attempt | Wall | Reason | final | passed |")
        w("|---|---|---|---|---|---|---|---|")
        for q, v in blocked:
            row, run, qid, att, sql, final, passed = q
            w(f"| {row} | {run} | {qid} | {att if att is not None else '-'} | {v[1]} | {v[2]} | "
              f"{'yes' if final else 'no'} | {'yes' if passed else 'no'} |")
        w("")
        w("### SQL of the blocked queries (distinct)")
        w("")
        seen = set()
        for q, v in blocked:
            if q[4] in seen:
                continue
            seen.add(q[4])
            w(f"**{q[0]} run {q[1]} {q[2]}** (wall {v[1]}: {v[2]})")
            w("")
            w("```sql")
            w(q[4])
            w("```")
            w("")
    else:
        w("(none)")
        w("")
    if pg_err:
        w("## Queries that fail in EXPLAIN (not blocks)")
        w("")
        c = Counter(reason for reason in (verdicts[q[4]][1] for q in pg_err))
        for reason, n in c.most_common():
            w(f"- {n} x {reason}")
        w("")
    w("## Per row")
    w("")
    per_row = defaultdict(lambda: [0, 0])
    for q in queries:
        per_row[(q[0])][0] += 1
        if verdicts[q[4]][0] == "blocked":
            per_row[(q[0])][1] += 1
    w("| Row | Queries | Blocked |")
    w("|---|---|---|")
    for row, (n, b) in sorted(per_row.items()):
        w(f"| {row} | {n} | {b} |")
    w("")
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"checked {total}; blocked {len(blocked)} (wall1 {by_wall.get(1, 0)}, wall2 {by_wall.get(2, 0)}); "
          f"pg errors at EXPLAIN {len(pg_err)}; final answers blocked {len(final_blocked)}, "
          f"of which passed {len(lost)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
