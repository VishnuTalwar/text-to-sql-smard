# Leak check: A = heldout_smard.yaml, B = gold_set_smard.yaml

A: 30 items, B: 84 items. Ids and scores only.

## Question text (TF-IDF cosine)

Pairs compared: 2520. Pairs above 0.6: 2.

| rank | A id | B id | score |
|---|---|---|---|
| 1 | hu_03 | u_08 | 0.742 |
| 2 | h2_01 | t2_01 | 0.638 |
| 3 | h1_06 | t1_29 | 0.591 |
| 4 | h1_10 | t1_35 | 0.568 |
| 5 | h2_08 | t3_10 | 0.537 |
| 6 | h1_01 | u_08 | 0.536 |
| 7 | h1_01 | t1_01 | 0.534 |
| 8 | h2_03 | t3_02 | 0.514 |
| 9 | h2_07 | t2_12 | 0.506 |
| 10 | h1_10 | t1_16 | 0.498 |

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
