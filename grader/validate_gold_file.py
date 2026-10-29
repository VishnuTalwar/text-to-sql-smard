"""
Validates a gold-set YAML before it is fed to the grader.

    python grader/validate_gold_file.py PATH_TO_YAML

Structural checks (the loader silently ignores some of these problems, which is
why they are checked here):
  - top level is a dict with "fragen" (list) and optionally "standard" (dict)
  - every item has id (non-empty string), tier (int) and frage (non-empty string)
  - ids are unique
  - tier 1-4: non-empty gold_sql string, reihenfolge_relevant (bool), toleranz (number)
  - tier 0: gold_sql present and explicitly null
  - no key outside the 15 fields of loader.Question (a typo is otherwise ignored)

SQL checks (read-only grader_ro role, same environment variables as executor.py):
  - tier 1-4: runs gold_sql, reports row count and column count or the error
  - tier 0 with beleg_sql: runs it and shows the result

Exit code 0 if every check passes, 1 if any check fails, 2 if the file cannot be
read at all. Warnings (unknown top-level keys, gold_zeilen differing from the
actual row count, tier outside 0-4) do not change the exit code.
"""

import argparse
import dataclasses
import os
import sys
from pathlib import Path

import psycopg2
import yaml
from dotenv import load_dotenv

from loader import Question

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

KNOWN_ITEM_KEYS = {f.name for f in dataclasses.fields(Question)}
KNOWN_TOP_LEVEL_KEYS = {"standard", "fragen"}
KNOWN_STANDARD_KEYS = {"reihenfolge_relevant", "toleranz"}
BELEG_PREVIEW_ROWS = 5


class Report:
    def __init__(self) -> None:
        self.failures = 0
        self.warnings = 0

    def ok(self, where: str, msg: str) -> None:
        print(f"  ok    {where:<10} {msg}")

    def fail(self, where: str, msg: str) -> None:
        self.failures += 1
        print(f"  FAIL  {where:<10} {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings += 1
        print(f"  warn  {where:<10} {msg}")


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _run(sql: str) -> tuple[int, list[tuple]]:
    """Execute sql on grader_ro. Returns (column count, rows). Raises on any error.
    Unlike executor.run_query this also yields the column count for 0-row results."""
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "smard"),
        user=os.environ["GRADER_DB_USER"],
        password=os.environ["GRADER_DB_PASSWORD"],
    )
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            cur.execute(sql)
            return len(cur.description), cur.fetchall()
    finally:
        conn.close()


def check_structure(data, report: Report) -> list[dict]:
    """Top-level and per-item structural checks. Returns the usable item dicts."""
    print("Structure")
    if not isinstance(data, dict):
        report.fail("top level", f"expected a dict with 'fragen', got {type(data).__name__}")
        return []

    for key in data:
        if key not in KNOWN_TOP_LEVEL_KEYS:
            report.warn("top level", f"unknown top-level key {key!r} (the loader ignores it)")

    fragen = data.get("fragen")
    if not isinstance(fragen, list):
        report.fail("top level", f"'fragen' must be a list, got {type(fragen).__name__}")
        return []
    report.ok("top level", f"'fragen' is a list of {len(fragen)} items")

    if "standard" in data:
        standard = data["standard"]
        if not isinstance(standard, dict):
            report.fail("standard", f"must be a dict, got {type(standard).__name__}")
        else:
            for key in standard:
                if key not in KNOWN_STANDARD_KEYS:
                    report.fail("standard", f"unknown key {key!r} (the loader ignores it)")
            if "reihenfolge_relevant" in standard and not isinstance(standard["reihenfolge_relevant"], bool):
                report.fail("standard", "reihenfolge_relevant must be a bool")
            if "toleranz" in standard and not _is_number(standard["toleranz"]):
                report.fail("standard", "toleranz must be a number")
            report.ok("standard", f"keys: {sorted(standard)}")
    else:
        report.ok("standard", "absent (optional); loader falls back to its own defaults")

    items = []
    seen: dict[str, int] = {}
    for idx, item in enumerate(fragen):
        where = f"#{idx}"
        if not isinstance(item, dict):
            report.fail(where, f"item must be a dict, got {type(item).__name__}")
            continue
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            where = item_id
        items.append(item)

        # Required by the loader: id, tier, frage.
        for key in ("id", "tier", "frage"):
            if key not in item:
                report.fail(where, f"missing required key {key!r}")
        if "id" in item and not (isinstance(item_id, str) and item_id):
            report.fail(where, f"id must be a non-empty string, got {item_id!r}")
        if "frage" in item and not (isinstance(item["frage"], str) and item["frage"].strip()):
            report.fail(where, "frage must be a non-empty string")

        if isinstance(item_id, str) and item_id:
            if item_id in seen:
                report.fail(where, f"duplicate id (first at #{seen[item_id]})")
            else:
                seen[item_id] = idx

        tier = item.get("tier")
        if "tier" in item and not _is_int(tier):
            report.fail(where, f"tier must be an int, got {tier!r}")
        elif _is_int(tier) and not 0 <= tier <= 4:
            report.warn(where, f"tier {tier} is outside 0-4")

        unknown = sorted(set(item) - KNOWN_ITEM_KEYS)
        if unknown:
            report.fail(where, f"unknown key(s) {unknown} (the loader ignores them; typo?)")

        if not _is_int(tier):
            continue
        if tier == 0:
            if "gold_sql" not in item:
                report.fail(where, "tier 0: gold_sql key missing (must be present and null)")
            elif item["gold_sql"] is not None:
                report.fail(where, "tier 0: gold_sql must be null")
        else:
            sql = item.get("gold_sql")
            if not (isinstance(sql, str) and sql.strip()):
                report.fail(where, f"tier {tier}: gold_sql must be a non-empty string")
            if "reihenfolge_relevant" not in item:
                report.fail(where, f"tier {tier}: reihenfolge_relevant missing")
            elif not isinstance(item["reihenfolge_relevant"], bool):
                report.fail(where, "reihenfolge_relevant must be a bool")
            if "toleranz" not in item:
                report.fail(where, f"tier {tier}: toleranz missing")
            elif not _is_number(item["toleranz"]):
                report.fail(where, "toleranz must be a number")
            elif item["toleranz"] <= 0:
                report.fail(where, f"toleranz must be > 0, got {item['toleranz']}")

    print(f"  {len(items)} items checked structurally")
    return items


def check_sql(items: list[dict], report: Report) -> None:
    print("\nSQL (grader_ro, read-only)")
    try:
        _run("SELECT 1")
    except Exception as exc:  # KeyError for missing env vars, psycopg2 errors, ...
        report.fail("connect", f"cannot run SQL as grader_ro: {type(exc).__name__}: {exc}")
        return

    for item in items:
        tier = item.get("tier")
        where = item.get("id") if isinstance(item.get("id"), str) else "?"
        if not _is_int(tier):
            continue

        if tier != 0:
            sql = item.get("gold_sql")
            if not (isinstance(sql, str) and sql.strip()):
                continue  # already reported by the structure check
            try:
                n_cols, rows = _run(sql)
            except Exception as exc:
                report.fail(where, f"gold_sql error: {str(exc).strip().splitlines()[0]}")
                continue
            report.ok(where, f"rows={len(rows)} cols={n_cols}")
            expected = item.get("gold_zeilen")
            if _is_int(expected) and expected != len(rows):
                report.warn(where, f"gold_zeilen={expected} but gold_sql returned {len(rows)} rows")
        elif isinstance(item.get("beleg_sql"), str) and item["beleg_sql"].strip():
            try:
                n_cols, rows = _run(item["beleg_sql"])
            except Exception as exc:
                report.fail(where, f"beleg_sql error: {str(exc).strip().splitlines()[0]}")
                continue
            report.ok(where, f"beleg_sql rows={len(rows)} cols={n_cols}")
            for row in rows[:BELEG_PREVIEW_ROWS]:
                print(f"              {row!r}")
            if len(rows) > BELEG_PREVIEW_ROWS:
                print(f"              ... {len(rows) - BELEG_PREVIEW_ROWS} more rows")


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate a gold-set YAML file for the grader.")
    ap.add_argument("path", type=Path, help="gold-set YAML to validate")
    args = ap.parse_args()

    try:
        with open(args.path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        print(f"Cannot read {args.path}: {exc}")
        sys.exit(2)

    print(f"Validating {args.path}\n")
    report = Report()
    items = check_structure(data, report)
    check_sql(items, report)

    print(f"\n{report.failures} failure(s), {report.warnings} warning(s)")
    print("RESULT: PASS" if report.failures == 0 else "RESULT: FAIL")
    sys.exit(0 if report.failures == 0 else 1)


if __name__ == "__main__":
    main()
