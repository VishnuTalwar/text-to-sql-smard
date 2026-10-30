# Leak check: heldout_smard.yaml (re-frozen) vs gold_set_smard.yaml (2026-10-30)

Rerun on the re-frozen file after h2_01 and hu_03 were replaced. This replaces the first version of this report (kept in git history at commit 36b45cf), which was run on the first freeze.

## Summary (ids and scores only)

- Text pairs above 0.6: **0** of 2520.
- Top 5 text pairs:

| rank | held-out id | exam id | text score |
|---|---|---|---|
| 1 | h1_06 | t1_29 | 0.590 |
| 2 | h1_10 | t1_35 | 0.567 |
| 3 | h1_01 | u_08 | 0.546 |
| 4 | h2_08 | t3_10 | 0.537 |
| 5 | h1_01 | t1_01 | 0.531 |

- The two pairs that were the same question in the first freeze, now:

| pair | text score | SQL score | judgement |
|---|---|---|---|
| hu_03 vs u_08 | 0.180 | n/a (gold_sql is null in both) | same type only |
| h2_01 vs t2_01 | 0.071 | 0.448 | same type only |

- No exam item is the same question as the new h2_01 or the new hu_03 (side-by-side check against every exam item; see heldout_rewrite_summary_2026-10-30.md).
- SQL pairs above 0.6: 510 of 2052, 36 of them exactly 1.000. Literals are masked, so this mostly reflects shared query shape.

Method: TF-IDF cosine on the lowercased question text; SQL normalised with sqlglot (literals masked) and compared with difflib SequenceMatcher. "Above" means strictly greater than the threshold. A low text score alone does not show a different question; the side-by-side check does.

---

# Full output of grader/leak_check.py

A: 30 items, B: 84 items. Ids and scores only.

## Question text (TF-IDF cosine)

Pairs compared: 2520. Pairs above 0.6: 0.

| rank | A id | B id | score |
|---|---|---|---|
| 1 | h1_06 | t1_29 | 0.590 |
| 2 | h1_10 | t1_35 | 0.567 |
| 3 | h1_01 | u_08 | 0.546 |
| 4 | h2_08 | t3_10 | 0.537 |
| 5 | h1_01 | t1_01 | 0.531 |
| 6 | h2_03 | t3_02 | 0.511 |
| 7 | h2_07 | t2_12 | 0.503 |
| 8 | h1_10 | t1_16 | 0.495 |
| 9 | hu_01 | t1_06 | 0.478 |
| 10 | hu_03 | t1_06 | 0.462 |

## SQL (sqlglot-normalised, SequenceMatcher ratio)

Pairs compared: 2052. Pairs above 0.6: 510.

| rank | A id | B id | score |
|---|---|---|---|
| 1 | h1_01 | t1_01 | 1.000 |
| 2 | h1_01 | t1_08 | 1.000 |
| 3 | h1_01 | t1_12 | 1.000 |
| 4 | h1_01 | t1_14 | 1.000 |
| 5 | h1_01 | t1_15 | 1.000 |
| 6 | h1_01 | t1_17 | 1.000 |
| 7 | h1_01 | t1_19 | 1.000 |
| 8 | h1_01 | t1_23 | 1.000 |
| 9 | h1_01 | t1_28 | 1.000 |
| 10 | h1_01 | t1_34 | 1.000 |

SQL measure: skipped for null gold_sql (A: 3, B: 8); unparseable: none.
