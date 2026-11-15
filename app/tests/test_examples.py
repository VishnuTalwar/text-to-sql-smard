"""Checks app/examples.yaml (D44, step 3c): exam items only, word for word, all passed 3 of 3 runs."""

import json
import sys
import unittest
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "app"))

import answer  # noqa: E402,F401  (puts grader/ on the path)
from loader import GOLD_SET_PATH, load_questions  # noqa: E402

EXAMPLES = yaml.safe_load((PROJECT_ROOT / "app" / "examples.yaml").read_text(encoding="utf-8"))["examples"]
RUNS = [PROJECT_ROOT / "results" / f"r3b_safe_run{n}_2026-11-06.jsonl" for n in (1, 2, 3)]


class TestExamples(unittest.TestCase):
    def test_six_examples_with_unique_ids(self):
        self.assertEqual(len(EXAMPLES), 6)
        self.assertEqual(len({e["id"] for e in EXAMPLES}), 6)
        for e in EXAMPLES:
            self.assertTrue(e["label"] and e["question"] and e["why"], e["id"])

    def test_every_example_is_an_exam_item_word_for_word(self):
        self.assertEqual(GOLD_SET_PATH.name, "gold_set_smard.yaml")
        by_id = {q.id: q for q in load_questions()}
        for e in EXAMPLES:
            self.assertIn(e["id"], by_id)
            self.assertEqual(e["question"], by_id[e["id"]].frage, e["id"])

    def test_the_mix(self):
        by_id = {q.id: q for q in load_questions()}
        tiers = sorted(by_id[e["id"]].tier for e in EXAMPLES)
        self.assertEqual(tiers, [0, 0, 1, 1, 2, 2])
        self.assertIn("u_08", {e["id"] for e in EXAMPLES})

    def test_all_passed_in_3_of_3_runs(self):
        for path in RUNS:
            passed = {}
            with open(path, encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    passed[rec["id"]] = rec["passed"]
            for e in EXAMPLES:
                self.assertTrue(passed[e["id"]], f"{e['id']} did not pass in {path.name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
