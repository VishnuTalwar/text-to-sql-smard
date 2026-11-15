"""
.env.example (D46): every environment variable the code reads is listed, and no value looks like a real key.
Offline: it only reads source files (app, grader, scripts and docker-compose.yml), never a data or exam file.
"""

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / ".env.example"
CODE_DIRS = ("app", "grader", "scripts")
# names of this project's variables, also when a constant holds the name (app/tracing.py: ENV_PUBLIC = "LANGFUSE_...")
OWN_PREFIXES = re.compile(r"^(POSTGRES|GRADER_DB|OPENAI|LANGFUSE)_[A-Z_]+$|^RUN_TAG$")


def _is_environ(node) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "environ" or isinstance(node, ast.Name) and node.id == "environ"


def variables_read_by_code() -> set[str]:
    names = set()
    for d in CODE_DIRS:
        for path in sorted((ROOT / d).glob("*.py")):  # tests are in a sub folder and are not scanned
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Subscript) and _is_environ(node.value) and isinstance(node.slice, ast.Constant):
                    names.add(node.slice.value)  # os.environ["X"]
                elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                        and isinstance(node.args[0].value, str):
                    f = node.func
                    if isinstance(f, ast.Attribute) and (
                            (f.attr == "get" and _is_environ(f.value)) or f.attr == "getenv"):
                        names.add(node.args[0].value)  # os.environ.get("X"), os.getenv("X")
                elif isinstance(node, ast.Constant) and isinstance(node.value, str) and OWN_PREFIXES.match(node.value):
                    names.add(node.value)  # a constant that holds a name
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    names.update(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)", compose))
    return names


def names_in_example() -> set[str]:
    found = set()
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#?\s*([A-Z_][A-Z0-9_]*)=", line)  # a commented-out variable still counts as listed
        if m:
            found.add(m.group(1))
    return found


class TestEnvExample(unittest.TestCase):
    def test_the_scan_finds_the_known_variables(self):
        read = variables_read_by_code()
        for name in ("OPENAI_API_KEY", "GRADER_DB_USER", "GRADER_DB_PASSWORD", "POSTGRES_HOST", "POSTGRES_USER",
                     "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL", "LANGFUSE_HOST", "RUN_TAG"):
            self.assertIn(name, read)

    def test_every_variable_the_code_reads_is_in_env_example(self):
        missing = sorted(variables_read_by_code() - names_in_example())
        self.assertEqual(missing, [], f"read by the code but not in .env.example: {missing}")

    def test_every_variable_in_env_example_is_read_by_the_code(self):
        unused = sorted(names_in_example() - variables_read_by_code())
        self.assertEqual(unused, [], f"in .env.example but not read by any code: {unused}")

    def test_no_value_looks_like_a_real_key(self):
        text = EXAMPLE.read_text(encoding="utf-8")
        for token in re.findall(r"(?:sk-lf-|pk-lf-|sk-)[A-Za-z0-9_-]+", text):
            body = re.sub(r"^(?:sk-lf-|pk-lf-|sk-)", "", token)
            self.assertTrue(body == "your-key-here" or len(body) <= 12, f"looks like a real key: {token[:10]}...")
        # the check itself works: a realistic key is caught
        fake = "sk-" + "a1B2c3D4e5F6g7H8"
        body = re.sub(r"^(?:sk-lf-|pk-lf-|sk-)", "", fake)
        self.assertFalse(body == "your-key-here" or len(body) <= 12)

    def test_secrets_are_ignored_by_git(self):
        lines = {x.strip() for x in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
        for entry in (".env", "app_data/", "data/raw/"):
            self.assertIn(entry, lines)

    def test_env_example_itself_is_not_ignored(self):
        lines = {x.strip() for x in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
        self.assertNotIn(".env.example", lines)
        self.assertNotIn(".env*", lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
