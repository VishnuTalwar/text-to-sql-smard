"""
Freeze for the final held-out run (D47): a SHA-256 fingerprint of every file that affects a score.

    python grader/freeze.py write     writes results/freeze_final-v1.json (do this once, after review)
    python grader/freeze.py check     exits 1 and lists the files if any fingerprint differs

Which files: the two configs of the final run (r3b_safe and v2b), every prompt / catalog / helper module they
load (resolved from the configs through run.PROMPTS and followed through the local imports), the loop
(agent_loop.py, which also holds the model call, and naive_agent.py), the date finder, the safe runner and its
limits, the executor, both comparators, both answer-column files, the loader, run.py, the exam and the held-out
files, and requirements.txt. Nothing is ever written except the freeze file.

The held-out file must have the D29 hash. "write" refuses to freeze anything else.
"""

import argparse
import ast
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

GRADER = Path(__file__).resolve().parent
ROOT = GRADER.parent
FREEZE_PATH = ROOT / "results" / "freeze_final-v1.json"
HELDOUT = "heldout_smard.yaml"
HELDOUT_SHA256_D29 = "26ffe76d93f419e4d77a230d54fe8df5d60c464854940d03db0ee01345a80713"

CONFIGS = ("grader/configs/r3b_safe.yaml", "grader/configs/v2b.yaml")
FIXED_FILES = (
    "grader/agent_loop.py",            # the loop and the model call (call_openai)
    "grader/date_facts.py",
    "grader/safe_runner.py",
    "grader/limits.yaml",
    "grader/executor.py",
    "grader/comparator.py",
    "grader/answer_comparator.py",
    "grader/answer_columns.yaml",
    "grader/answer_columns_heldout.yaml",
    "grader/loader.py",
    "grader/run.py",
    "gold_set_smard.yaml",
    HELDOUT,
    "requirements.txt",
)
# python files whose local imports are followed (everything they load at run time stays frozen)
SEED_MODULES = ("agent_loop", "date_facts", "safe_runner", "executor", "comparator", "answer_comparator",
                "loader", "run")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- which files

def _local_imports(py_file: Path, grader: Path) -> set[str]:
    """Names of grader/*.py modules imported anywhere in the file (also inside functions)."""
    found = set()
    for node in ast.walk(ast.parse(Path(py_file).read_text(encoding="utf-8"))):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        found.update(n for n in names if (grader / f"{n}.py").is_file())
    return found


def module_closure(start: set[str], grader: Path = GRADER) -> set[str]:
    seen, todo = set(), list(start)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo.extend(_local_imports(grader / f"{name}.py", grader) - seen)
    return seen


def config_modules(cfg_path: Path) -> set[str]:
    """The prompt modules a config loads, resolved the way run.prompt_builder resolves them."""
    sys.path.insert(0, str(GRADER))
    try:
        import run  # noqa: E402  (imports only; no database connection, no API call)
        cfg, _ = run.load_config(Path(cfg_path))
        module, _func, patches, _uses_retriever = run.PROMPTS[cfg["prompt"]]
        mods = {module, run.EXAMPLES[cfg["examples"]] or module}
        for mod_name, _attr, replacement in patches:
            mods.update({mod_name, replacement.split(":")[0]})
        return mods
    finally:
        sys.path.remove(str(GRADER))


def frozen_files(root: Path = ROOT) -> list[str]:
    """Sorted project-relative paths of every file that is frozen."""
    root = Path(root)
    grader = root / "grader"
    modules = set(SEED_MODULES)
    for cfg in CONFIGS:
        modules |= config_modules(root / cfg)
    files = set(CONFIGS) | set(FIXED_FILES)
    files |= {f"grader/{m}.py" for m in module_closure(modules, grader)}
    return sorted(files)


# ---------------------------------------------------------------- write / check

def compute(files, root: Path = ROOT) -> dict[str, str]:
    return {f: sha256_file(Path(root) / f) for f in files}


def _package_versions(root: Path) -> dict:
    versions = {}
    for line in (Path(root) / "requirements.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*==", line)
        if m:
            try:
                versions[m.group(1)] = metadata.version(m.group(1))
            except metadata.PackageNotFoundError:
                versions[m.group(1)] = None
    return versions


def _models(root: Path) -> list[str]:
    import yaml
    return sorted({yaml.safe_load((Path(root) / c).read_text(encoding="utf-8"))["model"] for c in CONFIGS})


def write_freeze(out_path: Path = FREEZE_PATH, root: Path = ROOT, files=None,
                 expected_heldout_sha256: str = HELDOUT_SHA256_D29) -> dict:
    """Fingerprint the files and write the JSON. Raises ValueError if the held-out file is not the D29 one."""
    files = list(files) if files is not None else frozen_files(root)
    hashes = compute(files, root)
    held = hashes.get(HELDOUT)
    if held != expected_heldout_sha256:
        raise ValueError(f"{HELDOUT} does not have the D29 hash (got {held}); nothing was written")
    data = {
        "name": "final-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "models": _models(root),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": _package_versions(root),
        "files": hashes,
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def check_freeze(freeze_path: Path = FREEZE_PATH, root: Path = ROOT, files=None) -> list[str]:
    """Problems found (empty list = the freeze holds). Each problem names the file."""
    freeze_path = Path(freeze_path)
    if not freeze_path.is_file():
        return [f"freeze file missing: {freeze_path.name}"]
    try:
        recorded = json.loads(freeze_path.read_text(encoding="utf-8"))["files"]
    except (ValueError, KeyError) as exc:
        return [f"freeze file unreadable: {type(exc).__name__}"]
    current = list(files) if files is not None else frozen_files(root)
    problems = []
    for f in sorted(set(recorded) | set(current)):
        path = Path(root) / f
        if f not in recorded:
            problems.append(f"not in the freeze file: {f}")
        elif not path.is_file():
            problems.append(f"missing: {f}")
        elif sha256_file(path) != recorded[f]:
            problems.append(f"changed: {f}")
        elif f not in current:
            problems.append(f"no longer part of the frozen set: {f}")
    if recorded.get(HELDOUT) != HELDOUT_SHA256_D29:
        problems.append(f"{HELDOUT}: the freeze file does not hold the D29 hash")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("mode", choices=["write", "check"])
    ap.add_argument("--freeze-file", type=Path, default=FREEZE_PATH)
    args = ap.parse_args(argv)
    if args.mode == "write":
        try:
            data = write_freeze(args.freeze_file)
        except ValueError as exc:
            print(f"STOP: {exc}")
            return 2
        print(f"Wrote {args.freeze_file} with {len(data['files'])} files:")
        for f, h in data["files"].items():
            print(f"  {h[:12]}  {f}")
        return 0
    problems = check_freeze(args.freeze_file)
    if problems:
        print(f"FREEZE CHECK FAILED ({len(problems)}):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"Freeze check passed: {len(json.loads(args.freeze_file.read_text())['files'])} files unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
