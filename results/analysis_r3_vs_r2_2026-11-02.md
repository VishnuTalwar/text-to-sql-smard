# Row R3 (R2 + decline review and empty fact) vs R2, 2026-11-02

Sources: `results/r3_run{1,2,3}_2026-11-02.jsonl`, `results/r2_run{1,2,3}_2026-11-02.jsonl` and `results/v2b_fresh_run{1,2,3}_2026-11-02.jsonl`; prediction in `results/r3_prediction_2026-11-02.md`. Same exam (84 questions), model `gpt-4o-2024-08-06`, temperature 0, seed 0, v2b prompt on attempt 1, at most 3 attempts in total for all checks.

**Headline:** R3 scored 59.67/84 (60, 60, 59), exactly R2's mean and 0.33 below v2b_fresh. The decline review never fired (there are no false declines on this base, so it had nothing to review) and it never fired on a correct tier-0 decline. The empty fact fired on `u_08` in all 3 runs and made things no better: the model answered with a made-up `SELECT 0`. Tier 0 fell to 6.33 because `u_05` was answered with SQL in 2 of 3 runs, which the loop did not cause (attempt 1 only). The five questions whose pass count changed are run-to-run variation.

## 1. Scores (passed out of 84; tiers: t0=8, t1=35, t2=25, t3=12, t4=4)

| Row | Run | Total | T0 | T1 | T2 | T3 | T4 |
|---|---|---:|---:|---:|---:|---:|---:|
| R3 | run 1 | 60 | 6 | 35 | 16 | 3 | 0 |
| R3 | run 2 | 60 | 6 | 34 | 17 | 3 | 0 |
| R3 | run 3 | 59 | 7 | 34 | 16 | 2 | 0 |
| **R3** | **mean** | **59.67** | **6.33** | **34.33** | **16.33** | **2.67** | **0.00** |
| R2 | run 1 | 60 | 7 | 35 | 15 | 3 | 0 |
| R2 | run 2 | 59 | 7 | 34 | 16 | 2 | 0 |
| R2 | run 3 | 60 | 7 | 34 | 17 | 2 | 0 |
| **R2** | **mean** | **59.67** | **7.00** | **34.33** | **16.00** | **2.33** | **0.00** |
| v2b_fresh | run 1 | 60 | 7 | 34 | 15 | 4 | 0 |
| v2b_fresh | run 2 | 60 | 7 | 34 | 16 | 3 | 0 |
| v2b_fresh | run 3 | 60 | 7 | 34 | 15 | 4 | 0 |
| **v2b_fresh** | **mean** | **60.00** | **7.00** | **34.00** | **15.33** | **3.67** | **0.00** |

Mean total difference: R3 minus R2 +0.00; R3 minus v2b_fresh -0.33. Noise on this exam is about 2 to 4 points per run.

## 2. Loop numbers per run

| Run | Retry rate | Mean attempts | Error retries | Empty retries (rows / NULL) | Empty facts fired (ids) | Reviews fired (ids) | Declined after review | Answered after review | Cap hits |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| run 1 | 3/84 (3.6%) | 1.048 | 4 | 0 / 1 | u_08 | - | 0 | 0 | 1 |
| run 2 | 2/84 (2.4%) | 1.024 | 1 | 0 / 1 | u_08 | - | 0 | 0 | 0 |
| run 3 | 3/84 (3.6%) | 1.060 | 4 | 0 / 1 | u_08 | - | 0 | 0 | 0 |
| **all 3** | **8/252 (3.2%)** | **1.044** | **9** | **0 / 3** | **3** | **0** | **0** | **0** | **1** |

For the "all 3" row the two fact columns are counts of questions. Declined after empty: run 1: 0, run 2: 0, run 3: 0.

## 3. u_08 (How much wind did we generate in July 2026?) per run

**Run 1: FAIL**, 2 attempt(s).

- Attempt 1: SQL: SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND energietraeger IN ('Wind Onshore', 'Wind Offshore'); (result: 1 row(s), only NULL)
  - Message sent back:

    ```
    This query ran but returned only NULL values.
    Fact: the tables have no rows for the period 2026-07-01 to 2026-07-31.
    Write a corrected query. Return only the SQL.
    ```
- Attempt 2: SQL: SELECT 0 AS total_wind_generation (result: 1 row(s))

**Run 2: FAIL**, 2 attempt(s).

- Attempt 1: SQL: SELECT SUM(mwh) FROM erzeugung WHERE energietraeger IN ('Wind Onshore', 'Wind Offshore') AND zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01'; (result: 1 row(s), only NULL)
  - Message sent back:

    ```
    This query ran but returned only NULL values.
    Fact: the tables have no rows for the period 2026-07-01 to 2026-07-31.
    Write a corrected query. Return only the SQL.
    ```
- Attempt 2: SQL: SELECT 0 AS total_mwh (result: 1 row(s))

**Run 3: FAIL**, 2 attempt(s).

- Attempt 1: SQL: SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND energietraeger IN ('Wind Onshore', 'Wind Offshore'); (result: 1 row(s), only NULL)
  - Message sent back:

    ```
    This query ran but returned only NULL values.
    Fact: the tables have no rows for the period 2026-07-01 to 2026-07-31.
    Write a corrected query. Return only the SQL.
    ```
- Attempt 2: SQL: SELECT 0 AS total_wind_generation; (result: 1 row(s))

**u_08 got worse than unanswered: the model invented a zero.** In all 3 runs the empty fact ("the tables have no rows for the period 2026-07-01 to 2026-07-31") was sent after a `SUM` over July 2026 that returned only NULL, and in all 3 runs the model then replied with a constant, `SELECT 0 AS total_wind_generation` (or `SELECT 0 AS total_mwh`). It never replied `NO_QUERY`. The expected behaviour of u_01 in `gold_set_smard.yaml` states the principle: the right answer is "keine Daten" (no data), not "0". That is the trap the tier-0 questions are built around. The question still fails exactly as before (tier 0: SQL instead of a decline), but the answer the user would see changed from an empty cell to a confident 0. My reading, not tested: the message ends with "Write a corrected query. Return only the SQL.", and with the fact in place the model's way to make the query "work" is to output the zero the fact seems to imply; the message never mentions that `NO_QUERY` is allowed.

## 4. u_01 to u_07 per run (expected: always declined, never reviewed)

| id | Question | Run 1 | Run 2 | Run 3 |
|---|---|---|---|---|
| u_01 | How much nuclear power was produced in June 2025? | declined | declined | declined |
| u_02 | How much electricity did Bavaria produce last year? | declined | declined | declined |
| u_03 | What will demand be next winter? | declined | declined | declined |
| u_04 | How much CO2 did German electricity generation emit in 2025? | declined | declined | declined |
| u_05 | Which power plant produced the most electricity? | ANSWERED WITH SQL | ANSWERED WITH SQL | declined |
| u_06 | How much solar capacity is installed in Germany? | declined | declined | declined |
| u_07 | What was the average price in the DE/AT/LU zone in 2025? | declined | declined | declined |

Reviews fired on u_01 to u_07: 0 (expected 0). Declined: 19 of 21.

## 5. Every review that fired

No review fired in any of the 3 runs.

## 6. Questions whose pass count changed (R2 to R3)

| id | Tier | R2 | R3 | Change | Review/empty fact fired in R3 | Marking | Note |
|---|---:|---:|---:|---:|---|---|---|
| t2_12 | 2 | 0/3 | 2/3 | +2 | none | run-to-run variation | R3 runs 1 and 2 used `TO_CHAR(zeitpunkt, 'Day')` (the name, passes); R2 used `EXTRACT(DOW ...)` (a number) in 3/3. |
| t3_06 | 3 | 0/3 | 2/3 | +2 | none | run-to-run variation | R3 runs 1 and 2 returned one row with `CASE` sums (gold shape); R2 returned two rows in 3/3. |
| u_05 | 0 | 3/3 | 1/3 | -2 | none | run-to-run variation | R3 runs 1 and 2 answered "which power plant" with a ranking of energy sources (SQL on a tier-0 question); R2 and v2b_fresh declined 3/3. Neither run was retried and no fact was sent, so this is attempt 1 only. |
| t2_25 | 2 | 1/3 | 0/3 | -1 | none | run-to-run variation | R2 run 3 passed with an `EXTRACT(YEAR ...) = 2025` filter; R3 run 3 has that filter too but still ranks "Schweden 4" first (gold "Polen"). |
| t3_02 | 3 | 1/3 | 0/3 | -1 | none | run-to-run variation | R2 run 1 multiplied the share by 100 (gold 30.51); no R3 run did. |

5 questions changed; net +0 passes over 3 runs.

## 7. Failure groups a to g (definitions as in `results/failure_inventory_r1_v2b_2026-11-02.md`)

| Group | R3: sum (mean/run) | R2: sum (mean/run) | v2b_fresh: sum (mean/run) |
|---|---:|---:|---:|
| a. SQL crash (still crashing at the end) | 1 (0.33) | 0 (0.00) | 6 (2.00) |
| b. False decline (NO_QUERY on tier 1-4) | 0 (0.00) | 0 (0.00) | 0 (0.00) |
| c. Missed decline (SQL on tier 0) | 5 (1.67) | 3 (1.00) | 3 (1.00) |
| d. Empty result (0 rows or only NULLs), gold not empty | 0 (0.00) | 3 (1.00) | 2 (0.67) |
| e. Wrong column count | 25 (8.33) | 23 (7.67) | 22 (7.33) |
| f. Wrong row count | 13 (4.33) | 12 (4.00) | 11 (3.67) |
| g. Wrong values (same shape) | 29 (9.67) | 32 (10.67) | 28 (9.33) |
| **All failures** | **73 (24.33)** | **73 (24.33)** | **72 (24.00)** |

Question ids for R3 (runs failed that way, of 3):

- **a. SQL crash (still crashing at the end):** t4_02 (1/3)
- **b. False decline (NO_QUERY on tier 1-4):** -
- **c. Missed decline (SQL on tier 0):** u_08 (3/3), u_05 (2/3)
- **d. Empty result (0 rows or only NULLs), gold not empty:** -
- **e. Wrong column count:** t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_11 (3/3), t3_12 (3/3), t4_04 (3/3), t1_18 (2/3), t4_02 (2/3)
- **f. Wrong row count:** t2_15 (3/3), t2_21 (3/3), t4_01 (3/3), t4_03 (3/3), t3_06 (1/3)
- **g. Wrong values (same shape):** t2_07 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t2_25 (3/3), t3_02 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3), t2_09 (1/3), t2_12 (1/3)

## 8. Model and system_fingerprint seen (every attempt of every call)

| model | system_fingerprint | Calls |
|---|---|---:|
| gpt-4o-2024-08-06 | fp_625eb29508 | 173 |
| gpt-4o-2024-08-06 | fp_43dd38799b | 55 |
| gpt-4o-2024-08-06 | fp_d44a43dee5 | 33 |
| gpt-4o-2024-08-06 | fp_4c910a9acf | 2 |

All 263 calls report `gpt-4o-2024-08-06`: yes.

The fingerprints again differ from the previous set of runs: R3 saw `fp_625eb29508` (173 calls), `fp_43dd38799b` (55), `fp_d44a43dee5` (33) and `fp_4c910a9acf` (2). `fp_625eb29508` and `fp_d44a43dee5` are the values of the v2b_fresh runs; R2 had `fp_03eab4df58` and `fp_9e3f708ee1` instead; `fp_43dd38799b` is new. So the serving fingerprints change from one set of runs to the next, even with the model name pinned.

## 9. Latency, tokens, cost (per question, mean over 84 x 3)

| Row | p50 / p95 model only (s) | p50 / p95 with checks (s) | Mean model latency (s) | Prompt tokens | Completion tokens | Cost (USD) |
|---|---:|---|---:|---:|---:|---:|
| R3 | 1.289 / 2.685 | 1.360 / 2.742 | 1.474 | 659.3 | 63.0 | 0.00228 |
| R2 | 1.143 / 2.141 | 1.186 / 2.219 | 1.308 | 692.4 | 64.1 | 0.00237 |
| v2b_fresh | 0.921 / 1.370 | n/a | 0.943 | 629.3 | 59.6 | 0.00217 |

Cost = prompt tokens x $2.50 + completion tokens x $10.00 per 1M (set in the runner files; check against the current OpenAI price page). Mean time in the checks per question in R3 (SQL runs and date facts): 0.079 s.

## 10. Prediction check (`results/r3_prediction_2026-11-02.md`)

| # | Prediction | Verdict | Deciding number |
|---|---|---|---|
| 1 | Base v2b_fresh 60.00; R2 59.67; model gpt-4o-2024-08-06 (D36) | Confirmed | All 263 calls report `gpt-4o-2024-08-06`; R2 mean is 59.67. |
| 2 | Decline review fires on 0 to 1 questions per run; dry run: 0 of 111 correct tier-0 declines | Confirmed | 0 reviews in each run (0 of 252); none on a tier-0 decline. |
| 3 | u_01 to u_07 stay declined in 3 of 3 runs; the known gap is watched via u_01 | Not confirmed | `u_05` was answered with SQL in 2 of 3 runs (19 of 21 declined). The loop did not cause it: no review or fact was involved, and nothing was retried. `u_01` was declined 3/3 and no review fired on it, so the known gap did not show. |
| 4 | Empty fact fires on u_08 in 3 of 3 runs | Confirmed | 3 of 3 (periods 2026-07-01 to 2026-07-31). |
| 5 | u_08 is declined after it in at least 1 of 3 runs | Not confirmed | 0 of 3. In all 3 runs the model replied `SELECT 0 AS ...` (a made-up zero), not `NO_QUERY`. |
| 6 | t4_03 unchanged: no date in its SQL, no fact, 0 of 3 | Confirmed | 0 of 3 passes, no fact. Attempt 1 differs from R2 (`WHERE e.mwh > v.mwh` returns 80 rows, so there was no empty retry), but the verdict (wrong row count, gold 8568) is the same. |
| 7 | Total within noise of 60.00 (roughly 58 to 63); expected gain 0 to +1, all from u_08 | Partly | 59.67 (60, 60, 59) is inside the range, but the gain is -0.33 against v2b_fresh and 0.00 against R2; `u_08` brought none of it. |
| 8 | Tier 0 between 7 and 8 | Not confirmed | 6.33 (6, 6, 7), because of `u_05`. |
| 9 | No new false declines on tiers 1-4 caused by the loop | Confirmed | 0 false declines in all 3 runs. |
| 10 | The real test of the decline review is the next row (ex-a on top of R3); the dry run predicts it catches only 2 of ex-a's 35 false declines | Not tested here | Nothing about ex-a was run. |
