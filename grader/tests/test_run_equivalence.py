"""
Equivalence tests for grader/run.py (D40 step 2). No API call: the model is a fake.
The SQL checks and the grading use the real read-only database.

  a. For each config, the 84 attempt-1 prompts built by run.py are compared character by
     character with the prompts the old runner for that row sends (old single-call runners
     are imported in a subprocess, because they patch module globals at import time; the
     loop runners R1 to R3b are run in-process with the fake model).
  b. For r1, r2, r3 and r3b: the whole pipeline through run.py and through the old runner
     with the same fake model (one that returns the gold SQL, and one scripted to trigger an
     error retry, an empty retry, a decline review and a system decline). The .jsonl
     records must match field by field, apart from timing.
  c. The fake-model runs of run.py write a manifest with every field of step 3.

Run from the grader folder:  python -m unittest discover -s tests -v
"""

import contextlib
import hashlib
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GRADER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GRADER))

import run as shared_runner
import prompt_template_v2b
from loader import GOLD_SET_PATH, load_questions
from _db import needs_db  # noqa: E402  (D46: skipped only when SKIP_DB_TESTS=1)

CONFIG_DIR = GRADER / "configs"
QUESTIONS = load_questions()
BY_ID = {q.id: q for q in QUESTIONS}

# config file -> old runner module (the single-call rows) / loop rows
SINGLE_CALL = {
    "naive": "run_baseline", "schema_linked": "run_schema_linked", "decline": "run_schema_linked_decline",
    "v2a": "run_v2a", "v2b": "run_v2b", "v2b2": "run_v2b2", "v2c": "run_v2c",
    "ex-a": "run_exa", "ex-b": "run_exb", "df": "run_df",
}
LOOP_ROWS = {"r1": "run_r1", "r2": "run_r2", "r3": "run_r3", "r3b": "run_r3b"}

TIMING_FIELDS = {"check_seconds", "total_seconds"}  # real clock time of the SQL checks


# ---------------------------------------------------------------- the fake model

def _find_question(messages):
    first = messages[0]["content"]
    for q in QUESTIONS:
        if f"\n\nQuestion: {q.frage}\n\n" in first:
            return q
    raise AssertionError("no exam question found in the prompt")


EMPTY_JULY = "SELECT SUM(mwh) FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'"
BROKEN = "SELECT mwhh FROM erzeugung LIMIT 1"


class FakeModel:
    """Deterministic stand-in for the OpenAI call (same interface as agent_loop.call_openai).

    mode "gold":     tier 1-4 -> the gold SQL; tier 0 -> NO_QUERY.
    mode "scripted": like "gold", except for these questions (attempt = number of assistant
                     messages so far + 1):
        t1_01  attempt 1 SQL with an error (and a HINT)   -> error retry, then gold
        t1_02  attempt 1 SQL with 0 rows, no period       -> empty retry (rows), then gold
        t1_03  attempt 1 SQL, only NULL, for July 2026    -> empty fact (R3), system decline (R3b)
        t1_04  broken SQL on every attempt                -> error retry until the cap
        t1_12  attempt 1 NO_QUERY "Data for February 2026 is not available" -> decline review, then gold
        u_08   attempt 1 SQL, only NULL, for July 2026    -> system decline (R3b); else NO_QUERY
    """

    def __init__(self, mode):
        self.mode = mode
        self.first_prompts = {}  # question id -> text of the first message
        self.calls = 0

    def gold(self, q):
        return "NO_QUERY: the information is not in the tables." if q.gold_sql is None else q.gold_sql.strip()

    def reply(self, q, attempt):
        if self.mode == "scripted":
            if q.id == "t1_01" and attempt == 1:
                return BROKEN
            if q.id == "t1_02" and attempt == 1:
                return "SELECT mwh FROM erzeugung WHERE energietraeger = 'Nonexistent'"
            if q.id == "t1_03" and attempt == 1:
                return EMPTY_JULY
            if q.id == "t1_04":
                return BROKEN
            if q.id == "t1_12" and attempt == 1:
                return "NO_QUERY: Data for February 2026 is not available."
            if q.id == "u_08":
                return EMPTY_JULY if attempt == 1 else "NO_QUERY: no data for July 2026."
        return self.gold(q)

    def __call__(self, messages):
        self.calls += 1
        q = _find_question(messages)
        attempt = 1 + sum(1 for m in messages if m["role"] == "assistant")
        if attempt == 1:
            self.first_prompts[q.id] = messages[0]["content"]
        raw = self.reply(q, attempt)
        return {
            "raw_model_output": raw,
            "model": "fake-model", "system_fingerprint": "fp_fake",
            "prompt_tokens": sum(len(m["content"]) for m in messages) // 4,
            "completion_tokens": len(raw) // 4,
            "latency_seconds": 0.5,
        }


def _quiet(func, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


# ---------------------------------------------------------------- 5a, single-call rows

CAPTURE = r'''
import importlib, json, os, sys
os.environ["OPENAI_API_KEY"] = "test-key-no-network"
sys.path.insert(0, sys.argv[1])
importlib.import_module(sys.argv[2])          # the old runner: it patches the prompt at import
import naive_agent
from loader import load_questions
sent = []
class _Msg:
    def __init__(self, c): self.content = c
class _Choice:
    def __init__(self, c): self.message = _Msg(c)
class _Usage:
    prompt_tokens = 1
    completion_tokens = 1
class _Resp:
    def __init__(self): self.choices = [_Choice("SELECT 1")]; self.usage = _Usage(); self.model = "m"; self.system_fingerprint = "f"
class _Completions:
    def create(self, **kw):
        sent.append({k: kw[k] for k in ("model", "messages", "temperature", "seed")})
        return _Resp()
class _Client:
    def __init__(self, *a, **k): self.chat = type("c", (), {"completions": _Completions()})()
naive_agent.OpenAI = _Client                  # the old runner's own API call now lands here
for q in load_questions():
    naive_agent.answer(q.frage)
print(json.dumps(sent))
'''


def old_single_call_requests(runner_module):
    """What the old runner sends for the 84 questions (imported in a subprocess)."""
    proc = subprocess.run([sys.executable, "-I", "-c", CAPTURE, str(GRADER), runner_module],
                          capture_output=True, text=True, cwd=str(GRADER), timeout=300)
    if proc.returncode != 0:
        raise AssertionError(f"{runner_module} could not be imported/captured:\n{proc.stderr[-2000:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestPromptEquivalenceSingleCallRows(unittest.TestCase):
    summary = {}

    def test_attempt1_prompts_identical_to_the_old_runner(self):
        for name, old_module in SINGLE_CALL.items():
            with self.subTest(config=name):
                cfg, _ = shared_runner.load_config(CONFIG_DIR / f"{name}.yaml")
                sent = old_single_call_requests(old_module)
                self.assertEqual(len(sent), len(QUESTIONS))
                with shared_runner.prompt_builder(cfg["prompt"], cfg["examples"]) as build:
                    diffs = []
                    for q, req in zip(QUESTIONS, sent):
                        new_prompt = build(q.frage)
                        old_messages = req["messages"]
                        if old_messages != [{"role": "user", "content": new_prompt}]:
                            diffs.append(q.id)
                        self.assertEqual((req["model"], req["temperature"], req["seed"]),
                                         (cfg["model"], cfg["temperature"], cfg["seed"]),
                                         f"{name}: call settings differ from the old runner")
                n_same = len(QUESTIONS) - len(diffs)
                self.summary[name] = f"{n_same}/{len(QUESTIONS)} identical" + (f", differences: {diffs}" if diffs else "")
                self.assertEqual(diffs, [], f"{name}: prompts differ for {diffs}")

    @classmethod
    def tearDownClass(cls):
        print("\n[5a] attempt-1 prompts, run.py vs old runner (single-call rows)")
        for name in SINGLE_CALL:
            print(f"  {name:14s} {cls.summary.get(name, 'not run')}")


# ---------------------------------------------------------------- 5a/5b/5c, loop rows

@needs_db
class TestPipelineEquivalenceLoopRows(unittest.TestCase):
    prompt_summary = {}
    pipeline_summary = {}
    runs = {}   # (row, mode) -> (old_records, new_records, new_dir, fake_old, fake_new)

    @classmethod
    def setUpClass(cls):
        for row, old_module in LOOP_ROWS.items():
            old = importlib.import_module(old_module)
            for mode in ("gold", "scripted"):
                old_dir, new_dir = tempfile.mkdtemp(prefix=f"old_{row}_"), tempfile.mkdtemp(prefix=f"new_{row}_")
                fake_old, fake_new = FakeModel(mode), FakeModel(mode)
                _quiet(old.run, "run1", None, fake_old, Path(old_dir), 0)
                _quiet(shared_runner.run_config, CONFIG_DIR / f"{row}.yaml", 1, None, fake_new, Path(new_dir), 0)
                old_file = next(Path(old_dir).glob("*.jsonl"))
                new_file = next(Path(new_dir).glob("*.jsonl"))
                cls.runs[(row, mode)] = (_read_jsonl(old_file), _read_jsonl(new_file), Path(new_dir),
                                         fake_old, fake_new)

    def test_attempt1_prompts_identical_to_the_old_runner(self):
        for row in LOOP_ROWS:
            with self.subTest(config=row):
                cfg, _ = shared_runner.load_config(CONFIG_DIR / f"{row}.yaml")
                _, _, _, fake_old, fake_new = self.runs[(row, "gold")]
                with shared_runner.prompt_builder(cfg["prompt"], cfg["examples"]) as build:
                    diffs = [q.id for q in QUESTIONS
                             if not (build(q.frage) == fake_old.first_prompts[q.id] == fake_new.first_prompts[q.id])]
                    # the old loop runners use prompt_template_v2b through agent_loop
                    diffs += [q.id for q in QUESTIONS if build(q.frage) != prompt_template_v2b.build_prompt(q.frage)]
                self.prompt_summary[row] = f"{len(QUESTIONS) - len(set(diffs))}/{len(QUESTIONS)} identical"
                self.assertEqual(diffs, [])

    def test_jsonl_records_match_field_by_field(self):
        for (row, mode), (old_recs, new_recs, _, fake_old, fake_new) in self.runs.items():
            with self.subTest(row=row, mode=mode):
                self.assertEqual(len(old_recs), len(QUESTIONS))
                self.assertEqual(len(new_recs), len(QUESTIONS))
                self.assertEqual(fake_old.calls, fake_new.calls, "different number of model calls")
                mismatches, extra_nonempty = [], []
                for o, n in zip(old_recs, new_recs):
                    self.assertEqual(o["id"], n["id"])
                    for key in o:
                        if key in TIMING_FIELDS:
                            continue
                        if o[key] != n.get(key, "<missing>"):
                            mismatches.append((o["id"], key))
                    for key in set(n) - set(o):  # fields the older row did not have
                        if key == "retried_after_error":  # restates the attempt list; check it against it
                            kinds = [a["check_fired"] for a in n["attempts"]]
                            if n[key] != ("error" in kinds[:-1]):
                                extra_nonempty.append((o["id"], key, n[key]))
                        elif n[key] not in (False, [], None, 0):  # all other new fields: must be off/empty
                            extra_nonempty.append((o["id"], key, n[key]))
                self.pipeline_summary[(row, mode)] = (
                    f"{len(QUESTIONS)}/{len(QUESTIONS)} records identical in {len(old_recs[0]) - len(TIMING_FIELDS)} "
                    f"compared fields" if not mismatches else f"MISMATCHES {mismatches[:5]}")
                self.assertEqual(mismatches, [])
                self.assertEqual(extra_nonempty, [], "fields the older row did not have must be off/empty (or consistent)")
                # same keys as the newest runner
                self.assertEqual(set(new_recs[0]), set(self.runs[("r3b", mode)][1][0]))

    def test_scripted_fake_triggers_every_path(self):
        """The scripted model really exercises the error retry, empty retry, review and system decline."""
        by = {row: {r["id"]: r for r in self.runs[(row, "scripted")][1]} for row in LOOP_ROWS}
        for row in LOOP_ROWS:   # error retry (all rows have it on)
            self.assertEqual([a["check_fired"] for a in by[row]["t1_01"]["attempts"]], ["error", None])
            self.assertTrue(by[row]["t1_04"]["cap_hit"])
            self.assertEqual(by[row]["t1_04"]["n_attempts"], 3)
        for row in ("r2", "r3", "r3b"):  # empty retry
            self.assertEqual([a["check_fired"] for a in by[row]["t1_02"]["attempts"]], ["empty_rows", None])
        self.assertEqual(by["r1"]["t1_02"]["n_attempts"], 1)
        for row in ("r3", "r3b"):  # decline review
            self.assertTrue(by[row]["t1_12"]["review_fired"], row)
            self.assertTrue(by[row]["t1_12"]["answered_after_review"], row)
        for row in ("r1", "r2"):
            self.assertFalse(by[row]["t1_12"]["review_fired"])
        # empty fact in R3, system decline in R3b
        self.assertTrue(by["r3"]["t1_03"]["empty_fact_fired"])
        self.assertFalse(by["r3"]["t1_03"]["system_declined"])
        self.assertTrue(by["r3b"]["t1_03"]["system_declined"])
        self.assertTrue(by["r3b"]["u_08"]["system_declined"])
        self.assertEqual(by["r3b"]["u_08"]["n_attempts"], 1)
        self.assertEqual(by["r3b"]["u_08"]["extracted_sql"], None)
        self.assertFalse(by["r3"]["u_08"]["system_declined"])
        self.assertEqual(by["r3"]["u_08"]["n_attempts"], 2)

    def test_manifest_has_every_field(self):
        for (row, mode), (_, _, new_dir, _, _) in self.runs.items():
            with self.subTest(row=row, mode=mode):
                files = list(new_dir.glob("*.manifest.json"))
                self.assertEqual(len(files), 1)
                self.assertTrue(files[0].name.startswith(f"{row}_run1_"), files[0].name)
                m = json.loads(files[0].read_text(encoding="utf-8"))
                cfg_text = (CONFIG_DIR / f"{row}.yaml").read_text(encoding="utf-8")
                self.assertEqual(m["config_file"], f"{row}.yaml")
                self.assertEqual(m["config_content"], cfg_text)
                self.assertEqual(len(m["prompt_sha256"]), len(QUESTIONS))
                self.assertTrue(all(len(h) == 64 for h in m["prompt_sha256"].values()))
                with shared_runner.prompt_builder("v2b") as build:
                    want = {q.id: hashlib.sha256(build(q.frage).encode("utf-8")).hexdigest() for q in QUESTIONS}
                self.assertEqual(m["prompt_sha256"], want)
                combined = hashlib.sha256("\n".join(f"{i}:{h}" for i, h in want.items()).encode("utf-8")).hexdigest()
                self.assertEqual(m["prompt_sha256_combined"], combined)
                self.assertEqual(m["gold_file_sha256"], hashlib.sha256(GOLD_SET_PATH.read_bytes()).hexdigest())
                self.assertEqual(m["gold_file"], "gold_set_smard.yaml")
                self.assertEqual(len(m["git"]["commit"]), 40)
                self.assertIn(m["git"]["working_tree_clean"], (True, False))
                self.assertIn("untracked_files", m["git"])
                self.assertEqual((m["model"], m["temperature"], m["seed"], m["max_attempts"]),
                                 ("gpt-4o-2024-08-06", 0, 0, 3))
                self.assertEqual(set(m["switches"]), set(shared_runner.SWITCH_NAMES))
                self.assertTrue(m["start_time"] and m["end_time"])
                self.assertLessEqual(m["start_time"], m["end_time"])
                for pkg in ("openai", "psycopg", "sqlglot"):
                    self.assertTrue(m["packages"][pkg]["version"], pkg)
                self.assertEqual(m["n_questions"], len(QUESTIONS))

    @classmethod
    def tearDownClass(cls):
        print("\n[5a] attempt-1 prompts, run.py vs old runner (loop rows)")
        for row in LOOP_ROWS:
            print(f"  {row:14s} {cls.prompt_summary.get(row, 'not run')}")
        print("[5b] full pipeline with the same fake model, .jsonl records old runner vs run.py")
        for row in LOOP_ROWS:
            for mode in ("gold", "scripted"):
                print(f"  {row:4s} {mode:9s} {cls.pipeline_summary.get((row, mode), 'not run')}")
        print("[5c] manifest written by every fake-model run with all fields: see test_manifest_has_every_field")


# ---------------------------------------------------------------- config and builder checks

class TestConfigs(unittest.TestCase):
    def test_every_config_loads_and_builds_a_prompt(self):
        files = sorted(CONFIG_DIR.glob("*.yaml"))
        names = {f.stem for f in files}
        self.assertTrue({"v2b", "v2c", "v2b2", "ex-a", "ex-b", "df", "r1", "r2", "r3", "r3b",
                         "naive", "schema_linked", "decline"} <= names)
        for f in files:
            cfg, _ = shared_runner.load_config(f)
            with shared_runner.prompt_builder(cfg["prompt"], cfg["examples"]) as build:
                self.assertIn("Question: " + QUESTIONS[0].frage, build(QUESTIONS[0].frage), f.name)

    def test_loop_switches_match_the_old_runners(self):
        want = {"r1": ["error_retry"], "r2": ["error_retry", "empty_retry"],
                "r3": ["error_retry", "empty_retry", "decline_review"],
                "r3b": ["error_retry", "empty_retry", "decline_review", "empty_fact_decline"]}
        for row, on in want.items():
            cfg, _ = shared_runner.load_config(CONFIG_DIR / f"{row}.yaml")
            self.assertEqual([k for k, v in cfg["switches"].items() if v], on)
            self.assertEqual(cfg["max_attempts"], 3)
        for row in SINGLE_CALL:
            cfg, _ = shared_runner.load_config(CONFIG_DIR / f"{row}.yaml")
            self.assertFalse(any(cfg["switches"].values()))
            self.assertEqual(cfg["max_attempts"], 1)

    def test_catalog_patches_are_undone(self):
        import prompt_template_schema_linked
        import prompt_template_v2b as v2b_template
        before = (v2b_template.CATALOG, prompt_template_schema_linked.CATALOG)
        with shared_runner.prompt_builder("v2b2") as build:
            self.assertIsNot(v2b_template.CATALOG, before[0])
            build(QUESTIONS[0].frage)
        with shared_runner.prompt_builder("v2a"):
            self.assertIsNot(prompt_template_schema_linked.CATALOG, before[1])
        self.assertIs(v2b_template.CATALOG, before[0])
        self.assertIs(prompt_template_schema_linked.CATALOG, before[1])
        with shared_runner.prompt_builder("v2b") as build:
            self.assertEqual(build(QUESTIONS[0].frage), prompt_template_v2b.build_prompt(QUESTIONS[0].frage))

    def test_config_values_reach_the_model_call(self):
        """run.py passes model, temperature and seed of the config to agent_loop.call_openai."""
        import agent_loop
        from types import SimpleNamespace
        seen = {}

        class Client:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kw):
                        seen.update(kw)
                        return SimpleNamespace(
                            choices=[SimpleNamespace(message=SimpleNamespace(content="SELECT 1"))],
                            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
                            model="m", system_fingerprint="f")

        msgs = [{"role": "user", "content": "x"}]
        agent_loop.call_openai(msgs, client=Client, model="some-model", temperature=0.3, seed=7)
        self.assertEqual((seen["model"], seen["temperature"], seen["seed"]), ("some-model", 0.3, 7))
        agent_loop.call_openai(msgs, client=Client)  # defaults = the fixed settings of every row so far
        self.assertEqual((seen["model"], seen["temperature"], seen["seed"]), ("gpt-4o-2024-08-06", 0, 0))


    def test_bad_configs_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            good = (CONFIG_DIR / "r3b.yaml").read_text(encoding="utf-8")
            for name, text in {"missing": good.replace("seed: 0\n", ""),
                               "unknown_key": good + "colour: red\n",
                               "unknown_switch": good.replace("error_retry: true", "error_retry: true\n  made_up: true"),
                               "unknown_prompt": good.replace("prompt: v2b", "prompt: v9"),
                               "examples_on_other_prompt": good.replace("prompt: v2b", "prompt: df").replace("examples: none", "examples: ex-a")}.items():
                p = Path(d) / f"{name}.yaml"
                p.write_text(text, encoding="utf-8")
                if name == "examples_on_other_prompt":
                    cfg, _ = shared_runner.load_config(p)
                    with self.assertRaises(ValueError):
                        with shared_runner.prompt_builder(cfg["prompt"], cfg["examples"]):
                            pass
                else:
                    with self.assertRaises(ValueError, msg=name):
                        shared_runner.load_config(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
