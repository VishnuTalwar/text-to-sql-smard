# Row R2 (error retry + empty-result retry) vs v2b_fresh, 2026-11-02

Sources: `results/r2_run{1,2,3}_2026-11-02.jsonl` (model pinned to `gpt-4o-2024-08-06`, D36), `results/v2b_fresh_run{1,2,3}_2026-11-02.jsonl` and `results/r1_run{1,2,3}_2026-11-02.jsonl`; prediction in `results/r2_prediction_2026-11-02.md`. Same exam (84 questions), temperature 0, seed 0, v2b prompt on attempt 1, at most 3 attempts in total for both checks.

**Headline:** the empty-result retry changed nothing. Mean 59.67/84 (60, 59, 60) against v2b_fresh 60.00, a difference of -0.33 (noise). It fired on exactly the two target questions in every run, `u_08` and `t4_03`, and fixed neither: `u_08` was never declined (0 of 3) and `t4_03` returned 0 rows on all 9 attempts. The retry rate is 4.0% (10 of 252), the cost per question is 9% higher ($0.00237 vs $0.00217), and no tier 1-4 question was falsely declined. All six questions whose pass count changed were never retried, so those changes are run-to-run variation.

## 1. Scores (passed out of 84; tiers: t0=8, t1=35, t2=25, t3=12, t4=4)

| Row | Run | Total | T0 | T1 | T2 | T3 | T4 |
|---|---|---:|---:|---:|---:|---:|---:|
| R2 | run 1 | 60 | 7 | 35 | 15 | 3 | 0 |
| R2 | run 2 | 59 | 7 | 34 | 16 | 2 | 0 |
| R2 | run 3 | 60 | 7 | 34 | 17 | 2 | 0 |
| **R2** | **mean** | **59.67** | **7.00** | **34.33** | **16.00** | **2.33** | **0.00** |
| v2b_fresh | run 1 | 60 | 7 | 34 | 15 | 4 | 0 |
| v2b_fresh | run 2 | 60 | 7 | 34 | 16 | 3 | 0 |
| v2b_fresh | run 3 | 60 | 7 | 34 | 15 | 4 | 0 |
| **v2b_fresh** | **mean** | **60.00** | **7.00** | **34.00** | **15.33** | **3.67** | **0.00** |
| R1 | run 1 | 58 | 7 | 33 | 15 | 3 | 0 |
| R1 | run 2 | 59 | 7 | 34 | 16 | 2 | 0 |
| R1 | run 3 | 61 | 7 | 34 | 17 | 3 | 0 |
| **R1** | **mean** | **59.33** | **7.00** | **33.67** | **16.00** | **2.67** | **0.00** |

Mean total difference: R2 minus v2b_fresh -0.33; R2 minus R1 +0.33. Noise on this exam is about 2 to 4 points per run.

## 2. Loop numbers per run

| Run | Retry rate | Mean attempts | Error retries | Empty retries (rows / NULL) | Empty on attempt 1 | Fixed after empty (pass) | Declined after empty | Declined after error | Cap hits | Ended empty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| run 1 | 3/84 (3.6%) | 1.060 | 1 | 3 / 3 | 2 | 0 | 0 | 0 | 2 | 2 |
| run 2 | 4/84 (4.8%) | 1.083 | 3 | 3 / 3 | 2 | 0 | 0 | 0 | 2 | 2 |
| run 3 | 3/84 (3.6%) | 1.060 | 1 | 3 / 3 | 2 | 0 | 0 | 0 | 2 | 2 |
| **all 3** | **10/252 (4.0%)** | **1.067** | **5** | **9 / 9** | **6** | **0** | **0** | **0** | **6** | **6** |

"Error retries" and "empty retries" count the checks that fired (an attempt asking for another attempt, or the last attempt still failing/empty). "Fixed after empty" = a question that had an empty retry and passes in the end. Crashed on attempt 1 per run: run 1: ['t4_04']; run 2: ['t4_02', 't4_04']; run 3: ['t4_04'].

## 3. u_08 (How much wind did we generate in July 2026?) per run

| Run | Attempt 1 (SQL -> result) | Retry message sent | Later attempts | Final verdict |
|---|---|---|---|---|
| run 1 | SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026- -> 1 row(s), only NULL | This query ran but returned only NULL values. / Write a corrected query. Return only the SQL. | attempt 2: SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND -> 1 row(s), only NULL; attempt 3: SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND -> 1 row(s), only NULL | FAIL |
| run 2 | SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026- -> 1 row(s), only NULL | This query ran but returned only NULL values. / Write a corrected query. Return only the SQL. | attempt 2: SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND -> 1 row(s), only NULL; attempt 3: SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND -> 1 row(s), only NULL | FAIL |
| run 3 | SELECT SUM(mwh) FROM erzeugung WHERE energietraeger IN ('Wind Onshore', 'Wind Offshore') AND zeitpunkt >= '202 -> 1 row(s), only NULL | This query ran but returned only NULL values. / Write a corrected query. Return only the SQL. | attempt 2: SELECT SUM(mwh) FROM erzeugung WHERE energietraeger IN ('Wind Onshore', 'Wind Offshore') AND zeitpunkt >= '2026-07-01' A -> 1 row(s), only NULL; attempt 3: SELECT SUM(mwh) FROM erzeugung WHERE energietraeger IN ('Wind Onshore', 'Wind Offshore') AND zeitpunkt >= '2026-07-01' A -> 1 row(s), only NULL | FAIL |

u_08 declined after the empty retry in 0 of 3 runs.

In all 3 runs the model answered attempt 1 with a `SUM(mwh)` over July 2026 (one row, NULL), got the "only NULL values" message, tried the same query with `AND mwh IS NOT NULL` (still NULL), and then went back to the attempt-1 query. It never replied `NO_QUERY`. My reading, not tested: the retry text says "Write a corrected query. Return only the SQL." and does not mention that a decline is possible, so the model keeps writing SQL.

## 4. Every other question with an empty retry

### Run 1, t4_03 (tier 4): Which hours had more generation than consumption?

Attempt 1 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY hour
HAVING SUM(e.mwh) > SUM(v.mwh);
```
Attempt 2 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY hour
HAVING SUM(e.mwh) > SUM(v.mwh)
ORDER BY hour;
```
Attempt 3 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY DATE_TRUNC('hour', e.zeitpunkt)
HAVING SUM(e.mwh) > SUM(v.mwh)
ORDER BY hour;
```
**Final: FAIL**, SQL runs, wrong row count (gold=8568 agent=0).

### Run 2, t4_03 (tier 4): Which hours had more generation than consumption?

Attempt 1 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt
GROUP BY hour
HAVING SUM(e.mwh) > SUM(v.mwh)
```
Attempt 2 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY hour
HAVING SUM(e.mwh) > SUM(v.mwh)
```
Attempt 3 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY hour
HAVING SUM(e.mwh) > SUM(CASE WHEN v.metrik = 'grid load' THEN v.mwh ELSE 0 END)
```
**Final: FAIL**, SQL runs, wrong row count (gold=8568 agent=0).

### Run 3, t4_03 (tier 4): Which hours had more generation than consumption?

Attempt 1 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY hour
HAVING SUM(e.mwh) > SUM(v.mwh);
```
Attempt 2 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY hour
HAVING SUM(e.mwh) > SUM(v.mwh)
ORDER BY hour;
```
Attempt 3 -> 0 row(s) [check fired: empty_rows]:
```sql
SELECT DISTINCT DATE_TRUNC('hour', e.zeitpunkt) AS hour
FROM erzeugung e
JOIN verbrauch v ON e.zeitpunkt = v.zeitpunkt AND v.metrik = 'grid load'
GROUP BY DATE_TRUNC('hour', e.zeitpunkt)
HAVING SUM(e.mwh) > SUM(v.mwh)
ORDER BY hour;
```
**Final: FAIL**, SQL runs, wrong row count (gold=8568 agent=0).

What the retry did in these cases: attempts 2 and 3 only changed the form of the query, not its logic (an added `ORDER BY`, the `GROUP BY` written as an expression, a `CASE` inside `HAVING`). In all 9 attempts over the 3 runs `t4_03` returned 0 rows, so the "no rows" message never led to a query that returns rows. My reading, not tested: the join of `erzeugung` to `verbrauch` repeats each consumption value once per energy source, so `SUM(v.mwh)` is always larger than the generation and the `HAVING` never holds; the retry text does not say what is wrong, so the model cannot find it.


## 5. Questions whose pass count changed (v2b_fresh to R2)

| id | Tier | v2b_fresh | R2 | Change | Retried in R2 | Marking | Note |
|---|---:|---:|---:|---:|---|---|---|
| t3_06 | 3 | 3/3 | 0/3 | -3 | none | run-to-run variation (attempt 1 only) | R2 returned two rows (`UNION ALL` or `GROUP BY year`) in 3/3 runs where v2b_fresh returned the one-row `CASE` form 3/3; old v2b (27 Oct) also had the two-row form. |
| t2_01 | 2 | 1/3 | 3/3 | +2 | none | run-to-run variation (attempt 1 only) | R2 kept the `SUM(mwh)` column in 3/3 runs; v2b_fresh dropped it in 2 of 3. |
| t1_18 | 1 | 0/3 | 1/3 | +1 | none | run-to-run variation (attempt 1 only) | R2 run 1 used `SELECT MAX(mwh)` (1 column, gold shape); the five other runs return `zeitpunkt, mwh` (2 columns). |
| t2_09 | 2 | 3/3 | 2/3 | -1 | none | run-to-run variation (attempt 1 only) | R2 run 1 used `TO_CHAR(zeitpunkt, 'YYYY-MM')` (text) instead of `DATE_TRUNC` (date). |
| t2_25 | 2 | 0/3 | 1/3 | +1 | none | run-to-run variation (attempt 1 only) | R2 run 3 added the filter `EXTRACT(YEAR FROM zeitpunkt) = 2025` and passes; the other five runs rank over all years. |
| t3_02 | 3 | 2/3 | 1/3 | -1 | none | run-to-run variation (attempt 1 only) | v2b_fresh runs 1 and 3 multiplied the share by 100 (gold 30.51); R2 did so only in run 1. |

6 questions changed; net -1 passes over 3 runs.

## 6. Failure groups a to g (definitions as in `results/failure_inventory_r1_v2b_2026-11-02.md`)

| Group | R2: sum (mean/run) | v2b_fresh: sum (mean/run) |
|---|---:|---:|
| a. SQL crash (still crashing at the end) | 0 (0.00) | 6 (2.00) |
| b. False decline (NO_QUERY on tier 1-4) | 0 (0.00) | 0 (0.00) |
| c. Missed decline (SQL on tier 0) | 3 (1.00) | 3 (1.00) |
| d. Empty result (0 rows or only NULLs), gold not empty | 3 (1.00) | 2 (0.67) |
| e. Wrong column count | 23 (7.67) | 22 (7.33) |
| f. Wrong row count | 12 (4.00) | 11 (3.67) |
| g. Wrong values (same shape) | 32 (10.67) | 28 (9.33) |
| **All failures** | **73 (24.33)** | **72 (24.00)** |

Question ids for R2 (runs failed that way, of 3):

- **a. SQL crash (still crashing at the end):** -
- **b. False decline (NO_QUERY on tier 1-4):** -
- **c. Missed decline (SQL on tier 0):** u_08 (3/3)
- **d. Empty result (0 rows or only NULLs), gold not empty:** t4_03 (3/3)
- **e. Wrong column count:** t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_11 (3/3), t4_02 (3/3), t4_04 (3/3), t1_18 (2/3)
- **f. Wrong row count:** t2_15 (3/3), t2_21 (3/3), t3_06 (3/3), t4_01 (3/3)
- **g. Wrong values (same shape):** t2_07 (3/3), t2_12 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3), t3_12 (3/3), t2_25 (2/3), t3_02 (2/3), t2_09 (1/3)

## 7. Model and system_fingerprint seen (every attempt of every call)

| model | API calls (all attempts, 3 runs) |
|---|---:|
| gpt-4o-2024-08-06 | 269 |

| model | system_fingerprint | Calls |
|---|---|---:|
| gpt-4o-2024-08-06 | fp_03eab4df58 | 177 |
| gpt-4o-2024-08-06 | fp_e85bcce457 | 55 |
| gpt-4o-2024-08-06 | fp_9e3f708ee1 | 33 |
| gpt-4o-2024-08-06 | fp_4c910a9acf | 4 |

All 269 calls report `gpt-4o-2024-08-06`: yes.

**The fingerprints differ from the v2b_fresh runs earlier on the same day.** v2b_fresh saw `fp_625eb29508` (163 calls), `fp_e85bcce457` (51), `fp_d44a43dee5` (33) and `fp_4c910a9acf` (5); R2 saw `fp_03eab4df58` (177), `fp_e85bcce457` (55), `fp_9e3f708ee1` (33) and `fp_4c910a9acf` (4). Per question: 56 questions moved from `fp_625eb29508` to `fp_03eab4df58`, 11 from `fp_d44a43dee5` to `fp_9e3f708ee1`, and 17 kept `fp_e85bcce457`. The model name is the same, so the pin (D36) did not change the model; the fingerprints changed between the two sets of runs. Reply agreement between R2 attempt 1 and v2b_fresh, same code and prompt: 61.2% for the 67 questions whose fingerprint changed (fresh within-row: 72.1%), 79.1% for the 17 whose fingerprint did not (fresh within-row: 80.4%). That fits the idea that the serving configuration changes the replies, but it is 17 questions against 67 and the two groups are not comparable in difficulty, so it is a pointer, not a result. Overall, R2 attempt 1 agrees with v2b_fresh in 54.4 of 84 questions (64.8%), with R1 in 56.4 (67.1%) and with old v2b in 51.9 (61.8%); R2 within-row: 52, 57 and 60 of 84.

## 8. Latency, tokens, cost (per question, mean over 84 x 3)

| Row | p50 / p95 model only (s) | p50 / p95 with SQL checks (s) | Mean model latency (s) | Prompt tokens | Completion tokens | Cost (USD) |
|---|---:|---|---:|---:|---:|---:|
| R2 | 1.143 / 2.141 | 1.186 / 2.219 | 1.308 | 692.4 | 64.1 | 0.00237 |
| v2b_fresh | 0.921 / 1.370 | n/a | 0.943 | 629.3 | 59.6 | 0.00217 |

Cost = prompt tokens x $2.50 + completion tokens x $10.00 per 1M (set in `run_r1.py`/`run_r2.py`; check against the current OpenAI price page). Mean SQL-check time per question in R2: 0.065 s.

## 9. Prediction check (`results/r2_prediction_2026-11-02.md`)

| # | Prediction | Verdict | Deciding number |
|---|---|---|---|
| 1 | Base v2b_fresh 60.00; model pinned to gpt-4o-2024-08-06 (D36) | Confirmed | All 269 calls (all attempts) report `gpt-4o-2024-08-06`. The system fingerprints are not the same as in the v2b_fresh runs (2 of 4 values changed). |
| 2 | No gold query is empty, so the empty retry cannot break a correct answer | Confirmed | Empty retries fired only on `u_08` and `t4_03`, which fail anyway; 0 passes were lost to an empty retry. |
| 3 | Targets: `t4_03` (empty in 2/3 v2b and 3/3 R1 runs) and `u_08` (single NULL in 6/6 runs) | Confirmed | Empty on attempt 1: exactly `u_08` and `t4_03` in all 3 runs (2 per run, 6 in total); `u_08` returned a single NULL and `t4_03` 0 rows each time. |
| 4 | `u_08` declined after the empty retry in at least 2 of 3 runs | Not confirmed | 0 of 3. The model rewrote the query (added `IS NOT NULL`), then returned to the original, and never replied `NO_QUERY`. |
| 5 | `t4_03`: SQL returns rows after the retry, but passes in at most 1 of 3 runs | Partly | Passes 0 of 3 (within "at most 1"), but the SQL never returned rows: 0 rows on all 9 attempts. |
| 6 | Empty retries fire on 1 to 3 questions per run; other questions are not affected by the loop | Confirmed | 2 questions per run (`u_08`, `t4_03`). The only other retries were error retries on `t4_02` and `t4_04` (1, 2 and 1 questions per run); every other question had 1 attempt. |
| 7 | Total within noise of 60.00 (roughly 58 to 63); expected gain about +1 (`u_08`) | Partly | Total 59.67 (60, 59, 60), inside the range; but the gain is -0.33, not +1, since `u_08` was not declined. |
| 8 | Tier 0 rises from 7 to 8 if `u_08` is declined; `u_01` to `u_07` stay declined | Partly | `u_01` to `u_07` declined in all 3 runs (confirmed). Tier 0 stays at 7.00 because `u_08` was not declined (the condition did not occur). |
| 9 | No new false declines on tiers 1-4 caused by the loop (declined_after_empty on tiers 1-4: 0) | Confirmed | 0 false declines in all 3 runs; `declined_after_empty` is 0 overall. |
