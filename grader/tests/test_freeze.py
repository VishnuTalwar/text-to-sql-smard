"""
Tests for grader/freeze.py (D47). No API call, no database. Everything is done on a copy of the frozen files in a
temporary folder; the real results/freeze_final-v1.json is never written.
"""

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freeze  # noqa: E402


class TestFrozenFiles(unittest.TestCase):
    def test_the_list_has_every_required_file_and_all_exist(self):
        files = freeze.frozen_files()
        for needed in ("grader/configs/r3b_safe.yaml", "grader/configs/v2b.yaml", "grader/agent_loop.py",
                       "grader/date_facts.py", "grader/safe_runner.py", "grader/limits.yaml", "grader/executor.py",
                       "grader/comparator.py", "grader/answer_comparator.py", "grader/answer_columns.yaml",
                       "grader/answer_columns_heldout.yaml", "grader/loader.py", "grader/run.py",
                       "gold_set_smard.yaml", "heldout_smard.yaml", "requirements.txt"):
            self.assertIn(needed, files)
        # what the configs load: the v2b prompt, its catalog chain, the retriever, and the model call's module
        for loaded in ("grader/prompt_template_v2b.py", "grader/schema_catalog_v2b.py", "grader/schema_catalog_v2a.py",
                       "grader/catalog_retriever.py", "grader/prompt_template_decline.py", "grader/naive_agent.py"):
            self.assertIn(loaded, files)
        for f in files:
            self.assertTrue((freeze.ROOT / f).is_file(), f)
        self.assertEqual(files, sorted(set(files)))

    def test_the_final_run_files_are_not_frozen_by_accident(self):
        files = freeze.frozen_files()
        self.assertNotIn("grader/final_run.py", files)   # not part of the score path (not in the agreed list)
        self.assertNotIn("results/freeze_final-v1.json", files)


class TestWriteAndCheck(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.files = freeze.frozen_files()
        for f in self.files:  # a copy of every frozen file
            dest = self.root / f
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(freeze.ROOT / f, dest)
        self.freeze_path = self.root / "results" / "freeze_final-v1.json"

    def write(self):
        return freeze.write_freeze(self.freeze_path, root=self.root, files=self.files)

    def test_write_records_hashes_model_python_and_packages(self):
        data = self.write()
        self.assertEqual(set(data["files"]), set(self.files))
        self.assertEqual(data["models"], ["gpt-4o-2024-08-06"])
        self.assertIn("3.", data["python"])
        self.assertIn("sqlglot", data["packages"])
        self.assertEqual(data["files"]["heldout_smard.yaml"], freeze.HELDOUT_SHA256_D29)
        self.assertEqual(json.loads(self.freeze_path.read_text())["name"], "final-v1")

    def test_check_passes_on_an_untouched_copy(self):
        self.write()
        self.assertEqual(freeze.check_freeze(self.freeze_path, root=self.root, files=self.files), [])

    def test_check_fails_when_one_byte_of_a_frozen_file_changes(self):
        self.write()
        target = self.root / "grader" / "agent_loop.py"
        raw = bytearray(target.read_bytes())
        raw[len(raw) // 2] ^= 1  # one bit of one byte
        target.write_bytes(bytes(raw))
        problems = freeze.check_freeze(self.freeze_path, root=self.root, files=self.files)
        self.assertEqual(problems, ["changed: grader/agent_loop.py"])

    def test_check_lists_every_file_that_differs(self):
        self.write()
        (self.root / "grader" / "limits.yaml").write_text("changed\n")
        (self.root / "requirements.txt").unlink()
        problems = freeze.check_freeze(self.freeze_path, root=self.root, files=self.files)
        self.assertEqual(sorted(problems), ["changed: grader/limits.yaml", "missing: requirements.txt"])

    def test_check_fails_when_the_freeze_file_is_missing_or_the_set_grew(self):
        self.assertEqual(freeze.check_freeze(self.freeze_path, root=self.root, files=self.files),
                         ["freeze file missing: freeze_final-v1.json"])
        self.write()
        problems = freeze.check_freeze(self.freeze_path, root=self.root, files=self.files + ["grader/new_file.py"])
        self.assertEqual(problems, ["not in the freeze file: grader/new_file.py"])

    def test_write_refuses_when_the_heldout_file_is_not_the_d29_one(self):
        (self.root / "heldout_smard.yaml").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.write()
        self.assertFalse(self.freeze_path.exists())  # nothing was written

    def test_command_line_exit_codes(self):
        self.write()
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(freeze.main(["check", "--freeze-file", str(self.freeze_path)]), 0)
        self.assertIn("passed", out.getvalue())
        # a freeze made from a copy with one changed byte no longer matches the real files: exit 1, files listed
        target = self.root / "grader" / "comparator.py"
        target.write_bytes(target.read_bytes() + b"\n#")
        self.write()
        with redirect_stdout(io.StringIO()) as out:
            code = freeze.main(["check", "--freeze-file", str(self.freeze_path)])
        self.assertEqual(code, 1)
        self.assertIn("changed: grader/comparator.py", out.getvalue())
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(freeze.main(["check", "--freeze-file", str(self.root / "none.json")]), 1)

    def test_write_mode_stops_with_code_2_when_the_heldout_hash_differs(self):
        with mock.patch.object(freeze, "HELDOUT_SHA256_D29", "0" * 64), \
                mock.patch.object(freeze, "write_freeze", side_effect=ValueError("not D29")):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(freeze.main(["write", "--freeze-file", str(self.freeze_path)]), 2)
        self.assertIn("STOP", out.getvalue())
        self.assertFalse(self.freeze_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
