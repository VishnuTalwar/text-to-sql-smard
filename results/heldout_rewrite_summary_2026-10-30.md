# Held-out rewrite of h2_01 and hu_03: summary (2026-10-30)

Ids and scores only. No question text, no SQL. Only h2_01 and hu_03 were changed in `heldout_smard.yaml`; the other 28 items are untouched.

## Validator
`python grader/validate_gold_file.py heldout_smard.yaml`: 0 failures, 0 warnings, RESULT: PASS. The h2_01 gold_sql returns 1 row, 2 columns. The hu_03 beleg_sql returns a count of 0 (no rows).

## Leak check against gold_set_smard.yaml
- Text pairs above 0.6: **0** of 2520.
- SQL pairs above 0.6: 510 of 2052, 36 of them exactly 1.000. Literals are masked, so this mostly reflects shared query shape. It was 515 and 37 before the rewrite.
- Top 5 text pairs:

| rank | held-out id | exam id | text score |
|---|---|---|---|
| 1 | h1_06 | t1_29 | 0.590 |
| 2 | h1_10 | t1_35 | 0.567 |
| 3 | h1_01 | u_08 | 0.546 |
| 4 | h2_08 | t3_10 | 0.537 |
| 5 | h1_01 | t1_01 | 0.531 |

## The two rewritten items

| item | closest exam item by text | closest exam item by SQL |
|---|---|---|
| h2_01 | t3_08, 0.337 | t2_16, 0.821 |
| hu_03 | t1_06, 0.462 | n/a (gold_sql is null) |

- h2_01: no exam item is the same question. The closest by shape are t2_12 and t3_08 (same type only). The high SQL score against t2_16 comes from a shared grouped-average-of-price structure, not from the same question.
- hu_03: no exam item is the same question. The closest tier-0 item is u_08 (same type only: a period after the data ends, different table, aggregate and month).
