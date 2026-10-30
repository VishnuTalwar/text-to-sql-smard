"""
Structural comparison of the gold_sql of two gold-set YAML files.

    python grader/structure_check.py A.yaml B.yaml [--near N] [--ids ID,ID] [--out REPORT.md]

For every pair (item of A, item of B) the abstract structure of the two gold_sql is
compared with dates, energy sources and price zones masked. The features are:

  tables         tables read (CTE names excluded)
  measure        columns inside aggregate functions
  metrik         verbrauch.metrik literal(s)
  measure_pred   predicates on mwh / preis_eur_mwh (WHERE and FILTER)
  aggs           aggregate functions (ranking functions count as window, not aggregate)
  group          grain of each GROUP BY key: day, trunc-month, extract-hour, weekday,
                 weekend-split, case-group, by-source, by-zone, ...
  order_dir      direction of the first outer ORDER BY key
  limit          outer LIMIT value
  cte, join, window, filter_clause (FILTER), having, ratio (a division), case
  change         a division whose numerator contains a subtraction (change, not share)
  src, zone      selection on energietraeger / preiszone: none, single, set
  time           "point" for an exact timestamp match, otherwise "masked" (ranges ignored)

Verdict per pair:
  same question   no feature differs
  same type only  at least one feature differs

Tier-0 items (gold_sql null) have no structure and are not compared; their ids are listed.
The tool prints ids, feature names and verdicts only, never question text or SQL, so its
output is safe to share whichever file is B (including heldout_smard.yaml).

Exit code 0 if no pair is "same question", 1 if at least one is, 2 if a file cannot be read.
With --ids only those items of A are compared.
"""

import argparse
import re
import sys
from pathlib import Path

import sqlglot
import yaml
from sqlglot import exp

FEATURES = [
    "tables", "measure", "metrik", "measure_pred", "aggs", "group", "order_dir", "limit",
    "cte", "join", "window", "filter_clause", "having", "ratio", "change", "src", "zone",
    "case", "time",
]
MASKED_COLUMNS = {"zeitpunkt", "energietraeger", "preiszone"}
RANKING_FUNCS = {"rank", "denserank", "rownumber", "ntile", "percentrank"}


def _grain(e: exp.Expression) -> str:
    s = e.sql(dialect="postgres").lower()
    if "isodow" in s and "case" in s:
        return "weekend-split"
    if "to_char" in s and "day" in s:
        return "weekday"
    if "case" in s:
        return "case-group"
    m = re.search(r"date_trunc\('(\w+)'", s)
    if m:
        return "trunc-" + m.group(1)
    m = re.search(r"extract\((\w+) from", s)
    if m:
        return "extract-" + m.group(1)
    if "as date" in s or "::date" in s:
        return "day"
    bare = s.strip('"')
    if bare == "energietraeger":
        return "by-source"
    if bare == "preiszone":
        return "by-zone"
    if bare == "zeitpunkt":
        return "raw-timestamp"
    return "other"


def _group_grains(tree: exp.Expression) -> str:
    """Grain of every GROUP BY key, resolved against the SELECT that owns the GROUP BY
    (so keys inside a CTE are resolved too)."""
    grains = []
    for g in tree.find_all(exp.Group):
        sel = g.parent.expressions if isinstance(g.parent, exp.Select) else []
        for ge in g.expressions:
            if isinstance(ge, exp.Literal) and ge.is_int and 1 <= int(ge.name) <= len(sel):
                ge = sel[int(ge.name) - 1]
            elif isinstance(ge, exp.Column):
                for s in sel:
                    if isinstance(s, exp.Alias) and s.alias == ge.name:
                        ge = s
                        break
            if isinstance(ge, exp.Alias):
                ge = ge.this
            grains.append(_grain(ge))
    return ",".join(sorted(grains))


def _selection_kind(tree: exp.Expression, column: str) -> str:
    """none / single (one equality literal) / set (IN list or <>) for a masked column."""
    kinds = set()
    for e in tree.find_all(exp.In):
        if any(c.name == column for c in e.find_all(exp.Column)):
            kinds.add("set")
    for e in tree.find_all(exp.EQ):
        if isinstance(e.left, exp.Column) and e.left.name == column and isinstance(e.right, exp.Literal):
            kinds.add("single")
    for e in tree.find_all(exp.NEQ):
        if isinstance(e.left, exp.Column) and e.left.name == column:
            kinds.add("set")
    if not kinds:
        return "none"
    return "set" if "set" in kinds else "single"


def _conjuncts(e: exp.Expression):
    if isinstance(e, exp.And):
        yield from _conjuncts(e.left)
        yield from _conjuncts(e.right)
    else:
        yield e


def _measure_predicates(tree: exp.Expression) -> str:
    preds = []
    for w in tree.find_all(exp.Where):
        for c in _conjuncts(w.this):
            cols = {x.name for x in c.find_all(exp.Column)}
            if cols and cols <= MASKED_COLUMNS | {"metrik"}:
                continue
            hit = cols & {"preis_eur_mwh", "mwh"}
            if hit:
                preds.append(type(c).__name__ + ":" + ",".join(sorted(hit)))
    return ",".join(sorted(preds))


def features(sql: str) -> dict:
    tree = sqlglot.parse_one(sql, read="postgres")
    cte_names = {c.alias_or_name for c in tree.find_all(exp.CTE)}

    aggs = {type(a).__name__.lower() for a in tree.find_all(exp.AggFunc)} - RANKING_FUNCS
    measure = set()
    for a in tree.find_all(exp.AggFunc):
        if type(a).__name__.lower() not in RANKING_FUNCS:
            measure |= {c.name for c in a.find_all(exp.Column)}
    metrik = sorted(
        lit.this.lower()
        for lit in tree.find_all(exp.Literal)
        if lit.is_string
        and isinstance(lit.parent, exp.EQ)
        and any(c.name == "metrik" for c in lit.parent.find_all(exp.Column))
    )
    order = tree.args.get("order")
    limit = tree.args.get("limit")
    point = any(
        isinstance(e.left, exp.Column) and e.left.name == "zeitpunkt" and isinstance(e.right, exp.Literal)
        for e in tree.find_all(exp.EQ)
    )

    return {
        "tables": ",".join(sorted({t.name for t in tree.find_all(exp.Table)} - cte_names)),
        "measure": ",".join(sorted(measure - MASKED_COLUMNS)),
        "metrik": ",".join(metrik),
        "measure_pred": _measure_predicates(tree),
        "aggs": ",".join(sorted(aggs)),
        "group": _group_grains(tree),
        "order_dir": ("desc" if order.expressions[0].args.get("desc") else "asc") if order else "",
        "limit": limit.expression.name if limit else "",
        "cte": bool(cte_names),
        "join": any(True for _ in tree.find_all(exp.Join)),
        "window": any(True for _ in tree.find_all(exp.Window)),
        "filter_clause": any(True for _ in tree.find_all(exp.Filter)),
        "having": any(True for _ in tree.find_all(exp.Having)),
        "ratio": any(True for _ in tree.find_all(exp.Div)),
        "change": any(any(True for _ in d.this.find_all(exp.Sub)) for d in tree.find_all(exp.Div)),
        "src": _selection_kind(tree, "energietraeger"),
        "zone": _selection_kind(tree, "preiszone"),
        "case": any(True for _ in tree.find_all(exp.Case)),
        "time": "point" if point else "masked",
    }


def differing(fa: dict, fb: dict) -> list[str]:
    return [k for k in FEATURES if fa[k] != fb[k]]


def load_items(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["fragen"]


def split_items(items: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """({id: features} for items with gold_sql, ids without gold_sql)."""
    feats, no_sql = {}, []
    for it in items:
        if it.get("gold_sql"):
            feats[it["id"]] = features(it["gold_sql"])
        else:
            no_sql.append(it["id"])
    return feats, no_sql


def compare(fa: dict[str, dict], fb: dict[str, dict]) -> list[tuple[str, str, list[str]]]:
    return [(a, b, differing(va, vb)) for a, va in fa.items() for b, vb in fb.items()]


def render(path_a, path_b, fa, fb, no_sql_a, no_sql_b, pairs, near: int) -> list[str]:
    same = [(a, b) for a, b, d in pairs if not d]
    close = [(a, b, d) for a, b, d in pairs if 0 < len(d) <= near]
    lines = [
        f"# Structure check: A = {path_a}, B = {path_b}",
        "",
        f"A: {len(fa)} items with gold_sql, B: {len(fb)} items with gold_sql. Ids and feature names only.",
        f"Not compared (gold_sql null): A: {', '.join(no_sql_a) or 'none'}; B: {', '.join(no_sql_b) or 'none'}.",
        f"Pairs compared: {len(pairs)}.",
        "",
        f"## Same question: {len(same)} pairs, {len({a for a, _ in same})} of {len(fa)} A items",
        "",
    ]
    if same:
        by_a: dict[str, list[str]] = {}
        for a, b in same:
            by_a.setdefault(a, []).append(b)
        lines += ["| A id | same question as (B ids) |", "|---|---|"]
        lines += [f"| {a} | {', '.join(bs)} |" for a, bs in by_a.items()]
    else:
        lines.append("None.")
    lines += ["", f"## Same type only, {near} or fewer differing features: {len(close)} pairs", ""]
    if close:
        lines += ["| A id | B id | differing features |", "|---|---|---|"]
        lines += [f"| {a} | {b} | {', '.join(d)} |" for a, b, d in sorted(close)]
    else:
        lines.append("None.")
    lines += ["", f"All other pairs differ in more than {near} features: same type only."]
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare the structure of the gold_sql of two gold-set YAML files.")
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--near", type=int, default=1,
                    help="also list pairs with 1..N differing features (default 1; 0 = same question only)")
    ap.add_argument("--ids", help="comma-separated ids of A to compare (default: all)")
    ap.add_argument("--out", type=Path, help="also write the report to this file")
    args = ap.parse_args()

    try:
        items_a, items_b = load_items(args.a), load_items(args.b)
    except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
        print(f"Cannot read input: {exc}")
        sys.exit(2)
    if args.ids:
        wanted = set(args.ids.split(","))
        items_a = [it for it in items_a if it.get("id") in wanted]

    fa, no_sql_a = split_items(items_a)
    fb, no_sql_b = split_items(items_b)
    pairs = compare(fa, fb)
    lines = render(args.a, args.b, fa, fb, no_sql_a, no_sql_b, pairs, args.near)
    print("\n".join(lines))
    if args.out:
        args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nReport written to {args.out}")
    sys.exit(1 if any(not d for _, _, d in pairs) else 0)


if __name__ == "__main__":
    main()
