"""
The final held-out run (D47): r3b_safe and v2b, 3 runs each, on heldout_smard.yaml, on the same day.

    python grader/final_run.py --dry-run     every check, builds all 30 prompts of both configs, no API call
    python grader/final_run.py               the real run (about $0.50); refuses unless every check passes

The real run starts only if ALL of these hold (a refusal changes nothing and calls nothing):
  1. the freeze check passes (grader/freeze.py check; results/freeze_final-v1.json)
  2. the git working tree is clean (changes to tracked files; untracked files are only listed)
  3. HEAD is the commit tagged final-v1
  4. heldout_smard.yaml still has the D29 hash (also part of the freeze check)
  5. results/final_heldout_prediction.md exists and is no longer marked DRAFT (D47: the prediction is
     written and approved before any API call)
  6. grader/answer_columns_heldout.yaml covers exactly the held-out items that have gold SQL
  7. no output file of today exists yet (nothing is overwritten, runs of two days are never mixed)

Then it runs both configs through the normal run.py path (run.run_config: same prompts, loop, manifests,
logs and per-question .jsonl files as every other row), grades every run with the strict comparator and the
answer comparator (answer columns of the held-out set), and writes results/final_heldout_<date>.md with
totals and counts only: no question ids, no question text, no SQL.
"""

import argparse
import logging
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

GRADER = Path(__file__).resolve().parent
ROOT = GRADER.parent
sys.path.insert(0, str(GRADER))

import freeze  # noqa: E402
import run as grader_run  # noqa: E402
from answer_comparator import answer_compare, load_answer_columns  # noqa: E402
from executor import run_query_with_columns  # noqa: E402
from loader import load_questions  # noqa: E402

TAG = "final-v1"
RUNS = 3
CONFIGS = (("r3b_safe", GRADER / "configs" / "r3b_safe.yaml"), ("v2b", GRADER / "configs" / "v2b.yaml"))
HELDOUT = ROOT / "heldout_smard.yaml"
COLUMNS_HELDOUT = GRADER / "answer_columns_heldout.yaml"
RESULTS = ROOT / "results"
PREDICTION = RESULTS / "final_heldout_prediction.md"
DRAFT_MARK = "DRAFT"
FAILURE_TYPES = ("wrong shape", "wrong values", "SQL error", "false decline", "missed decline", "blocked", "other")


# ---------------------------------------------------------------- checks

def _git(root: Path, *args) -> tuple[int, str]:
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=30)
        return out.returncode, out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def check_clean(root: Path = ROOT) -> list[str]:
    """Problems with the working tree: tracked files changed or staged (untracked files do not count)."""
    code, _ = _git(root, "rev-parse", "--git-dir")
    if code != 0:
        return ["not a git repository"]
    code, status = _git(root, "status", "--porcelain", "--untracked-files=no")
    if code != 0:
        return ["git status failed"]
    if status:
        return [f"the git working tree is not clean ({len(status.splitlines())} tracked file(s) changed or staged)"]
    return []


def check_tag_at_head(root: Path = ROOT, tag: str = TAG) -> list[str]:
    """Problems with the tag: it does not exist, or HEAD is not the commit it points to."""
    code, _ = _git(root, "rev-parse", "--git-dir")
    if code != 0:
        return ["not a git repository"]
    code, tagged = _git(root, "rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}")
    if code != 0 or not tagged:
        return [f"the tag {tag} does not exist"]
    code, head = _git(root, "rev-parse", "HEAD")
    if code != 0 or head != tagged:
        return [f"HEAD is not the commit tagged {tag}"]
    return []


def check_prediction(path: Path = PREDICTION) -> list[str]:
    path = Path(path)
    if not path.is_file():
        return [f"{path.name} is missing"]
    if DRAFT_MARK in path.read_text(encoding="utf-8"):
        return [f"{path.name} is still marked DRAFT (not yet approved)"]
    return []


def check_answer_columns(heldout: Path = HELDOUT, columns: Path = COLUMNS_HELDOUT) -> list[str]:
    try:
        ids = {q.id for q in load_questions(path=heldout) if q.gold_sql}
        entries = load_answer_columns(columns)
    except Exception as exc:
        return [f"answer columns not readable: {type(exc).__name__}"]
    problems = []
    if set(entries) != ids:
        problems.append(f"{columns.name} does not cover exactly the held-out items with gold SQL "
                        f"({len(entries)} entries, {len(ids)} items)")
    return problems


def output_paths(date: str, results_dir: Path = RESULTS) -> list[Path]:
    """Files the real run would create or overwrite today, by name (nothing is opened)."""
    paths = [Path(results_dir) / f"final_heldout_{date}.md"]
    for tag, _ in CONFIGS:
        base = f"{tag}_{re.sub(r'[^A-Za-z0-9]+', '_', HELDOUT.stem).strip('_')}"
        for k in range(1, RUNS + 1):
            for ext in ("jsonl", "log", "manifest.json"):
                paths.append(Path(results_dir) / f"{base}_run{k}_{date}.{ext}")
    return paths


def check_no_outputs_yet(date: str, results_dir: Path = RESULTS) -> list[str]:
    exist = [p.name for p in output_paths(date, results_dir) if p.exists()]
    return [f"{len(exist)} output file(s) of {date} already exist"] if exist else []


def all_checks(root: Path = ROOT, results_dir: Path = RESULTS, date: str | None = None) -> list[tuple[str, list[str]]]:
    date = date or datetime.now().strftime("%Y-%m-%d")
    freeze_path = Path(results_dir) / "freeze_final-v1.json"
    return [
        ("freeze check", freeze.check_freeze(freeze_path, root)),
        ("git working tree clean", check_clean(root)),
        (f"HEAD is the commit tagged {TAG}", check_tag_at_head(root)),
        ("held-out file has the D29 hash",
         [] if freeze.sha256_file(root / freeze.HELDOUT) == freeze.HELDOUT_SHA256_D29 else
         [f"{freeze.HELDOUT} does not have the D29 hash"]),
        ("prediction approved", check_prediction(Path(results_dir) / "final_heldout_prediction.md")),
        ("answer columns cover the held-out items", check_answer_columns(root / freeze.HELDOUT,
                                                                         root / "grader" / "answer_columns_heldout.yaml")),
        ("no output files of today yet", check_no_outputs_yet(date, results_dir)),
    ]


# ---------------------------------------------------------------- grading

def failure_type(reason: str) -> str:
    """Failure type of a strict-comparator failure, from its reason text."""
    r = reason or ""
    if r.startswith("agent SQL blocked"):
        return "blocked"
    if r.startswith("agent SQL error"):
        return "SQL error"
    if r == grader_run.DECLINED_REASON:
        return "false decline"
    if r.startswith("tier 0: agent returned SQL"):
        return "missed decline"
    if r.startswith(("row count mismatch", "column count mismatch")):
        return "wrong shape"
    if r.startswith("cell mismatch"):
        return "wrong values"
    return "other"


def read_records(path: Path) -> list[dict]:
    import json
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def grade_records(records: list[dict], questions: dict, entries: dict, run=run_query_with_columns) -> list[dict]:
    """One dict per record, WITHOUT any text: tier, strict, answer, failure type, system decline, blocked walls,
    cost, model, fingerprints. Strict is what run.py recorded. Answer is graded here (answer comparator)."""
    rows = []
    for rec in records:
        q = questions[rec["id"]]
        attempts = rec.get("attempts") or []
        last = attempts[-1] if attempts else {}
        final_blocked = bool(last.get("blocked")) and rec.get("extracted_sql") is not None
        if final_blocked and not q.is_tier0:
            answer_ok = False  # same rule as run.py: a blocked final answer is a fail, and is never run again
        else:
            answer_ok = answer_compare(q, rec.get("extracted_sql") or "", entries.get(q.id), run=run).passed
        strict_ok = bool(rec["passed"])
        rows.append({
            "tier": rec["tier"],
            "strict": strict_ok,
            "answer": answer_ok,
            "failure": None if strict_ok else failure_type(rec.get("comparator_reason")),
            "system_declined": bool(rec.get("system_declined")),
            "blocked_walls": [a.get("wall") for a in attempts if a.get("blocked")],
            "cost_usd": float(rec.get("cost_usd") or 0.0),
            "models": sorted({m for m in [rec.get("model")] + [a.get("model") for a in attempts] if m}),
            "fingerprints": sorted({f for f in [rec.get("system_fingerprint")]
                                    + [a.get("system_fingerprint") for a in attempts] if f}),
        })
    return rows


# ---------------------------------------------------------------- the report (totals and counts only)

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def build_final_report(graded: dict, meta: dict) -> str:
    """graded: {setup: [rows of run 1, rows of run 2, ...]} (rows from grade_records). meta: date, commit, notes.
    Contains totals and counts only: no question ids, no question text, no SQL."""
    setups = list(graded)
    tiers = sorted({r["tier"] for runs in graded.values() for run in runs for r in run})
    n_of = {t: sum(1 for r in next(iter(graded.values()))[0] if r["tier"] == t) for t in tiers}
    n_all = sum(n_of.values())
    out = [f"# Final held-out run, {meta['date']}", "",
           "Totals and counts only: no question text, no question ids, no SQL (D47).", "",
           f"- Commit: {meta.get('commit', 'unknown')} (tag {TAG})",
           f"- Same day: {'yes' if meta.get('same_day', True) else 'NO: the runs crossed midnight'}",
           f"- Held-out items: {n_all} (" + ", ".join(f"tier {t}: {n_of[t]}" for t in tiers) + ")", ""]

    out += ["## Per-run totals (passed of %d)" % n_all, "", "| setup | run | strict | answer score |", "|---|---:|---:|---:|"]
    for s in setups:
        for k, run in enumerate(graded[s], 1):
            out.append(f"| {s} | {k} | {sum(r['strict'] for r in run)} | {sum(r['answer'] for r in run)} |")
    out.append("")

    out += ["## Mean over the runs (passed)", "",
            "| setup | " + " | ".join(f"tier {t} (of {n_of[t]})" for t in tiers) + f" | total (of {n_all}) |",
            "|---|" + "---:|" * (len(tiers) + 1)]
    for s in setups:
        for label, key in (("strict", "strict"), ("answer score", "answer")):
            cells = [f"{_mean([sum(r[key] for r in run if r['tier'] == t) for run in graded[s]]):.2f}" for t in tiers]
            total = _mean([sum(r[key] for r in run) for run in graded[s]])
            out.append(f"| {s}, {label} | " + " | ".join(cells) + f" | {total:.2f} |")
    out.append("")

    out += ["## Failure types (strict failures, summed over the runs)", "",
            "| setup | " + " | ".join(FAILURE_TYPES) + " | total |", "|---|" + "---:|" * (len(FAILURE_TYPES) + 1)]
    for s in setups:
        c = Counter(r["failure"] for run in graded[s] for r in run if r["failure"])
        out.append(f"| {s} | " + " | ".join(str(c.get(f, 0)) for f in FAILURE_TYPES) + f" | {sum(c.values())} |")
    out.append("")

    out += ["## System decline fired (summed over the runs)", "",
            "| setup | " + " | ".join(f"tier {t}" for t in tiers) + " |", "|---|" + "---:|" * len(tiers)]
    for s in setups:
        out.append(f"| {s} | " + " | ".join(
            str(sum(1 for run in graded[s] for r in run if r["tier"] == t and r["system_declined"])) for t in tiers) + " |")
    out.append("")

    out += ["## Blocked queries per wall (every attempt, summed over the runs)", "",
            "| setup | wall 1 | wall 2 | wall 3 | total |", "|---|---:|---:|---:|---:|"]
    for s in setups:
        walls = Counter(w for run in graded[s] for r in run for w in r["blocked_walls"])
        out.append(f"| {s} | {walls.get(1, 0)} | {walls.get(2, 0)} | {walls.get(3, 0)} | {sum(walls.values())} |")
    out.append("")

    out += ["## Cost, model, fingerprints", "", "| setup | cost (USD, 3 runs) | model | system fingerprints |", "|---|---:|---|---|"]
    total = 0.0
    for s in setups:
        cost = sum(r["cost_usd"] for run in graded[s] for r in run)
        total += cost
        models = sorted({m for run in graded[s] for r in run for m in r["models"]})
        prints = sorted({f for run in graded[s] for r in run for f in r["fingerprints"]})
        out.append(f"| {s} | {cost:.4f} | {', '.join(models)} | {', '.join(prints)} |")
    out += ["", f"Total cost: ${total:.4f}", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- the run

def _quiet_question_logs() -> None:
    """The retriever logs every question at INFO; keep held-out question text out of the logs."""
    logging.getLogger("catalog_retriever").setLevel(logging.WARNING)


def dry_run(out=print, checks=None) -> int:
    """Every check, and all 30 prompts of both configs built. No API call, no database run."""
    _quiet_question_logs()
    checks = checks if checks is not None else all_checks()
    out("== checks that the real run needs ==")
    failed = 0
    for name, problems in checks:
        out(f"  [{'ok' if not problems else 'NOT MET'}] {name}")
        for p in problems:
            out(f"        - {p}")
        failed += bool(problems)
    questions = load_questions(path=HELDOUT)
    out(f"== prompts (held-out file: {len(questions)} items) ==")
    built = 0
    for tag, cfg_path in CONFIGS:
        cfg, _ = grader_run.load_config(cfg_path)
        with grader_run.prompt_builder(cfg["prompt"], cfg["examples"]) as build:
            hashes = grader_run.prompt_hashes(questions, build)
            prompts = [build(q.frage) for q in questions]
        ok = len(prompts) == len(questions) and all(isinstance(p, str) and p.strip() for p in prompts)
        built += ok
        out(f"  {tag}: {len(prompts)} prompts built ({'all non-empty' if ok else 'PROBLEM'}), "
            f"model {cfg['model']}, switches on: {[k for k, v in cfg['switches'].items() if v] or 'none'}, "
            f"max_attempts {cfg['max_attempts']}, combined prompt hash {hashes['combined'][:16]}")
    out("== no API call was made ==")
    out(f"The real run would {'start' if not failed else 'REFUSE to start'} now "
        f"({failed} of {len(checks)} checks not met).")
    return 0 if built == len(CONFIGS) else 1


def _find_run_files(tag: str, k: int, since: float, results_dir: Path) -> Path:
    """The .jsonl this run just wrote (same name rule as run.run_config; only files newer than the start)."""
    base = f"{tag}_{re.sub(r'[^A-Za-z0-9]+', '_', HELDOUT.stem).strip('_')}"
    found = [p for p in Path(results_dir).glob(f"{base}_run{k}_*.jsonl") if p.stat().st_mtime >= since - 2]
    if len(found) != 1:
        raise RuntimeError(f"expected one fresh results file for {tag} run {k}, found {len(found)}")
    return found[0]


def run_final(results_dir: Path = RESULTS, llm=None, checks=None, out=print, root: Path = ROOT) -> int:
    """checks / llm / results_dir / root are for the tests; the command line leaves them at their defaults."""
    _quiet_question_logs()
    results_dir = Path(results_dir)
    date = datetime.now().strftime("%Y-%m-%d")
    checks = checks if checks is not None else all_checks(root=root, results_dir=results_dir, date=date)
    unmet = [(n, p) for n, p in checks if p]
    if unmet:
        out("REFUSING to start the final run. Not met:")
        for name, problems in unmet:
            out(f"  - {name}")
            for p in problems:
                out(f"      {p}")
        return 3

    questions = {q.id: q for q in load_questions(path=HELDOUT)}
    entries = load_answer_columns(COLUMNS_HELDOUT)
    graded, started = {}, datetime.now()
    for tag, cfg_path in CONFIGS:
        t0 = time.time()
        code = grader_run.run_config(cfg_path, runs=RUNS, gold_file=HELDOUT, llm=llm, results_dir=results_dir)
        if code != 0:
            out(f"STOP: {tag} did not finish (exit code {code}); no report written")
            return code
        graded[tag] = [grade_records(read_records(_find_run_files(tag, k, t0, results_dir)), questions, entries)
                       for k in range(1, RUNS + 1)]
    same_day = datetime.now().strftime("%Y-%m-%d") == started.strftime("%Y-%m-%d")
    _, head = _git(ROOT, "rev-parse", "--short", "HEAD")
    report = build_final_report(graded, {"date": date, "commit": head or "unknown", "same_day": same_day})
    path = results_dir / f"final_heldout_{date}.md"
    path.write_text(report + "\n", encoding="utf-8")
    out(f"Final report written to {path}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The final held-out run (D47).")
    ap.add_argument("--dry-run", action="store_true",
                    help="run every check and build all 30 prompts of both configs; no API call")
    args = ap.parse_args(argv)
    return dry_run() if args.dry_run else run_final()


if __name__ == "__main__":
    sys.exit(main())
