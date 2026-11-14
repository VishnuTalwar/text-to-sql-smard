"""
Re-grade of all saved rows after the label_only fix (D43). No API call.

Same method as regrade_answer_score.py (D42): every final SQL of every results/*.jsonl (held-out
files skipped by name, never opened) is run once through the grader's path (cache) and graded on
the same rows by
  strict      comparator.compare (unchanged)
  answer old  the D42 answer comparator, loaded from git commit 0369782 (labels only had to group
              the rows consistently)
  answer new  the current answer comparator (labels must mean a gold label, D43)

    python regrade_answer_score_v2.py [--out ../results/answer_score_regrade_v2_<date>.md]
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import comparator
from answer_comparator import answer_compare, load_answer_columns, match_label
from executor import QueryError
from loader import load_questions
from regrade_answer_score import FILE_RE, ROW_ORDER, TIERS, RESULTS, mean, run_cached

OLD_COMMIT = "0369782"          # D42: answer comparator before the label_only fix
LABEL_ITEMS = ["t2_15", "t3_08", "t3_11"]


def load_old_comparator():
    root = Path(__file__).resolve().parent.parent
    src = subprocess.run(["git", "show", f"{OLD_COMMIT}:grader/answer_comparator.py"], cwd=root,
                         capture_output=True, text=True, check=True).stdout
    tmp = Path(tempfile.mkdtemp()) / "answer_comparator_d42.py"
    tmp.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("answer_comparator_d42", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=RESULTS / f"answer_score_regrade_v2_{date.today().isoformat()}.md")
    args = ap.parse_args()

    old = load_old_comparator()
    questions = {q.id: q for q in load_questions()}
    entries = load_answer_columns()
    comparator.run_query = lambda sql: run_cached(sql)[1]

    files, skipped = [], []
    for path in sorted(RESULTS.glob("*.jsonl")):
        if "heldout" in path.name.lower():
            skipped.append(path.name)
            continue
        m = FILE_RE.match(path.name)
        if m:
            files.append((m["row"], int(m["run"]), path))

    graded = []
    for row, run, path in files:
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                q = questions[rec["id"]]
                sql = rec.get("extracted_sql") or ""
                strict = comparator.compare(q, sql)
                a_old = old.answer_compare(q, sql, entries.get(q.id), run=run_cached)
                a_new = answer_compare(q, sql, entries.get(q.id), run=run_cached)
                graded.append({"row": row, "run": run, "id": q.id, "tier": q.tier, "recorded": bool(rec["passed"]),
                               "strict": strict.passed, "old": a_old.passed, "new": a_new.passed,
                               "new_reason": a_new.reason, "old_reason": a_old.reason, "sql": sql})
        print(f"graded {path.name}", flush=True)

    rows_present = [r for r in ROW_ORDER if any(g["row"] == r for g in graded)]
    rows_present += sorted({g["row"] for g in graded} - set(rows_present))

    stats = {}
    for row in rows_present:
        runs = [[g for g in graded if g["row"] == row and g["run"] == run]
                for run in sorted({g["run"] for g in graded if g["row"] == row})]
        s = {"n_runs": len(runs)}
        for key in ("recorded", "old", "new"):
            s[key] = mean([sum(g[key] for g in r) for r in runs])
            s[key + "_runs"] = [sum(g[key] for g in r) for r in runs]
            s[key + "_tier"] = {t: mean([sum(g[key] for g in r if g["tier"] == t) for r in runs]) for t in TIERS}
        stats[row] = s

    consistency = [g for g in graded if g["recorded"] != g["strict"]]
    monotonic = [g for g in graded if g["strict"] and not g["new"]]
    monotonic_old = [g for g in graded if g["strict"] and not g["old"]]
    changed = [g for g in graded if g["old"] != g["new"]]
    gained = [g for g in changed if g["new"] and not g["old"]]

    # agent labels seen in the three label items: every text column of the agent result
    seen = {i: defaultdict(lambda: [0, 0, 0]) for i in LABEL_ITEMS}   # label -> [question-runs, new pass, new fail]
    labels_of_run = {}
    for g in graded:
        if g["id"] not in LABEL_ITEMS or not g["sql"]:
            continue
        try:
            cols, rows = run_cached(g["sql"])
        except QueryError:
            continue
        item = entries[g["id"]]
        col = item["label_only"][0]
        meanings = item["label_meanings"][col]
        run_labels = []
        for j in range(len(cols)):
            vals = [r[j] for r in rows]
            if vals and all(isinstance(v, str) for v in vals):
                for v in dict.fromkeys(vals):
                    rec = seen[g["id"]][v]
                    rec[0] += 1
                    rec[1] += g["new"]
                    rec[2] += (not g["new"])
                    run_labels.append(v)
        labels_of_run[(g["row"], g["run"], g["id"])] = run_labels

    L = []
    w = L.append
    w(f"# Answer score, version 2 (label_only needs meaning): re-grade of all saved rows ({date.today().isoformat()})")
    w("")
    w("Same method as `results/answer_score_regrade_2026-11-06.md`, without any API call: every question-run of every saved row (`results/*.jsonl`; "
      "held-out files skipped by name, never opened) had its final SQL run once through the grader's path and graded on the same rows by three comparators: "
      "**strict** (D19, unchanged), **answer old** (the D42 comparator, loaded from git commit "
      f"`{OLD_COMMIT}`: a label_only column only had to group the rows consistently) and **answer new** (D43: an agent label must contain a keyword of exactly one gold label, "
      "from `label_meanings` in `grader/answer_columns.yaml`, and the numbers next to it must match that gold label's row). Script: `grader/regrade_answer_score_v2.py`.")
    w("")
    w("## Per row (mean of the runs, out of 84)")
    w("")
    w("| Row | Strict (recorded) | Answer old | Answer new | Change (new - old) | Answer new per run |")
    w("|---|---:|---:|---:|---:|---|")
    for row in rows_present:
        s = stats[row]
        w(f"| {row} | {s['recorded']:.2f} | {s['old']:.2f} | {s['new']:.2f} | {s['new'] - s['old']:+.2f} | {', '.join(map(str, s['new_runs']))} |")
    w("")
    w("## Per tier (mean of the runs: strict recorded / answer old / answer new)")
    w("")
    w("| Row | Tier 0 (of 8) | Tier 1 (of 35) | Tier 2 (of 25) | Tier 3 (of 12) | Tier 4 (of 4) |")
    w("|---|---|---|---|---|---|")
    for row in rows_present:
        s = stats[row]
        w(f"| {row} | " + " | ".join(f"{s['recorded_tier'][t]:.2f} / {s['old_tier'][t]:.2f} / {s['new_tier'][t]:.2f}" for t in TIERS) + " |")
    w("")
    w(f"Question-runs graded: {len(graded)} in {len(files)} files; distinct SQL texts executed: {len(_cache_size())}.")
    w("")
    w("## Checks")
    w("")
    w(f"- **Monotonic (strict pass, answer new fail): {len(monotonic)}** (expected 0)."
      + (" " + "; ".join(f"{g['row']} run {g['run']} {g['id']}: {g['new_reason']}" for g in monotonic) if monotonic else ""))
    w(f"- Monotonic for the old comparator: {len(monotonic_old)}.")
    w(f"- Consistency (re-run strict verdict vs recorded `passed`): {len(consistency)} differences in {len(graded)} question-runs.")
    w(f"- Verdict changes old -> new: **{len(changed)}** question-runs ({len(changed) - len(gained)} pass -> fail, {len(gained)} fail -> pass).")
    w("")
    w("## Agent labels in t2_15, t3_08 and t3_11")
    w("")
    w("Every distinct text value in any text column of the agent results for these three items (this includes the label column; other text columns, if any, would show as `none`). "
      "\"Matched to\" is what the keyword lists make of it. \"Pass / fail\" counts the question-runs (new verdict) in which the label appeared.")
    w("")
    for item in LABEL_ITEMS:
        col = entries[item]["label_only"][0]
        meanings = entries[item]["label_meanings"][col]
        w(f"### {item} (`{col}`; gold labels: {', '.join(meanings)})")
        w("")
        w("| Agent label | Matched to | Question-runs | Pass / fail (answer new) |")
        w("|---|---|---:|---|")
        for label, (n, ok, bad) in sorted(seen[item].items(), key=lambda kv: -kv[1][0]):
            gold, kind = match_label(label, meanings)
            w(f"| {label} | {gold if gold else kind} | {n} | {ok} / {bad} |")
        w("")
    w("### Question-runs without a usable label, and with an unmatched label")
    w("")
    for item in LABEL_ITEMS:
        runs = [g for g in graded if g["id"] == item and g["sql"]]
        no_text = [g for g in runs if not labels_of_run.get((g["row"], g["run"], g["id"]))]
        w(f"- **{item}**: {len(runs)} question-runs with SQL; {len(no_text)} returned no text column at all (for example one row with one value column per category), "
          f"so there was no label to judge: answer new pass {sum(g['new'] for g in no_text)} / fail {sum(not g['new'] for g in no_text)}.")
        col = entries[item]["label_only"][0]
        meanings = entries[item]["label_meanings"][col]
        odd = [g for g in runs if any(match_label(v, meanings)[0] is None for v in labels_of_run.get((g["row"], g["run"], g["id"]), []))]
        for g in odd:
            labs = labels_of_run[(g["row"], g["run"], g["id"])]
            w(f"  - unmatched label in {g['row']} run {g['run']}: {labs}; answer old {'pass' if g['old'] else 'fail'}, answer new {'pass' if g['new'] else 'fail'}; reason (new): {g['new_reason']}; reason (old): {g['old_reason']}")
    w("")
    w("## Question-runs whose answer verdict changed (old -> new)")
    w("")
    if changed:
        w("| Row | Run | Id | Old | New | Agent labels seen | Reason (new) |")
        w("|---|---:|---|---|---|---|---|")
        for g in changed:
            labs = ", ".join(map(repr, labels_of_run.get((g["row"], g["run"], g["id"]), []))) or "-"
            w(f"| {g['row']} | {g['run']} | {g['id']} | {'pass' if g['old'] else 'fail'} | {'pass' if g['new'] else 'fail'} | {labs} | {g['new_reason']} |")
        w("")
        by = defaultdict(int)
        for g in changed:
            by[g["id"]] += 1
        w("By question: " + ", ".join(f"{k} ({v})" for k, v in sorted(by.items())))
    else:
        w("(none)")
    w("")
    w("## Limits")
    w("")
    w("- A label that the keyword lists do not know fails, even if a human would accept it (for example a count or a date as the group name). The lists were written blind, before this re-grade, from the question text and the gold labels.")
    w("- Each distinct SQL text was executed once; queries with unstable tie order are not re-sampled.")
    w("- Held-out files were not opened. Rows without a `.jsonl` file are not covered.")
    args.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"graded {len(graded)}; monotonic {len(monotonic)}; consistency diffs {len(consistency)}; changed {len(changed)} ({len(gained)} fail->pass)")
    return 0


def _cache_size():
    from regrade_answer_score import _cache
    return _cache


if __name__ == "__main__":
    sys.exit(main())
