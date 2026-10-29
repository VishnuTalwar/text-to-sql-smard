# Leak check: heldout_smard.yaml vs gold_set_smard.yaml (2026-10-30)

## Summary (ids and scores only)

- Text pairs above 0.6: **0** (of 2520).
- Top 5 text pairs:

| rank | held-out id | exam id | text score |
|---|---|---|---|
| 1 | h1_06 | t1_29 | 0.591 |
| 2 | h1_10 | t1_35 | 0.565 |
| 3 | h1_01 | u_08 | 0.552 |
| 4 | h2_08 | t3_10 | 0.537 |
| 5 | h1_01 | t1_01 | 0.533 |

- The two pairs checked by hand:

| pair | text score | SQL score | judgement |
|---|---|---|---|
| hu_03 vs u_08 | 0.314 | n/a (gold_sql is null in both) | same question |
| h2_01 vs t2_01 | 0.077 | 0.849 | same question |

- hu_03 vs u_08: same question.
- h2_01 vs t2_01: same question.
- SQL pairs above 0.6: 515 of 2052, 37 of them exactly 1.000. Literals are masked, so this mostly reflects shared query shape, not copied items.

Method: TF-IDF cosine on the lowercased question text; SQL normalised with sqlglot (literals masked) and compared with difflib SequenceMatcher. "Above" means strictly greater than the threshold.

---

# Full output of grader/leak_check.py

A: 30 items, B: 84 items. Ids and scores only.

## Question text (TF-IDF cosine)

Pairs compared: 2520. Pairs above 0.6: 0.

| rank | A id | B id | score |
|---|---|---|---|
| 1 | h1_06 | t1_29 | 0.591 |
| 2 | h1_10 | t1_35 | 0.565 |
| 3 | h1_01 | u_08 | 0.552 |
| 4 | h2_08 | t3_10 | 0.537 |
| 5 | h1_01 | t1_01 | 0.533 |
| 6 | h2_03 | t3_02 | 0.510 |
| 7 | h2_07 | t2_12 | 0.504 |
| 8 | h1_10 | t1_16 | 0.494 |
| 9 | hu_01 | t1_06 | 0.487 |
| 10 | h1_09 | t1_33 | 0.447 |

## SQL (sqlglot-normalised, SequenceMatcher ratio)

Pairs compared: 2052. Pairs above 0.6: 515.

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
