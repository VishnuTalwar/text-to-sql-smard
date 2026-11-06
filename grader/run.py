"""
Shared runner for every ablation row (D40 step 2).

    python run.py --config configs/<row>.yaml [--runs N] [--gold-file PATH]

One YAML file per row (grader/configs/) holds only what differs between rows: the prompt
(by name), the example block, the loop switches, max_attempts, model, temperature, seed,
number of runs and the output tag. Everything else is reused, not copied:

  prompt templates   prompt_template*.py and the schema catalogs (by name, see PROMPTS)
  the loop           agent_loop.run_question (a row without checks is the loop with all
                     switches off and max_attempts 1: one model call, nothing else)
  grading            comparator.compare, loader.load_questions, executor.run_query
  records            result_logging.make_record, write_jsonl

Outputs (names as before): results/<tag>_run{n}_<date>.log and .jsonl, with the record
fields of run_r3b.py, plus results/<tag>_run{n}_<date>.manifest.json (the run receipt).
With --gold-file the gold file's stem goes into the name: <tag>_<stem>_run{n}_<date>.

The older run_*.py files are kept only to reproduce earlier results. Nothing here edits
them. No API call is made when `llm=` is given (used by tests/test_run_equivalence.py).
"""

import argparse
import contextlib
import hashlib
import importlib
import json
import logging
import platform
import re
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime
from functools import partial
from importlib import metadata
from pathlib import Path

import yaml

from agent_loop import SWITCH_NAMES, call_openai, run_question
from catalog_retriever import get_relevant_tables
from comparator import compare
from executor import QueryError, run_query
from loader import GOLD_SET_PATH, load_questions
from result_logging import make_record, write_jsonl

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s — %(message)s", level=logging.INFO)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRADER_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"

# gpt-4o prices in US dollars per 1M tokens (not read from the API; check them before quoting a cost).
PRICE_INPUT_PER_M = 2.50
PRICE_OUTPUT_PER_M = 10.00

DECLINED_REASON = "declined (no SQL)"
TIER_NAMES = {
    0: "Tier 0 (unanswerable)",
    1: "Tier 1 (single aggregate)",
    2: "Tier 2 (grouping/ranking)",
    3: "Tier 3 (dates/comparisons)",
    4: "Tier 4 (hard)",
}

# ---------------------------------------------------------------- prompts

# name -> (module, builder function, catalog patches, uses_retriever)
# A patch is (module, attribute, "module:attribute" holding the replacement). It is applied
# only while the run builds prompts and is undone afterwards, so configs never leak into
# each other (the old runners patched module globals for the whole process).
PROMPTS = {
    "naive": ("prompt_template", "build_prompt", [], False),
    "schema_linked": ("prompt_template_schema_linked", "build_prompt", [], True),
    "decline": ("prompt_template_decline", "build_prompt", [], True),
    "v2a": ("prompt_template_decline", "build_prompt",
            [("prompt_template_schema_linked", "CATALOG", "schema_catalog_v2a:CATALOG")], True),
    "v2b": ("prompt_template_v2b", "build_prompt", [], True),
    "v2b2": ("prompt_template_v2b", "build_prompt",
             [("prompt_template_v2b", "CATALOG", "schema_catalog_v2b2:CATALOG")], True),
    "v2c": ("prompt_template_v2c", "build_prompt", [], True),
    "df": ("prompt_template_df", "build_prompt", [], True),
}
# example block -> module whose build_prompt wraps the v2b prompt with that block
EXAMPLES = {"none": None, "ex-a": "prompt_template_exa", "ex-b": "prompt_template_exb"}


def _resolve(spec: str):
    module, attr = spec.split(":")
    return getattr(importlib.import_module(module), attr)


@contextlib.contextmanager
def prompt_builder(prompt: str, examples: str = "none"):
    """Yield build_prompt(question) -> str for a prompt name and example block."""
    if prompt not in PROMPTS:
        raise ValueError(f"unknown prompt {prompt!r}; known: {sorted(PROMPTS)}")
    if examples not in EXAMPLES:
        raise ValueError(f"unknown examples {examples!r}; known: {sorted(EXAMPLES)}")
    if examples != "none" and prompt != "v2b":
        raise ValueError("the example blocks (ex-a, ex-b) are built on the v2b prompt; use prompt: v2b")
    module, func, patches, _ = PROMPTS[prompt]
    undo = []
    try:
        for mod_name, attr, replacement in patches:
            mod = importlib.import_module(mod_name)
            undo.append((mod, attr, getattr(mod, attr)))
            setattr(mod, attr, _resolve(replacement))
        template = EXAMPLES[examples] or module
        yield getattr(importlib.import_module(template), func)
    finally:
        for mod, attr, old in reversed(undo):
            setattr(mod, attr, old)


# ---------------------------------------------------------------- config

CONFIG_KEYS = ("description", "prompt", "examples", "switches", "max_attempts", "model",
               "temperature", "seed", "runs", "tag")


def load_config(path: Path) -> tuple[dict, str]:
    """(config, raw text). All keys are required, so nothing differs by accident."""
    text = Path(path).read_text(encoding="utf-8")
    cfg = yaml.safe_load(text)
    if not isinstance(cfg, dict):
        raise ValueError(f"{path}: not a mapping")
    missing = [k for k in CONFIG_KEYS if k not in cfg]
    extra = [k for k in cfg if k not in CONFIG_KEYS]
    if missing or extra:
        raise ValueError(f"{path}: missing keys {missing}, unknown keys {extra}")
    switches = cfg["switches"] or {}
    unknown = [k for k in switches if k not in SWITCH_NAMES]
    if unknown:
        raise ValueError(f"{path}: unknown switches {unknown}; known: {list(SWITCH_NAMES)}")
    cfg["switches"] = {name: bool(switches.get(name, False)) for name in SWITCH_NAMES}
    if not (isinstance(cfg["max_attempts"], int) and cfg["max_attempts"] >= 1):
        raise ValueError(f"{path}: max_attempts must be a whole number >= 1")
    if not (isinstance(cfg["runs"], int) and cfg["runs"] >= 1):
        raise ValueError(f"{path}: runs must be a whole number >= 1")
    if cfg["prompt"] not in PROMPTS:
        raise ValueError(f"{path}: unknown prompt {cfg['prompt']!r}")
    if cfg["examples"] not in EXAMPLES:
        raise ValueError(f"{path}: unknown examples {cfg['examples']!r}")
    return cfg, text


# ---------------------------------------------------------------- manifest

def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(*args) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_state() -> dict:
    """Commit, and whether the tracked files are unmodified. Untracked files (result logs
    of earlier runs, console dumps) are listed but do not make the tree "dirty"."""
    changed = _git("status", "--porcelain", "--untracked-files=no")
    untracked = _git("ls-files", "--others", "--exclude-standard")
    return {
        "commit": _git("rev-parse", "HEAD"),
        "working_tree_clean": (changed == "") if changed is not None else None,
        "modified_tracked_files": changed.splitlines() if changed else [],
        "untracked_files": untracked.splitlines() if untracked else [],
    }


def package_versions() -> dict:
    versions = {}
    for label, candidates in (("openai", ["openai"]),
                              ("psycopg", ["psycopg", "psycopg2-binary", "psycopg2"]),
                              ("sqlglot", ["sqlglot"])):
        versions[label] = None
        for name in candidates:
            try:
                versions[label] = {"package": name, "version": metadata.version(name)}
                break
            except metadata.PackageNotFoundError:
                continue
    return versions


def prompt_hashes(questions, build) -> dict:
    per_question = {q.id: _sha256_text(build(q.frage)) for q in questions}
    combined = _sha256_text("\n".join(f"{i}:{h}" for i, h in per_question.items()))
    return {"per_question": per_question, "combined": combined}


def build_manifest(cfg, cfg_path, cfg_text, gold_path, hashes, run_no, runs, start, end=None) -> dict:
    return {
        "config_file": Path(cfg_path).name,
        "config_content": cfg_text,
        "tag": cfg["tag"],
        "run": run_no,
        "runs_in_this_call": runs,
        "prompt_sha256": hashes["per_question"],
        "prompt_sha256_combined": hashes["combined"],
        "n_questions": len(hashes["per_question"]),
        "gold_file": str(Path(gold_path).name),
        "gold_file_sha256": _sha256_file(gold_path),
        "git": git_state(),
        "model": cfg["model"],
        "temperature": cfg["temperature"],
        "seed": cfg["seed"],
        "max_attempts": cfg["max_attempts"],
        "switches": cfg["switches"],
        "start_time": start.isoformat(timespec="seconds"),
        "end_time": end.isoformat(timespec="seconds") if end else None,
        "packages": package_versions(),
        "python": platform.python_version(),
    }


# ---------------------------------------------------------------- one run

def _is_valid_sql(sql: str) -> bool:
    if not sql:
        return False
    try:
        run_query(sql)
        return True
    except QueryError:
        return False


def _gold_tables(gold_sql: str | None) -> set[str]:
    if not gold_sql:
        return set()
    return set(re.findall(r"\b(erzeugung|verbrauch|preise)\b", gold_sql.lower()))


def _percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0, 100]."""
    if not values:
        return 0.0
    xs = sorted(values)
    pos = (len(xs) - 1) * q / 100
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def run_once(cfg, questions, build, llm, pause, uses_retriever) -> dict | None:
    """Run every question once. Returns the pieces the report and the files need, or
    None if a gold query fails (fatal)."""
    switches, max_attempts = cfg["switches"], cfg["max_attempts"]
    results, records = [], []
    agent_sqls, replies, retrieved, loops = {}, {}, {}, {}
    valid_count = 0
    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question.id}...", end=" ", flush=True)
        tables = get_relevant_tables(question.frage) if uses_retriever else None
        retrieved[question.id] = tables

        loop = run_question(question.frage, switches, max_attempts=max_attempts, llm=llm,
                            prompt_builder=build)
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
            return None
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
            "review_fired": loop["review_fired"],
            "review_periods": loop["review_periods"],
            "declined_after_review": loop["declined_after_review"],
            "answered_after_review": loop["answered_after_review"],
            "empty_fact_fired": loop["empty_fact_fired"],
            "empty_fact_period": loop["empty_fact_period"],
            "system_declined": loop["system_declined"],
            "system_decline_period": loop["system_decline_period"],
            "check_seconds": loop["check_seconds"],
            "total_seconds": loop["total_seconds"],
            "cost_usd": round(cost, 6),
            "attempts": loop["attempts"],
        })
        records.append(record)
    return {"results": results, "records": records, "agent_sqls": agent_sqls, "replies": replies,
            "retrieved": retrieved, "loops": loops, "valid_count": valid_count}


# ---------------------------------------------------------------- the one report

def build_report(cfg, questions, out) -> str:
    """The per-run summary used for every config. Sections of switches that are off are left out."""
    results, loops, records = out["results"], out["loops"], out["records"]
    agent_sqls, replies, retrieved = out["agent_sqls"], out["replies"], out["retrieved"]
    sw = cfg["switches"]
    n = len(results)
    ids = [r.question_id for r in results]
    passed = {r.question_id: r.passed for r in results}
    lines: list[str] = []

    lines.append(f"=== Per-tier results ({cfg['tag']}: {cfg['description']}) ===")
    by_tier: dict[int, list] = {}
    for r in results:
        by_tier.setdefault(r.tier, []).append(r)
    for tier in sorted(by_tier):
        ok = sum(1 for r in by_tier[tier] if r.passed)
        lines.append(f"{TIER_NAMES.get(tier, f'Tier {tier}'):32s} {ok:3d}/{len(by_tier[tier]):<3d}")
    lines.append(f"\n{'Overall':32s} {sum(passed.values()):3d}/{n:<3d}")
    lines.append(f"{'Valid-SQL rate':32s} {out['valid_count']:3d}/{n:<3d}")
    t0 = [r for r in results if r.tier == 0]
    lines.append(f"{'Declines: tier 0 correct':32s} {sum(1 for r in t0 if r.question_id in replies):3d}/{len(t0):<3d}")
    lines.append(f"{'Declines: tiers 1-4 (wrong)':32s} "
                 f"{sum(1 for r in results if r.tier != 0 and r.question_id in replies):3d}")
    lines.append("")

    def w(label, value):
        return f"{label:44s} {value}"

    def lst(sel):
        return f"{len(sel)} {sel}"

    attempts = [loops[i]["n_attempts"] for i in ids]
    retried = [i for i in ids if loops[i]["retried"]]
    lines.append(f"=== Loop statistics ({cfg['tag']}; switches on: "
                 f"{[k for k, v in sw.items() if v] or 'none'}; max_attempts {cfg['max_attempts']}) ===")
    lines.append(w("Retry rate (questions with >1 attempt)", f"{len(retried)}/{n} ({len(retried) / n:.1%})"))
    lines.append(w("Mean attempts per question", f"{sum(attempts) / n:.3f}"))
    if sw["error_retry"]:
        crashed = [i for i in ids if loops[i]["crashed_on_attempt_1"]]
        fixed = [i for i in crashed if passed[i]]
        ran_ok = [i for i in crashed if not loops[i]["declined"] and loops[i]["attempts"][-1]["error"] is None]
        lines.append(w("Crashed on attempt 1", lst(crashed)))
        lines.append(w("  of those, pass after retry (fixed)", lst(fixed)))
        lines.append(w("  of those, SQL runs without error at the end", lst(ran_ok)))
        lines.append(w("Declined after an error", lst([i for i in ids if loops[i]["declined_after_error"]])))
    if any(sw.values()):
        lines.append(w("Hit the attempt cap, still failing or empty", lst([i for i in ids if loops[i]["cap_hit"]])))
    if sw["empty_retry"] or sw["empty_fact_decline"]:
        empty1 = [i for i in ids if loops[i]["empty_on_attempt1"]]
        empty_retried = [i for i in ids if loops[i]["retried_after_empty"]]
        lines.append("--- empty-result checks ---")
        lines.append(w("Empty on attempt 1 (0 rows / only NULL)",
                       f"{len(empty1)} {[f'{i}:{loops[i]['attempts'][0]['check_fired'][6:]}' for i in empty1]}"))
        lines.append(w("Retried after an empty result", lst(empty_retried)))
        lines.append(w("  of those, pass after empty retry (fixed)", lst([i for i in empty_retried if passed[i]])))
        lines.append(w("  of those, ended with a decline",
                       lst([i for i in ids if loops[i]["declined_after_empty"]])))
        lines.append(w("Final answer still empty", lst([i for i in ids if loops[i]["ended_empty"]])))
    if sw["decline_review"]:
        rev = [i for i in ids if loops[i]["review_fired"]]
        lines.append("--- decline review ---")
        lines.append(w("Decline reviews fired", lst(rev)))
        lines.append(w("  of those, declined again after the review",
                       lst([i for i in rev if loops[i]["declined_after_review"]])))
        lines.append(w("  of those, answered with SQL after the review",
                       lst([i for i in rev if loops[i]["answered_after_review"]])))
        lines.append(w("  of those, pass", lst([i for i in rev if passed[i]])))
        if not sw["empty_fact_decline"]:
            lines.append(w("Empty facts fired", lst([i for i in ids if loops[i]["empty_fact_fired"]])))
    if sw["empty_fact_decline"]:
        lines.append("--- system decline ---")
        lines.append(w("System declines", lst([i for i in ids if loops[i]["system_declined"]])))
    lines.append("--- tier 0 questions ---")
    for r in results:
        if r.tier == 0:
            lp = loops[r.question_id]
            what = "declined" if lp["declined"] else "answered with SQL"
            lines.append(w(r.question_id, f"{what} after {lp['n_attempts']} attempt(s); checks fired: "
                                          f"{[a['check_fired'] for a in lp['attempts']]}"
                                          + (" [system decline]" if lp["system_declined"] else "")))
    if any(sw.values()):
        err = [i for i in ids if loops[i]["retried_after_error"]]
        emp = [i for i in ids if loops[i]["retried_after_empty"]]
        lines.append(w("Share with an error retry", f"{len(err)}/{n} ({len(err) / n:.1%})"))
        lines.append(w("Share with an empty-result retry", f"{len(emp)}/{n} ({len(emp) / n:.1%})"))
        lines.append(w("Share with both kinds of retry", f"{len([i for i in err if i in emp])}/{n}"))
    totals = [loops[i]["total_seconds"] for i in ids]
    model_only = [loops[i]["latency_seconds"] for i in ids]
    cost = [rec["cost_usd"] for rec in records]
    lines.append("--- cost and time ---")
    lines.append(w("Latency p50 / p95 (model + checks, s)", f"{_percentile(totals, 50):.3f} / {_percentile(totals, 95):.3f}"))
    lines.append(w("Latency p50 / p95 (model calls only, s)", f"{_percentile(model_only, 50):.3f} / {_percentile(model_only, 95):.3f}"))
    lines.append(w("Mean latency, model calls only (s)", f"{sum(model_only) / n:.3f}"))
    lines.append(w("Mean prompt tokens per question", f"{sum(loops[i]['prompt_tokens'] for i in ids) / n:.1f}"))
    lines.append(w("Mean completion tokens per question", f"{sum(loops[i]['completion_tokens'] for i in ids) / n:.1f}"))
    lines.append(w("Cost per question (USD)", f"{sum(cost) / n:.5f}  (run total {sum(cost):.4f}; "
                                              f"prices ${PRICE_INPUT_PER_M}/${PRICE_OUTPUT_PER_M} per 1M in/out)"))

    lines.append("\n=== Per-question retrieval + outcome ===")
    lines.append(f"{'ID':<12} {'Tier':<6} {'Att':<4} {'Retrieved':<30} {'Pass'}")
    lines.append("-" * 74)
    for r in results:
        tables_str = ", ".join(retrieved[r.question_id]) if retrieved[r.question_id] is not None else "(all tables)"
        pass_str = "PASS" if r.passed else f"FAIL ({r.reason})"
        lines.append(f"{r.question_id:<12} {r.tier:<6} {loops[r.question_id]['n_attempts']:<4} "
                     f"{tables_str:<30} {pass_str}")

    questions_by_id = {q.id: q for q in questions}
    failures = [r for r in results if not r.passed]
    lines.append("\n=== Failures ===")
    if not failures:
        lines.append("(none)")
    narrow = []
    for r in failures:
        q = questions_by_id[r.question_id]
        tables = retrieved[r.question_id]
        missing = (_gold_tables(q.gold_sql) - set(tables)) if tables is not None else set()
        if missing:
            narrow.append(r)
        flag = f" [RETRIEVAL MISS: {sorted(missing)}]" if missing else ""
        lines.append(f"\n--- {r.question_id} (tier {r.tier}){flag} ---")
        lines.append(f"Retrieved: {tables if tables is not None else '(all tables)'}")
        lines.append(f"Question:  {q.frage}")
        lines.append(f"Gold SQL:  {q.gold_sql.strip() if q.gold_sql else '(none)'}")
        lines.append(f"Agent SQL: {agent_sqls[r.question_id] if agent_sqls[r.question_id] else '(empty)'}")
        if r.question_id in replies:
            lines.append(f"Reply:     {replies[r.question_id]}")
        lp = loops[r.question_id]
        if lp["retried"]:
            lines.append(f"Attempts:  {lp['n_attempts']} (errors: {[a['error'] for a in lp['attempts']]})")
        lines.append(f"Reason:    {r.reason}")
    if any(v is not None for v in retrieved.values()):
        lines.append("\n=== Retrieval analysis ===")
        lines.append(f"  Failed AND retriever missed a gold table: {len(narrow)} — retrieval-caused candidates")
        lines.append(f"  Failed with all gold tables supplied:     {len(failures) - len(narrow)} — catalog/model issue, not retrieval")
    return "\n".join(lines)


# ---------------------------------------------------------------- driver

def run_config(cfg_path, runs=None, gold_file=None, llm=None, results_dir=None, pause=None) -> int:
    """Run a config `runs` times. llm, results_dir and pause exist so the whole pipeline can be
    tested without the API; a normal call leaves them at None."""
    cfg, cfg_text = load_config(Path(cfg_path))
    runs = runs or cfg["runs"]
    out_dir = Path(results_dir) if results_dir else RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    gold_path = Path(gold_file) if gold_file else GOLD_SET_PATH
    if gold_file:
        print(f"Gold file: {gold_file}")
    questions = load_questions(path=gold_path)
    if llm is None:
        llm = partial(call_openai, model=cfg["model"], temperature=cfg["temperature"], seed=cfg["seed"])
        default_pause = 1.0
    else:
        default_pause = 0.0
    pause = default_pause if pause is None else pause
    uses_retriever = PROMPTS[cfg["prompt"]][3]
    base_tag = cfg["tag"]
    if gold_file:
        base_tag += "_" + re.sub(r"[^A-Za-z0-9]+", "_", gold_path.stem).strip("_")
    date = datetime.now().strftime("%Y-%m-%d")
    code = 0
    with prompt_builder(cfg["prompt"], cfg["examples"]) as build:
        hashes = prompt_hashes(questions, build)
        for k in range(1, runs + 1):
            stem = out_dir / f"{base_tag}_run{k}_{date}"
            print(f"\n##### {cfg['tag']} run {k}/{runs} (files: {stem.name}.*) #####")
            start = datetime.now()
            manifest_path = stem.with_suffix(".manifest.json")
            manifest_path.write_text(json.dumps(
                build_manifest(cfg, cfg_path, cfg_text, gold_path, hashes, k, runs, start), indent=2,
                ensure_ascii=False), encoding="utf-8")  # receipt exists even if the run crashes
            out = run_once(cfg, questions, build, llm, pause, uses_retriever)
            if out is None:
                code = 1
                break
            report = build_report(cfg, questions, out)
            print("\n" + report)
            stem.with_suffix(".log").write_text(report, encoding="utf-8")
            write_jsonl(stem.with_suffix(".jsonl"), out["records"])
            manifest_path.write_text(json.dumps(
                build_manifest(cfg, cfg_path, cfg_text, gold_path, hashes, k, runs, start, datetime.now()),
                indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\nLog saved to: {stem.with_suffix('.log')}")
            print(f"Per-question records saved to: {stem.with_suffix('.jsonl')}")
            print(f"Run receipt saved to: {manifest_path}")
    return code


def main() -> None:
    ap = argparse.ArgumentParser(description="Run one ablation row from a config file.")
    ap.add_argument("--config", required=True, type=Path, help="e.g. configs/r3b.yaml")
    ap.add_argument("--runs", type=int, default=None, help="number of repeated full runs (default: runs in the config)")
    ap.add_argument("--gold-file", type=Path, default=None,
                    help="load questions from this YAML instead of gold_set_smard.yaml; its name is added to the file names")
    args = ap.parse_args()
    if not args.config.is_file():
        ap.error(f"--config: no such file: {args.config}")
    if args.gold_file is not None and not args.gold_file.is_file():
        ap.error(f"--gold-file: no such file: {args.gold_file}")
    sys.exit(run_config(args.config, args.runs, args.gold_file))


if __name__ == "__main__":
    main()
