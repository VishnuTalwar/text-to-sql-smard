"""
Re-grade the saved rows with the strict comparator and the answer comparator (D42). No API call.

For every results/*.jsonl (held-out files are skipped by name and never opened) the final SQL of
each question-run is run through the grader's execution path (grader_ro, executor.py) and graded
twice, on the SAME execution:
  strict  - comparator.compare (D19), unchanged
  answer  - answer_comparator.answer_compare (D42)
Each distinct SQL text is executed once (cache), so both verdicts see identical rows.

    python regrade_answer_score.py [--out ../results/answer_score_regrade_<date>.md]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import comparator
from answer_comparator import answer_compare, load_answer_columns
from executor import QueryError, run_query_with_columns
from loader import load_questions

RESULTS = Path(__file__).resolve().parent.parent / "results"
FILE_RE = re.compile(r"^(?P<row>.+)_run(?P<run>\d+)_(?P<date>\d{4}-\d{2}-\d{2})\.jsonl$")
ROW_ORDER = ["schema_linked_decline_t0", "v2a_t0", "v2b_t0", "v2c_t0", "v2b2_t0", "exa", "exb", "df",
             "v2b_fresh", "r1", "r2", "r3", "r3b", "r3b_safe"]
TIERS = [0, 1, 2, 3, 4]

_cache: dict = {}


def run_cached(sql: str):
    """(columns, rows) of sql through the grader's path; one execution per distinct text."""
    if sql not in _cache:
        try:
            _cache[sql] = ("ok", run_query_with_columns(sql))
        except QueryError as exc:
            _cache[sql] = ("err", str(exc))
    kind, value = _cache[sql]
    if kind == "err":
        raise QueryError(value)
    return value


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=RESULTS / f"answer_score_regrade_{date.today().isoformat()}.md")
    args = ap.parse_args()

    questions = {q.id: q for q in load_questions()}
    entries = load_answer_columns()
    comparator.run_query = lambda sql: run_cached(sql)[1]   # strict comparator reads the same cached execution

    files, skipped = [], []
    for path in sorted(RESULTS.glob("*.jsonl")):
        if "heldout" in path.name.lower():
            skipped.append(path.name)
            continue
        m = FILE_RE.match(path.name)
        if m:
            files.append((m["row"], int(m["run"]), path))

    graded = []   # one dict per question-run
    for row, run, path in files:
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                q = questions[rec["id"]]
                sql = rec.get("extracted_sql") or ""
                strict = comparator.compare(q, sql)
                ans = answer_compare(q, sql, entries.get(q.id), run=run_cached)
                graded.append({"row": row, "run": run, "id": q.id, "tier": q.tier, "recorded": bool(rec["passed"]),
                               "strict": strict.passed, "answer": ans.passed, "strict_reason": strict.reason,
                               "answer_reason": ans.reason, "sql": sql})
        print(f"graded {path.name}", flush=True)

    rows_present = [r for r in ROW_ORDER if any(g["row"] == r for g in graded)]
    rows_present += sorted({g["row"] for g in graded} - set(rows_present))

    def per_run(row, key):
        out = []
        for run in sorted({g["run"] for g in graded if g["row"] == row}):
            out.append([g for g in graded if g["row"] == row and g["run"] == run])
        return out

    stats = {}
    for row in rows_present:
        runs = per_run(row, None)
        s = {"n_runs": len(runs), "n_q": [len(r) for r in runs]}
        for key in ("recorded", "strict", "answer"):
            s[key] = mean([sum(g[key] for g in r) for r in runs])
            s[key + "_tier"] = {t: mean([sum(g[key] for g in r if g["tier"] == t) for r in runs]) for t in TIERS}
            s[key + "_runs"] = [sum(g[key] for g in r) for r in runs]
        stats[row] = s

    consistency = [g for g in graded if g["recorded"] != g["strict"]]
    monotonic = [g for g in graded if g["strict"] and not g["answer"]]
    flips = defaultdict(lambda: defaultdict(int))     # id -> row -> runs with strict fail, answer pass
    for g in graded:
        if not g["strict"] and g["answer"]:
            flips[g["id"]][g["row"]] += 1
    n_flips = sum(sum(v.values()) for v in flips.values())

    L = []
    w = L.append
    w(f"# Answer score vs strict score: re-grade of all saved rows ({date.today().isoformat()})")
    w("")
    w("Every question-run of every saved row (`results/*.jsonl`, held-out files skipped by name and never opened) was re-graded without any API call: "
      "its final SQL was run through the grader's execution path (`grader_ro`) and graded with the strict comparator (D19, unchanged) and with the "
      "answer comparator (`grader/answer_comparator.py`, required columns from `grader/answer_columns.yaml`), both on the same execution. "
      "Script: `grader/regrade_answer_score.py`. Tier 0 is graded the same in both.")
    w("")
    w("## Per row (mean of the runs, out of 84)")
    w("")
    w("`strict` is the score as recorded when the row was run. `answer` is the new score. `difference` = answer - strict.")
    w("")
    w("| Row | Runs | Strict (recorded) | Answer | Difference | Strict per run | Answer per run |")
    w("|---|---:|---:|---:|---:|---|---|")
    for row in rows_present:
        s = stats[row]
        w(f"| {row} | {s['n_runs']} | {s['recorded']:.2f} | {s['answer']:.2f} | {s['answer'] - s['recorded']:+.2f} | "
          f"{', '.join(map(str, s['recorded_runs']))} | {', '.join(map(str, s['answer_runs']))} |")
    w("")
    w("## Per tier (mean of the runs; strict recorded / answer)")
    w("")
    w("| Row | Tier 0 (of 8) | Tier 1 (of 35) | Tier 2 (of 25) | Tier 3 (of 12) | Tier 4 (of 4) | Total |")
    w("|---|---|---|---|---|---|---|")
    for row in rows_present:
        s = stats[row]
        cells = [f"{s['recorded_tier'][t]:.2f} / {s['answer_tier'][t]:.2f}" for t in TIERS]
        w(f"| {row} | " + " | ".join(cells) + f" | {s['recorded']:.2f} / {s['answer']:.2f} |")
    w("")
    bad_n = [(r, stats[r]['n_q']) for r in rows_present if set(stats[r]['n_q']) != {84}]
    w(f"Question-runs graded: {len(graded)} in {len(files)} files; distinct SQL texts executed: {len(_cache)}. "
      + ("Every file has 84 questions." if not bad_n else f"Files with a different number of questions: {bad_n}"))
    w("")
    w("## Limits of this comparison")
    w("")
    w("- Each distinct SQL text was executed once and both verdicts use those rows. The comparison therefore does not re-sample queries whose result order or tie-breaking can vary between executions.")
    w("- `label_only` columns (t2_15, t3_08, t3_11) only have to group the rows the same way. The labels are aligned to the gold labels through the other needed columns, so an answer that attaches a wrong label to the right numbers would still pass.")
    w("- Neither score applies the unit hints of the gold file (MW instead of MWh with the unit named); only values are compared.")
    w("- A computed column that is not a gold column does not count (for example an absolute gap in t3_12 counts only through the gold columns of its alternative).")
    w("- Held-out files were not opened. Rows without a `.jsonl` file (the earliest `.log`-only runs) are not covered.")
    w("")
    w("## Checks")
    w("")
    w("### 1. Consistency: re-run strict verdict vs recorded `passed`")
    w("")
    w(f"Differences: **{len(consistency)}** of {len(graded)} question-runs.")
    w("")
    if consistency:
        w("| Row | Run | Id | Recorded | Re-run strict | Re-run strict reason | Answer verdict |")
        w("|---|---:|---|---|---|---|---|")
        for g in consistency:
            w(f"| {g['row']} | {g['run']} | {g['id']} | {'pass' if g['recorded'] else 'fail'} | {'pass' if g['strict'] else 'fail'} | "
              f"{g['strict_reason']} | {'pass' if g['answer'] else 'fail'} |")
        w("")
        by_q = defaultdict(int)
        for g in consistency:
            by_q[g["id"]] += 1
        w("By question: " + ", ".join(f"{k} ({v})" for k, v in sorted(by_q.items())))
        w("")
    w("### 2. Monotonic: strict passes but answer fails")
    w("")
    w(f"Cases: **{len(monotonic)}** (expected 0).")
    w("")
    if monotonic:
        w("| Row | Run | Id | Answer reason |")
        w("|---|---:|---|---|")
        for g in monotonic:
            w(f"| {g['row']} | {g['run']} | {g['id']} | {g['answer_reason']} |")
        w("")
    w("## Per question: strict fail, answer pass (flips)")
    w("")
    w(f"{n_flips} question-runs flip, on {len(flips)} questions. The cell shows in how many of the runs of that row the question flips.")
    w("")
    kinds = defaultdict(int)
    for g in graded:
        if not g["strict"] and g["answer"]:
            r = g["strict_reason"]
            kinds["column count mismatch (extra or missing column)" if r.startswith("column count") else
                  "text mismatch (labels)" if "text mismatch" in r else
                  "row count mismatch" if r.startswith("row count") else
                  "numeric or date mismatch" if r.startswith("cell mismatch") else r.split(":")[0]] += 1
    w("What the strict comparator said for these flips: " + "; ".join(f"{k}: {v}" for k, v in sorted(kinds.items(), key=lambda x: -x[1])) + ".")
    w("")
    w("| Question | Tier | Flips | Rows (runs flipped) |")
    w("|---|---:|---:|---|")
    for qid in sorted(flips):
        parts = [f"{r} {flips[qid][r]}/{stats[r]['n_runs']}" for r in rows_present if flips[qid].get(r)]
        w(f"| {qid} | {questions[qid].tier} | {sum(flips[qid].values())} | {', '.join(parts)} |")
    w("")
    w("### Flips of two rows in detail")
    w("")
    for row in ("v2b_fresh", "r3b_safe"):
        if row not in rows_present:
            continue
        w(f"**{row}**")
        w("")
        mine = sorted({g["id"] for g in graded if g["row"] == row and not g["strict"] and g["answer"]})
        if not mine:
            w("(no flips)")
        for qid in mine:
            runs = [g["run"] for g in graded if g["row"] == row and g["id"] == qid and not g["strict"] and g["answer"]]
            ex = next(g for g in graded if g["row"] == row and g["id"] == qid and not g["strict"] and g["answer"])
            w(f"- {qid} (tier {questions[qid].tier}): runs {runs}; strict said: {ex['strict_reason']}; answer: {ex['answer_reason']}")
        w("")
    args.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"graded {len(graded)}; consistency differences {len(consistency)}; strict-pass answer-fail {len(monotonic)}; flips {n_flips}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
