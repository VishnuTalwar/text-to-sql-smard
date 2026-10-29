"""
Near-duplicate check between two gold-format YAML files (e.g. held-out vs exam).

    python grader/leak_check.py A.yaml B.yaml [--top 10] [--threshold 0.6] [--out REPORT.md]

Every item of A is compared with every item of B on two measures:
  1. question text: TF-IDF cosine similarity on the lowercased `frage`
     (vocabulary fitted on the questions of both files together)
  2. SQL: both gold_sql strings are parsed with sqlglot (postgres dialect), string
     and number literals are replaced by placeholders, the tree is rendered with
     sqlglot.transpile(..., pretty=False) and lowercased; the similarity is
     difflib.SequenceMatcher.ratio() on the two strings. Items whose gold_sql is
     null (tier 0) are skipped for this measure.

Output is ids and scores only. Question text and SQL are never printed, also not
in error messages.
"""

import argparse
import sys
from difflib import SequenceMatcher
from pathlib import Path

import sqlglot
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlglot import exp

DIALECT = "postgres"


def load_items(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["fragen"]


def normalise_sql(sql: str) -> str:
    """Parse, replace literals by placeholders, render on one line, lowercase."""
    tree = sqlglot.parse_one(sql, read=DIALECT)
    tree = tree.transform(lambda n: exp.Placeholder() if isinstance(n, exp.Literal) else n)
    return sqlglot.transpile(tree.sql(dialect=DIALECT), read=DIALECT, write=DIALECT, pretty=False)[0].lower()


def question_similarity(items_a: list[dict], items_b: list[dict]) -> list[tuple[str, str, float]]:
    texts_a = [i["frage"].lower() for i in items_a]
    texts_b = [i["frage"].lower() for i in items_b]
    vec = TfidfVectorizer(lowercase=True)
    vec.fit(texts_a + texts_b)
    sims = cosine_similarity(vec.transform(texts_a), vec.transform(texts_b))
    return [
        (a["id"], b["id"], float(sims[i][j]))
        for i, a in enumerate(items_a)
        for j, b in enumerate(items_b)
    ]


def sql_similarity(items_a: list[dict], items_b: list[dict]) -> tuple[list[tuple[str, str, float]], list[str]]:
    """Returns (pairs, ids of items skipped because gold_sql is null or unparseable)."""
    skipped: list[str] = []

    def prepare(items: list[dict], label: str) -> list[tuple[str, str]]:
        out = []
        for i in items:
            if i.get("gold_sql") is None:
                continue
            try:
                out.append((i["id"], normalise_sql(i["gold_sql"])))
            except Exception as exc:  # never echo the message: it can contain SQL
                skipped.append(f"{label}:{i['id']} ({type(exc).__name__})")
        return out

    norm_a = prepare(items_a, "A")
    norm_b = prepare(items_b, "B")
    pairs = []
    for id_a, sa in norm_a:
        for id_b, sb in norm_b:
            # autojunk=False: with the default, characters that make up >1% of a
            # 200+ char string are ignored, which distorts SQL comparisons.
            pairs.append((id_a, id_b, SequenceMatcher(None, sa, sb, autojunk=False).ratio()))
    return pairs, skipped


def render(title: str, pairs: list[tuple[str, str, float]], top: int, threshold: float) -> list[str]:
    ranked = sorted(pairs, key=lambda p: (-p[2], p[0], p[1]))
    above = sum(1 for p in pairs if p[2] > threshold)
    lines = [f"## {title}", ""]
    lines.append(f"Pairs compared: {len(pairs)}. Pairs above {threshold}: {above}.")
    lines.append("")
    lines.append("| rank | A id | B id | score |")
    lines.append("|---|---|---|---|")
    for rank, (id_a, id_b, score) in enumerate(ranked[:top], start=1):
        lines.append(f"| {rank} | {id_a} | {id_b} | {score:.3f} |")
    lines.append("")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description="Near-duplicate check between two gold-format YAML files.")
    ap.add_argument("file_a", type=Path)
    ap.add_argument("file_b", type=Path)
    ap.add_argument("--top", type=int, default=10, help="pairs listed per measure")
    ap.add_argument("--threshold", type=float, default=0.6, help="count pairs with a score above this")
    ap.add_argument("--out", type=Path, default=None, help="also write the report to this markdown file")
    args = ap.parse_args()

    items_a = load_items(args.file_a)
    items_b = load_items(args.file_b)
    q_pairs = question_similarity(items_a, items_b)
    s_pairs, skipped = sql_similarity(items_a, items_b)

    lines = [
        f"# Leak check: A = {args.file_a.name}, B = {args.file_b.name}",
        "",
        f"A: {len(items_a)} items, B: {len(items_b)} items. Ids and scores only.",
        "",
    ]
    lines += render("Question text (TF-IDF cosine)", q_pairs, args.top, args.threshold)
    lines += render("SQL (sqlglot-normalised, SequenceMatcher ratio)", s_pairs, args.top, args.threshold)
    null_a = sum(1 for i in items_a if i.get("gold_sql") is None)
    null_b = sum(1 for i in items_b if i.get("gold_sql") is None)
    lines.append(f"SQL measure: skipped for null gold_sql (A: {null_a}, B: {null_b}); "
                 f"unparseable: {', '.join(skipped) if skipped else 'none'}.")
    lines.append("")

    report = "\n".join(lines)
    print(report)
    if args.out is not None:
        args.out.write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
