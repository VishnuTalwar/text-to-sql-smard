# ex-b vs v2b and ex-a, exam (84 items), 3 runs each, 2026-10-31

v2b = `v2b_t0_run{1,2,3}_2026-10-27`; ex-a = `exa_run{1,2,3}_2026-10-31` (fixed 8 examples); ex-b = `exb_run{1,2,3}_2026-10-31` (3 retrieved examples per question, most similar last, text-embedding-3-small). Same model, temperature 0, seed 0, same v2b base prompt. Exam only; the held-out set was not run.

## 1. Totals per run and per tier

| tier | n | v2b r1/r2/r3 | v2b mean | ex-a r1/r2/r3 | ex-a mean | ex-b r1/r2/r3 | ex-b mean | ex-b − v2b | ex-b − ex-a |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 8 | 7/7/7 | 7.00 | 8/8/8 | 8.00 | 7/7/7 | 7.00 | +0.00 | -1.00 |
| 1 | 35 | 34/34/34 | 34.00 | 32/33/33 | 32.67 | 31/32/32 | 31.67 | -2.33 | -1.00 |
| 2 | 25 | 17/18/18 | 17.67 | 16/15/16 | 15.67 | 15/16/16 | 15.67 | -2.00 | +0.00 |
| 3 | 12 | 2/2/2 | 2.00 | 3/3/3 | 3.00 | 2/2/2 | 2.00 | +0.00 | -1.00 |
| 4 | 4 | 0/0/0 | 0.00 | 0/0/0 | 0.00 | 0/0/0 | 0.00 | +0.00 | +0.00 |
| **all** | 84 | 60/61/61 | 60.67 | 59/59/60 | 59.33 | 55/57/57 | 56.33 | -4.33 | -3.00 |

## 2. Questions that changed, ex-b vs v2b

### 0/3 → 3/3 (4)

| id | tier | v2b | ex-b | v2b failures | ex-b failures | grader detail |
|---|---|---|---|---|---|---|
| t1_18 | 1 | 0/3 | 3/3 | r1:cols; r2:cols; r3:cols | r1:pass; r2:pass; r3:pass | v2b: column count mismatch at row 0: gold=1 agent=2; ex-b: - |
| t2_20 | 2 | 0/3 | 3/3 | r1:value; r2:value; r3:value | r1:pass; r2:pass; r3:pass | v2b: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.date(2025, 10, 1) agent=Decimal('4'); ex-b: - |
| t2_25 | 2 | 0/3 | 3/3 | r1:value; r2:value; r3:value | r1:pass; r2:pass; r3:pass | v2b: cell mismatch row 0 col 0: text mismatch: gold='Polen' agent='Schweden 4'; ex-b: - |
| t3_08 | 3 | 0/3 | 3/3 | r1:value; r2:value; r3:value | r1:pass; r2:pass; r3:pass | v2b: cell mismatch row 0 col 0: text mismatch: gold='Werktag' agent='Weekday'; ex-b: - |

### 3/3 → 0/3 (7)

| id | tier | v2b | ex-b | v2b failures | ex-b failures | grader detail |
|---|---|---|---|---|---|---|
| t1_12 | 1 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:decline | v2b: -; ex-b: declined (no SQL) |
| t1_22 | 1 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:decline | v2b: -; ex-b: declined (no SQL) |
| t2_03 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:decline | v2b: -; ex-b: declined (no SQL) |
| t2_16 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:value; r2:value; r3:value | v2b: -; ex-b: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.date(2025, 1, 1) agent=1 |
| t2_22 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:value; r2:value; r3:value | v2b: -; ex-b: cell mismatch row 0 col 0: text mismatch: gold='Photovoltaik' agent='Kernenergie' |
| t2_23 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:value; r2:value; r3:value | v2b: -; ex-b: cell mismatch row 0 col 0: could not compare numerically: gold=2023 agent=datetime.date(2023, 1, 1) |
| t3_05 | 3 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:decline | v2b: -; ex-b: declined (no SQL) |

### Partial changes (6)

| id | tier | v2b | ex-b | v2b failures | ex-b failures | grader detail |
|---|---|---|---|---|---|---|
| t1_02 | 1 | 3/3 | 1/3 | r1:pass; r2:pass; r3:pass | r1:cols; r2:pass; r3:cols | v2b: -; ex-b: column count mismatch at row 0: gold=1 agent=2 |
| t1_19 | 1 | 3/3 | 1/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:pass | v2b: -; ex-b: declined (no SQL) |
| t2_01 | 2 | 3/3 | 2/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:pass; r3:pass | v2b: -; ex-b: declined (no SQL) |
| t2_06 | 2 | 2/3 | 3/3 | r1:cols; r2:pass; r3:pass | r1:pass; r2:pass; r3:pass | v2b: column count mismatch at row 0: gold=2 agent=1; ex-b: - |
| t2_11 | 2 | 3/3 | 1/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:pass; r3:decline | v2b: -; ex-b: declined (no SQL) |
| t2_14 | 2 | 0/3 | 2/3 | r1:value; r2:value; r3:value | r1:pass; r2:value; r3:pass | v2b: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.datetime(2024, 12, 12, 17, 0) agent=date / cell mismatch row 0 col 0: datetime mismatch: gold=datetime.datetime(2024, 12, 12, 17, 0) agent=date; ex-b: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.datetime(2024, 12, 12, 17, 0) agent=date |

Same questions under ex-a (passes of 3): t1_18 0/3, t2_20 3/3, t2_25 3/3, t3_08 0/3, t1_12 3/3, t1_22 3/3, t2_03 2/3, t2_16 0/3, t2_22 3/3, t2_23 3/3, t3_05 0/3, t1_02 3/3, t1_19 3/3, t2_01 3/3, t2_06 3/3, t2_11 3/3, t2_14 0/3

### Changes vs ex-a (ex-b vs ex-a), summary

0/3 → 3/3 under ex-b: t1_18, t2_09, t2_12, t2_24, t3_08. 3/3 → 0/3: t1_12, t1_22, t2_22, t2_23, t3_02, u_08. Questions whose pass count differs at all: 21.

Always failing (0/3) in v2b, ex-a and ex-b: t2_07, t2_15, t2_18, t2_21, t3_03, t3_04, t3_07, t3_10, t3_11, t3_12, t4_01, t4_02, t4_03, t4_04

## 3. Failures by kind (sum over 3 runs, per-run in brackets)

| kind | v2b | ex-a | ex-b |
|---|---|---|---|
| wrong column count | 20 (7, 7, 6) | 11 (5, 3, 3) | 8 (3, 2, 3) |
| wrong row count | 15 (5, 5, 5) | 5 (2, 2, 1) | 4 (2, 1, 1) |
| wrong value | 27 (9, 9, 9) | 23 (7, 8, 8) | 16 (5, 6, 5) |
| SQL error | 5 (2, 1, 2) | 0 (0, 0, 0) | 1 (0, 1, 0) |
| wrong decline | 0 (0, 0, 0) | 35 (11, 12, 12) | 51 (18, 16, 17) |
| tier 0: SQL instead of decline | 3 (1, 1, 1) | 0 (0, 0, 0) | 3 (1, 1, 1) |
| total failures | 70 | 74 | 83 |

## 4. Copy check: agent SQL (sqlglot-normalised, SequenceMatcher) vs the examples that were in its own prompt, ratio > 0.9

- ex-b vs its own 3 retrieved examples: **12 hits** (highest ratio 0.980).
- ex-a vs its fixed 8: 3 hits (highest 0.979).
- Controls: ex-b vs the 25 pool examples NOT in its prompt: 12 hits (highest 0.925); v2b (no examples) vs the 8 ex-a examples: 0 hits (highest 0.744).

ex-b hits:

| run | question | example | ratio | passed |
|---|---|---|---|---|
| r1 | t1_33 | ex_03 | 0.954 | yes |
| r1 | t2_10 | ex_19 | 0.98 | yes |
| r1 | t2_16 | ex_20 | 0.979 | no |
| r1 | t2_24 | ex_15 | 0.929 | yes |
| r2 | t1_33 | ex_03 | 0.954 | yes |
| r2 | t2_10 | ex_19 | 0.98 | yes |
| r2 | t2_16 | ex_20 | 0.979 | no |
| r2 | t2_24 | ex_15 | 0.929 | yes |
| r3 | t1_33 | ex_03 | 0.954 | yes |
| r3 | t2_10 | ex_19 | 0.98 | yes |
| r3 | t2_16 | ex_20 | 0.979 | no |
| r3 | t2_24 | ex_15 | 0.929 | yes |

ex-a hits:

| run | question | example | ratio | passed |
|---|---|---|---|---|
| r1 | t2_16 | ex_20 | 0.979 | no |
| r2 | t2_16 | ex_20 | 0.979 | no |
| r3 | t2_16 | ex_20 | 0.979 | no |

ex-b control hits: r1 t1_05~ex_02 0.925; r1 t1_29~ex_02 0.921; r1 t2_10~ex_22 0.905; r1 t2_16~ex_22 0.904; r2 t1_05~ex_02 0.925; r2 t1_29~ex_02 0.921; r2 t2_10~ex_22 0.905; r2 t2_16~ex_22 0.904; r3 t1_05~ex_02 0.925; r3 t1_29~ex_02 0.921; r3 t2_10~ex_22 0.905; r3 t2_16~ex_22 0.904

## 5. Wrong declines (tier 1-4 declined)

Counts per run: v2b [0, 0, 0], ex-a [11, 12, 12], ex-b [18, 16, 17]. Tier 0 correctly declined per run (of 8): v2b [7, 7, 7], ex-a [8, 8, 8], ex-b [7, 7, 7].

ex-b, per run, with the model's reason:

**r1** (18)

- t1_12 (tier 1, top-1 sim 0.650 to ex_18): NO_QUERY: The table does not contain data for the year 2026.
- t1_19 (tier 1, top-1 sim 0.650 to ex_18): NO_QUERY: The term "Speicherkraftwerken" is ambiguous and not clearly defined in the provided tables.
- t1_22 (tier 1, top-1 sim 0.778 to ex_19): NO_QUERY: The exact price at midday on 3 March 2025 is missing.
- t2_01 (tier 2, top-1 sim 0.569 to ex_28): NO_QUERY: The time period for the query is not specified.
- t2_03 (tier 2, top-1 sim 0.467 to ex_21): NO_QUERY: The table does not contain information about hourly solar output.
- t2_11 (tier 2, top-1 sim 0.614 to ex_18): NO_QUERY: The question is missing.
- t2_18 (tier 2, top-1 sim 0.577 to ex_06): NO_QUERY: The table does not contain information about the year for each timestamp.
- t3_04 (tier 3, top-1 sim 0.507 to ex_28): NO_QUERY: The specific day when electricity was most expensive is not provided.
- t3_05 (tier 3, top-1 sim 0.640 to ex_15): NO_QUERY: The table does not contain daily maximum and minimum grid load values needed to calculate the swing.
- t3_07 (tier 3, top-1 sim 0.492 to ex_04): NO_QUERY: The share of consumption covered by renewables requires data on renewable generation and total consumption, but the tables do not directly provide this comparis
- t3_09 (tier 3, top-1 sim 0.637 to ex_08): NO_QUERY: The question requires identifying the windiest day, which needs additional data or calculations not provided in the tables.
- t3_10 (tier 3, top-1 sim 0.695 to ex_27): NO_QUERY: The table does not contain information about the total electricity generation for all energy sources.
- t3_11 (tier 3, top-1 sim 0.634 to ex_21): NO_QUERY: The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to correlate solar generation with prices.
- t3_12 (tier 3, top-1 sim 0.543 to ex_11): NO_QUERY: The table does not provide information on daily averages for comparison.
- t4_01 (tier 4, top-1 sim 0.347 to ex_17): NO_QUERY: The question requires identifying the top producer per week, but the necessary logic to determine the top producer is not specified.
- t4_02 (tier 4, top-1 sim 0.379 to ex_11): NO_QUERY: The table does not contain information about unbroken stretches or durations.
- t4_03 (tier 4, top-1 sim 0.482 to ex_05): NO_QUERY: The tables do not provide a direct way to compare total generation and consumption for each hour.
- t4_04 (tier 4, top-1 sim 0.712 to ex_06): NO_QUERY: Information about consecutive quarter-hours is missing.

**r2** (16)

- t1_12 (tier 1, top-1 sim 0.650 to ex_18): NO_QUERY: Data for February 2026 is not available in the table.
- t1_19 (tier 1, top-1 sim 0.650 to ex_18): NO_QUERY: The term "Speicherkraftwerken" is ambiguous and not directly represented in the tables.
- t1_22 (tier 1, top-1 sim 0.778 to ex_19): NO_QUERY: The specific timestamp for midday on 3 March 2025 is missing.
- t2_03 (tier 2, top-1 sim 0.467 to ex_21): NO_QUERY: The table does not contain information about hourly solar output.
- t2_15 (tier 2, top-1 sim 0.602 to ex_18): NO_QUERY: The question does not specify which energy sources are considered "Ökostrom" and which are "konventionell".
- t2_18 (tier 2, top-1 sim 0.577 to ex_06): NO_QUERY: The table does not contain information about the year for each timestamp.
- t3_04 (tier 3, top-1 sim 0.507 to ex_28): NO_QUERY: The specific day when electricity was most expensive is not provided.
- t3_05 (tier 3, top-1 sim 0.640 to ex_15): NO_QUERY: The table does not contain daily aggregated data to calculate the swing between highest and lowest grid load for each day.
- t3_07 (tier 3, top-1 sim 0.492 to ex_04): NO_QUERY: The table does not provide direct information on which energy sources are considered renewables.
- t3_09 (tier 3, top-1 sim 0.637 to ex_08): NO_QUERY: The date of the windiest day for onshore wind is missing.
- t3_10 (tier 3, top-1 sim 0.695 to ex_27): NO_QUERY: The table does not contain information about the total electricity generation for all energy sources.
- t3_11 (tier 3, top-1 sim 0.634 to ex_21): NO_QUERY: The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to compare prices with solar generation level
- t3_12 (tier 3, top-1 sim 0.543 to ex_11): NO_QUERY: The table does not provide information on daily averages for comparison.
- t4_01 (tier 4, top-1 sim 0.347 to ex_17): NO_QUERY: The question requires weekly aggregation, but the table does not have a direct way to determine the top producer per week without additional context or data.
- t4_03 (tier 4, top-1 sim 0.482 to ex_05): NO_QUERY: The tables do not provide direct information on hourly generation versus consumption comparison.
- t4_04 (tier 4, top-1 sim 0.712 to ex_06): NO_QUERY: Information about consecutive quarter-hours is missing.

**r3** (17)

- t1_12 (tier 1, top-1 sim 0.650 to ex_18): NO_QUERY: The table does not contain data for the year 2026.
- t1_22 (tier 1, top-1 sim 0.778 to ex_19): NO_QUERY: The specific timestamp for midday on 3 March 2025 is missing.
- t2_03 (tier 2, top-1 sim 0.467 to ex_21): NO_QUERY: The table does not have information on hourly solar output.
- t2_11 (tier 2, top-1 sim 0.614 to ex_18): NO_QUERY: The question does not specify the energy sources to be included.
- t2_15 (tier 2, top-1 sim 0.602 to ex_18): NO_QUERY: The question does not specify which energy sources are considered "Ökostrom" and which are "konventionell".
- t2_18 (tier 2, top-1 sim 0.577 to ex_06): NO_QUERY: The table does not contain information about the year for each timestamp.
- t3_04 (tier 3, top-1 sim 0.507 to ex_28): NO_QUERY: The specific day when electricity was most expensive is not provided.
- t3_05 (tier 3, top-1 sim 0.640 to ex_15): NO_QUERY: The table does not contain daily high and low grid load values to calculate the swing.
- t3_07 (tier 3, top-1 sim 0.492 to ex_04): NO_QUERY: The question requires data on renewable generation, which is not directly available in the tables.
- t3_09 (tier 3, top-1 sim 0.637 to ex_08): NO_QUERY: The specific date of the windiest day for onshore wind is missing.
- t3_10 (tier 3, top-1 sim 0.695 to ex_27): NO_QUERY: The table does not contain information about the total electricity generation for all energy sources.
- t3_11 (tier 3, top-1 sim 0.634 to ex_21): NO_QUERY: The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to correlate solar generation with prices.
- t3_12 (tier 3, top-1 sim 0.543 to ex_11): NO_QUERY: The table does not provide information on daily averages for comparison.
- t4_01 (tier 4, top-1 sim 0.347 to ex_17): NO_QUERY: The question requires weekly aggregation of generation data, which is not directly available in the tables.
- t4_02 (tier 4, top-1 sim 0.379 to ex_11): NO_QUERY: The table does not contain information about unbroken stretches or durations.
- t4_03 (tier 4, top-1 sim 0.482 to ex_05): NO_QUERY: The tables do not provide direct information on hourly generation versus consumption comparison.
- t4_04 (tier 4, top-1 sim 0.712 to ex_06): NO_QUERY: Information about consecutive quarter-hours is missing.

Questions declined at least once: ex-a 14, ex-b 19; in both: 11 (t2_03, t2_15, t3_04, t3_05, t3_07, t3_11, t3_12, t4_01, t4_02, t4_03, t4_04). Only ex-b: t1_12, t1_19, t1_22, t2_01, t2_11, t2_18, t3_09, t3_10. Only ex-a: t1_25, t1_26, t2_12.

## 6. Decline vs similarity

ex-b similarity = top-1 cosine similarity of the question to its 3 retrieved examples. ex-a similarity = highest cosine similarity of the question to any of the 8 fixed examples. Both from the embeddings cache (text-embedding-3-small); tier 1-4 questions only (tier 0 is excluded because declining is correct there). p = Mann-Whitney U, two-sided, on the per-question comparison.

| row | unit | n declined | mean sim declined | n not declined | mean sim not declined | difference | p |
|---|---|---|---|---|---|---|---|
| ex-b | per question (declined ≥1 run vs never) | 19 | 0.578 | 57 | 0.585 | -0.007 | 0.952 |
| ex-b | per question-run | 51 | 0.579 | 177 | 0.584 | -0.005 | - |
| ex-a | per question (declined ≥1 run vs never) | 14 | 0.482 | 62 | 0.511 | -0.029 | 0.410 |
| ex-a | per question-run | 35 | 0.478 | 193 | 0.511 | -0.033 | - |

For reference, mean over all tier 1-4 questions: ex-b top-1 0.583, ex-a best-of-8 0.506.

Per declined question (ever), ex-a best-of-8 sim / ex-b top-1 sim / declines of 3 in ex-a / declines of 3 in ex-b: t1_12 0.50/0.65/0/3; t1_19 0.56/0.65/0/2; t1_22 0.63/0.78/0/3; t1_25 0.46/0.52/2/0; t1_26 0.63/0.64/2/0; t2_01 0.31/0.57/0/1; t2_03 0.47/0.47/1/3; t2_11 0.51/0.61/0/2; t2_12 0.36/0.43/3/0; t2_15 0.50/0.60/2/2; t2_18 0.58/0.58/0/3; t3_04 0.47/0.51/3/3; t3_05 0.59/0.64/3/3; t3_07 0.44/0.49/2/3; t3_09 0.62/0.64/0/3; t3_10 0.65/0.69/0/3; t3_11 0.58/0.63/2/3; t3_12 0.54/0.54/3/3; t4_01 0.24/0.35/3/3; t4_02 0.38/0.38/3/2; t4_03 0.39/0.48/3/3; t4_04 0.71/0.71/3/3

## 7. Latency and tokens (per API call, 252 calls per row)

| | v2b | ex-a | ex-b |
|---|---|---|---|
| mean latency (s) | 1.48 | 1.09 | 1.16 |
| p95 latency (s) | 2.10 | 1.48 | 1.60 |
| mean prompt tokens | 629 | 1624 | 978 |
| mean completion tokens | 59 | 50 | 46 |

## 8. Per-example retrieval counts (84 questions, 3 slots each)

| example | tier | muster | retrieved | top-1 | in ex-a |
|---|---|---|---|---|---|
| ex_01 | 1 | single total | 13 | 2 |  |
| ex_02 | 1 | single average | 0 | 0 |  |
| ex_03 | 1 | single max | 17 | 2 |  |
| ex_04 | 2 | share | 3 | 2 |  |
| ex_05 | 3 | share per group | 3 | 1 |  |
| ex_06 | 2 | share of count | 6 | 4 | yes |
| ex_07 | 2 | percent change | 1 | 0 | yes |
| ex_08 | 2 | percent change | 15 | 8 |  |
| ex_09 | 2 | argmax | 13 | 3 |  |
| ex_10 | 2 | argmin | 3 | 0 |  |
| ex_11 | 2 | argmin day | 8 | 5 | yes |
| ex_12 | 2 | top-n | 10 | 6 |  |
| ex_13 | 2 | full ranking | 4 | 0 | yes |
| ex_14 | 2 | top-n days | 13 | 4 |  |
| ex_15 | 2 | monthly series | 14 | 5 |  |
| ex_16 | 2 | daily series | 8 | 2 | yes |
| ex_17 | 2 | weekly series | 17 | 4 |  |
| ex_18 | 2 | quarterly series | 12 | 10 |  |
| ex_19 | 2 | hour of day | 12 | 5 |  |
| ex_20 | 2 | month of year | 3 | 0 | yes |
| ex_21 | 3 | weekday | 19 | 5 |  |
| ex_22 | 2 | by year | 2 | 1 |  |
| ex_23 | 2 | weekend vs workday | 8 | 2 |  |
| ex_24 | 2 | two-way split | 4 | 0 | yes |
| ex_25 | 3 | join filter | 3 | 0 |  |
| ex_26 | 3 | join daily series | 15 | 3 | yes |
| ex_27 | 4 | running total | 15 | 1 |  |
| ex_28 | 4 | rank within group | 11 | 9 |  |
| total | | | 252 | 84 | |

Never retrieved: ex_02. Questions retrieving ex_20: t1_11 (rank 3), t1_16 (rank 3), t2_16 (rank 2).

## 9. Notes on the new failures

- **t2_22** ("each source produced on 21 June 2025, sorted highest first"): all 3 ex-b runs write `ORDER BY … DESC` without `NULLS LAST` and rank Kernenergie (NULL) first. Retrieved examples were ex_28, ex_03, ex_11; none of them shows `NULLS LAST`. ex-a's fixed set contains ex_13, which does (`ORDER BY netzlast_mwh DESC NULLS LAST`), and ex-a passed this question 3/3. The v2b prompt carries the NULLS LAST note in the catalog in both rows.
- **t2_23** ("how many quarter-hours per year …"): ex-b returns `date_trunc('year', zeitpunkt)::date` where the gold has the year as an integer. Retrieved examples were ex_17, ex_21, ex_18 (weekly, weekday, quarterly series); ex_22 ("by year", `EXTRACT(YEAR …)::int`) was not retrieved (2 retrievals in total).
- **t2_16** reproduces ex_20 at 0.979 in all 3 runs again, although ex_20 sits at rank 2 for this question, not rank 1.
- **Copy check reading.** Of the 12 ex-b hits above 0.9, only t2_16 (3 of the 12) fails; the other 3 questions (t1_33~ex_03, t2_10~ex_19, t2_24~ex_15) pass, i.e. the examples were the right pattern. The control (ex-b agent SQL against the 25 pool examples not in its prompt) also produces 12 hits at ≥ 0.904, so a ratio above 0.9 alone does not prove copying; it also occurs between queries of the same shape.
- **Tier 0.** ex-b does not repeat ex-a's u_08 gain (tier 0 7/8 per run, same as v2b); the SQL-instead-of-decline case is again one item per run.

## 10. Prediction check (`results/exb_prediction_2026-10-31.md`, written before the run)

1. **"Shape failures (wrong column count, wrong row count, SQL errors) drop compared with v2b, as in ex-a." Confirmed.** Sum over 3 runs: v2b 40 (20 + 15 + 5), ex-a 16 (11 + 5 + 0), ex-b 13 (8 + 4 + 1). Wrong values also fell, 27 → 23 → 16.
2. **"Wrong declines: if ex-a's declines came from examples that did not resemble the question, ex-b cuts them sharply. If they stay high, the cause is the presence of an example block itself."** The first branch is **not confirmed**; the second applies. Wrong declines rose from 35 (ex-a) to 51 (ex-b; 18, 16, 17 per run), against 0 for v2b, although ex-b's examples resemble the question more (mean top-1 similarity 0.583 vs 0.506 best-of-8 for ex-a). Within each row, declined and non-declined tier 1-4 questions have the same similarity: ex-b 0.578 vs 0.585 (p = 0.95), ex-a 0.482 vs 0.511 (p = 0.41). Similarity does not predict declines in either row. What this does not show: that the block itself is the only cause. It was not tested against a block with other contents or format, and the replies give wrong reasons (for example "no data for 2026" for t1_12, "year not in the table" for t2_18) that look like invented grounds, not reasoning about the examples.
3. **"Copying: month questions may still copy ex_20." Confirmed.** t2_16 copies ex_20 at 0.979 in all 3 runs and fails (date expected, integer returned), even though ex_20 was retrieved for only 3 of the 84 questions. The other month questions (t2_09, t2_24) pass under ex-b.
4. **"Tier 1 and tier 0 roughly unchanged." Tier 0: confirmed** (7.00 vs 7.00 for v2b). **Tier 1: not confirmed** (34.00 → 31.67, −2.33 vs v2b; −1.00 vs ex-a). The size is at the edge of the prediction's own noise band, but it comes from consistent declines of t1_12 and t1_22 (0/3, down from 3/3), and partial losses on t1_19 and t1_02, so it is a systematic effect on specific questions, not run-to-run scatter (the run totals within a row differ by at most 2).
5. **"Differences under about 2-3 points are noise."** Within-row run totals spread by 1 (v2b), 1 (ex-a) and 2 (ex-b), so differences of that size would be noise. The overall differences here are larger: ex-b is 4.33 below v2b and 3.00 below ex-a, so this point does not rescue ex-b; at tier level only the tier 1 and tier 2 drops vs v2b (−2.33, −2.00) sit at the band's edge.

**Net:** the shape failures that ex-a already reduced fall a little further, but the added declines cost more than they save (net −4.33 vs v2b, −3.00 vs ex-a). Retrieval did not reduce declines.
