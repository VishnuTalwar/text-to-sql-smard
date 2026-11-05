# Row R3b (R3 + system decline for proven-empty periods) vs R3, 2026-11-05

Sources: `results/r3b_run{1,2,3}_2026-11-05.jsonl` (run today), `results/r3_run{1,2,3}_2026-11-02.jsonl`, `results/r2_run{1,2,3}_2026-11-02.jsonl` and `results/v2b_fresh_run{1,2,3}_2026-11-02.jsonl`; prediction in `results/r3b_prediction_2026-11-02.md`. Same exam (84 questions), model `gpt-4o-2024-08-06`, temperature 0, seed 0, v2b prompt on attempt 1, at most 3 attempts in total for all checks. Held-out files were not opened.

**Headline:** R3b scored 61.67/84 (62, 61, 62), the highest mean in the progress table: +2.00 against R3, +1.67 against v2b_fresh (60.00). Of the +2.00 over R3, **+1.00 is caused by the loop**: the system decline fired on `u_08` in 3 of 3 runs, with no second model call and no made-up zero, and `u_08` passed 3/3 (0/3 in R3, R2 and v2b_fresh). The other +1.00 is run-to-run variation on four questions with no loop activity (`u_05` +2, `t2_09` +1, `t2_12` +1, `t1_18` -1; attempt 1 only). The system decline fired on no question in tiers 1 to 4. One thing the prediction did not expect: the decline review fired once (`t1_12`, run 2) and fixed a false decline. Failures fell from 73 to 67 over 3 runs (groups a and c to zero). With noise of 2 to 4 points per run, the 3-run mean is a good sign but `u_08` is the only part of the gain that can be pinned on the loop.

## 1. Scores (passed out of 84; tiers: t0=8, t1=35, t2=25, t3=12, t4=4)

| Row | Run | Total | T0 | T1 | T2 | T3 | T4 |
|---|---|---:|---:|---:|---:|---:|---:|
| R3b | run 1 | 62 | 8 | 34 | 17 | 3 | 0 |
| R3b | run 2 | 61 | 8 | 34 | 17 | 2 | 0 |
| R3b | run 3 | 62 | 8 | 34 | 17 | 3 | 0 |
| **R3b** | **mean** | **61.67** | **8.00** | **34.00** | **17.00** | **2.67** | **0.00** |
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

Mean total difference: R3b minus R3 +2.00; R3b minus R2 +2.00; R3b minus v2b_fresh +1.67. Tier 0 is 8/8 in all three runs.

## 2. Loop numbers per run (R3b)

| Run | Retry rate | Mean attempts | Error retries | Empty checks fired (rows / NULL) | System declines (ids) | Reviews fired (ids) | Cap hits |
|---|---:|---:|---:|---:|---|---|---:|
| run 1 | 3/84 (3.6%) | 1.071 | 4 | 3 / 1 | u_08 | - | 1 (t4_03) |
| run 2 | 2/84 (2.4%) | 1.024 | 1 | 0 / 1 | u_08 | t1_12 | 0 |
| run 3 | 3/84 (3.6%) | 1.060 | 3 | 3 / 1 | u_08 | - | 1 (t4_03) |
| **all 3** | **8/252 (3.2%)** | **1.052** | **8** | **6 / 3** | **3** | **1** | **2** |

R3 for comparison: retry rate 8/252 (3.2%), mean attempts 1.044, 9 error retries, 3 empty checks (all `u_08`, NULL), 0 reviews, 1 cap hit.

- "Error retries" and "empty checks fired" count attempts whose check fired (including the last attempt, where the cap stops further retries). Error retries: `t4_02` (runs 1 and 3, 2 each), `t4_04` (run 1: 2, runs 2 and 3: 1 each); all end with SQL that runs (no crash at the end in any run). Retried questions: run 1 t4_02, t4_03, t4_04; run 2 t1_12 (review), t4_04; run 3 t4_02, t4_03, t4_04.
- The 6 empty-rows checks are all `t4_03` (runs 1 and 3, 3 attempts each, 0 rows each time; no period in its SQL, so no system decline, as predicted). In run 2 `t4_03` returned rows on attempt 1 (wrong row count, no retry).
- The 3 empty-NULL checks are all `u_08`; each ended in a system decline on attempt 1, so no retry message was sent for it.
- Decline review: fired once, `t1_12` run 2: the model replied `NO_QUERY: Data for February 2026 is not available.`; the database has rows for 2026-02-01 to 2026-02-28 (erzeugung 32256, verbrauch 10752, preise 45696); the question went back with that fact, and attempt 2 answered with the right SQL (`SUM(mwh)` for Erdgas, February 2026) and passed. Declined again after review: 0. Answered after review: 1 (pass).

## 3. u_01 to u_08 per run

| id | Question | Run 1 | Run 2 | Run 3 | R3 (runs 1, 2, 3) |
|---|---|---|---|---|---|
| u_01 | How much nuclear power was produced in June 2025? | declined | declined | declined | declined, declined, declined |
| u_02 | How much electricity did Bavaria produce last year? | declined | declined | declined | declined, declined, declined |
| u_03 | What will demand be next winter? | declined | declined | declined | declined, declined, declined |
| u_04 | How much CO2 did German electricity generation emit in 2025? | declined | declined | declined | declined, declined, declined |
| u_05 | Which power plant produced the most electricity? | declined | declined | declined | ANSWERED WITH SQL, ANSWERED WITH SQL, declined |
| u_06 | How much solar capacity is installed in Germany? | declined | declined | declined | declined, declined, declined |
| u_07 | What was the average price in the DE/AT/LU zone in 2025? | declined | declined | declined | declined, declined, declined |
| u_08 | How much wind did we generate in July 2026? | declined (system) | declined (system) | declined (system) | ANSWERED WITH SQL x3 (`SELECT 0 ...`) |

Declined: 24 of 24 (u_01 to u_08 x 3 runs); u_01 to u_07 by the model (21 of 21), u_08 by the system (3 of 3). No review fired on any of u_01 to u_07.

**u_08 ended in a system decline in all 3 runs.** Each run had exactly one attempt (no second model call); the final reply is `NO_QUERY: No data: the tables have no rows for the period 2026-07-01 to 2026-07-31.` (period rows erzeugung/verbrauch/preise = 0/0/0).

| Run | Attempt 1 SQL | Result |
|---|---|---|
| 1 | `SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND energietraeger IN ('Wind Onshore', 'Wind Offshore');` | 1 row, only NULL, then system decline |
| 2 | same SQL as run 1 | 1 row, only NULL, then system decline |
| 3 | `SELECT SUM(mwh) FROM erzeugung WHERE energietraeger IN ('Wind Onshore', 'Wind Offshore') AND zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01';` | 1 row, only NULL, then system decline |

## 4. Every system decline

| Run | id | Tier | Triggering SQL | Period (rows erzeugung/verbrauch/preise) | Passed |
|---|---|---:|---|---|---|
| 1 | u_08 | 0 | `SELECT SUM(mwh) AS total_wind_generation FROM erzeugung WHERE zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01' AND energietraeger IN ('Wind Onshore', 'Wind Offshore');` | 2026-07-01 to 2026-07-31 (0/0/0) | yes |
| 2 | u_08 | 0 | same as run 1 | 2026-07-01 to 2026-07-31 (0/0/0) | yes |
| 3 | u_08 | 0 | `SELECT SUM(mwh) FROM erzeugung WHERE energietraeger IN ('Wind Onshore', 'Wind Offshore') AND zeitpunkt >= '2026-07-01' AND zeitpunkt < '2026-08-01';` | 2026-07-01 to 2026-07-31 (0/0/0) | yes |

**System declines on tiers 1 to 4: 0** (expected none). No made-up constant query (`SELECT 0` or any SQL without `FROM`) appears in any attempt of any question.

## 5. Questions whose pass count changed R3 -> R3b

| id | Tier | R3 | R3b | Change | Loop activity | Marking | Note |
|---|---:|---:|---:|---:|---|---|---|
| u_08 | 0 | 0/3 | 3/3 | +3 | R3b: system decline in runs 1, 2, 3. R3: empty fact, then `SELECT 0` | **caused by the loop** | The system decline replaces the empty fact; no second model call. |
| u_05 | 0 | 1/3 | 3/3 | +2 | none in either row | run-to-run variation | R3b declined 3/3 (`NO_QUERY: The table does not contain information about specific power plants.`); R3 runs 1 and 2 answered with a ranking of energy sources. Attempt 1 only. |
| t2_09 | 2 | 2/3 | 3/3 | +1 | none | run-to-run variation | R3 run 1 used `TO_CHAR(zeitpunkt, 'YYYY-MM')` (text, gold is a date); R3b used `DATE_TRUNC('month', ...)` 3/3. |
| t2_12 | 2 | 2/3 | 3/3 | +1 | none | run-to-run variation | R3 run 3 used `EXTRACT(DOW ...)` (a number); R3b used `TO_CHAR(zeitpunkt, 'Day')` 3/3. |
| t1_18 | 1 | 1/3 | 0/3 | -1 | none | run-to-run variation | R3 run 1 returned `SELECT MAX(mwh)` (gold shape); R3b returned `SELECT zeitpunkt, mwh ... LIMIT 1` (2 columns) 3/3, as R3 runs 2 and 3 did. |

5 questions changed; net +6 passes over 3 runs (+2.00 a run). Loop-caused: +3 (+1.00 a run). Variation: +3 (+1.00 a run).

Not in the table because the pass count did not change: `t1_12` run 2, where the decline review fired (a false decline) and the retry passed. R3 had 3/3 on `t1_12` without any decline, so the review's effect on the score here is that it avoided a loss in that run, not that it added a point.

Attempt-1 replies differ between R3 and R3b in 111 of 252 question-runs (141 identical), even at temperature 0 and seed 0; the serving fingerprints changed again (section 7). This is the run-to-run variation behind the four "variation" lines.

## 6. Failure groups a to g (definitions as in `results/failure_inventory_r1_v2b_2026-11-02.md`; first fit in the order a to g)

| Group | R3b: sum (mean/run) | R3: sum (mean/run) | v2b_fresh: sum (mean/run) |
|---|---:|---:|---:|
| a. SQL crash (still crashing at the end) | 0 (0.00) | 1 (0.33) | 6 (2.00) |
| b. False decline (NO_QUERY on tier 1-4) | 0 (0.00) | 0 (0.00) | 0 (0.00) |
| c. Missed decline (SQL on tier 0) | 0 (0.00) | 5 (1.67) | 3 (1.00) |
| d. Empty result (0 rows or only NULLs), gold not empty | 2 (0.67) | 0 (0.00) | 2 (0.67) |
| e. Wrong column count | 26 (8.67) | 25 (8.33) | 22 (7.33) |
| f. Wrong row count | 12 (4.00) | 13 (4.33) | 11 (3.67) |
| g. Wrong values (same shape) | 27 (9.00) | 29 (9.67) | 28 (9.33) |
| **All failures** | **67 (22.33)** | **73 (24.33)** | **72 (24.00)** |

Question ids for R3b (runs failed that way, of 3):

- **a. SQL crash (still crashing at the end):** -
- **b. False decline (NO_QUERY on tier 1-4):** -
- **c. Missed decline (SQL on tier 0):** -
- **d. Empty result (0 rows or only NULLs), gold not empty:** t4_03 (2/3)
- **e. Wrong column count:** t1_18 (3/3), t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_12 (3/3), t4_02 (3/3), t4_04 (3/3), t3_11 (2/3)
- **f. Wrong row count:** t2_15 (3/3), t2_21 (3/3), t4_01 (3/3), t3_06 (1/3), t4_03 (1/3), t3_11 (1/3)
- **g. Wrong values (same shape):** t2_07 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t2_25 (3/3), t3_02 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3)

Groups a, b and c are empty; every remaining failure is a shape or value error (e, f, g: 65 of 67) or the empty `t4_03` query (d). Groups d to g are the work for the next rows, not for this loop.

## 7. Model and system_fingerprint seen (every attempt of every call)

| model | system_fingerprint | Calls |
|---|---|---:|
| gpt-4o-2024-08-06 | fp_7c2c459cd0 | 210 |
| gpt-4o-2024-08-06 | fp_e665f1271d | 55 |

All 265 calls report `gpt-4o-2024-08-06`: yes. Both fingerprints are new (neither appears in R3 or v2b_fresh): R3 saw `fp_625eb29508` (173), `fp_43dd38799b` (55), `fp_d44a43dee5` (33), `fp_4c910a9acf` (2); v2b_fresh saw `fp_625eb29508` (163), `fp_e85bcce457` (51), `fp_d44a43dee5` (33), `fp_4c910a9acf` (5). Part of the +1.00 variation may come from the serving change, which cannot be separated from sampling noise here.

## 8. Latency, tokens, cost (per question, mean over 84 x 3)

| Row | p50 / p95 model only (s) | p50 / p95 with checks (s) | Mean model latency (s) | Prompt tokens | Completion tokens | Cost (USD) |
|---|---:|---|---:|---:|---:|---:|
| R3b | 1.216 / 2.465 | 1.276 / 2.545 | 1.403 | 677.2 | 64.4 | 0.00234 |
| R3 | 1.289 / 2.685 | 1.360 / 2.742 | 1.474 | 659.3 | 63.0 | 0.00228 |
| v2b_fresh | 0.921 / 1.370 | n/a | 0.943 | 629.3 | 59.6 | 0.00217 |

Cost = prompt tokens x $2.50 + completion tokens x $10.00 per 1M (set in the runner files; not checked against the current OpenAI price page). Mean time in the checks per question in R3b: 0.071 s (R3: 0.079 s). Total API cost of the 3 R3b runs: $0.5889. R3b costs about 8% more than v2b_fresh per question; the retries on `t4_02`, `t4_03` and `t4_04` explain part of the extra prompt tokens (677 vs 629), not necessarily all. The latency gap to v2b_fresh (p50 +0.30 s) is mostly on the API side: it is present in R2 and R3 too, and the loop's own check time is 0.07 s. The system decline saves a model call on `u_08` (1 call instead of 2 in R3).

## 9. Prediction check (`results/r3b_prediction_2026-11-02.md`)

| # | Prediction | Verdict | Deciding number |
|---|---|---|---|
| 1 | Base v2b_fresh 60.00; R3 59.67. Model gpt-4o-2024-08-06 | Confirmed | All 265 calls report `gpt-4o-2024-08-06`; the base means are 60.00 and 59.67. |
| 2 | System decline fires on u_08 in every run where its SQL returns an empty result for July 2026 (3 of 3), so u_08 passes in those runs | Confirmed | Fired in 3 of 3 runs (period 2026-07-01 to 2026-07-31, 0/0/0 rows); u_08 passed 3/3. |
| 3 | It fires on no tier 1-4 question (the dry run shows only u_08) | Confirmed | 0 system declines on tiers 1 to 4; 3 of 3 on u_08. |
| 4 | Tier 0 between 7 and 8, depending on u_05's attempt 1 | Confirmed | 8.00 (8, 8, 8); u_05 declined 3/3. |
| 5 | Total within noise of 60.00; expected gain about +1 (u_08) | Partly | Total 61.67 (62, 61, 62) is inside the noise range and the gain from `u_08` is exactly +1.00, but the total is +1.67 above 60.00: +1.00 from variation on `u_05`, `t2_09`, `t2_12`, `t1_18` (net +3 passes over 3 runs against R3; with `u_05` +2 the largest part). |
| 6 | No made-up constants for u_08 (no SELECT 0) | Confirmed | 0 attempts without `FROM` in the 265 calls; `u_08` has 1 attempt in each run and no second model call. |
| 7 | Decline review: still expected to fire on 0 questions on this base | Not confirmed | Fired once (0 of 252 in R3, 1 of 252 here: `t1_12`, run 2, "Data for February 2026 is not available" while the tables hold 32256 + 10752 + 45696 rows for February 2026). It sent the fact back and attempt 2 passed, so the review worked as designed, and it did not fire on any tier-0 decline (0 of 21 u_01 to u_07 declines). |

Beyond the prediction: failures dropped from 73 to 67 over 3 runs, with groups a and c at 0, and the retry rate (3.2%) and mean attempts (1.052) are unchanged from R3 within a few attempts.

## Notes for the next step

- `t4_03` is the only question where an empty result is still returned: 0 rows in runs 1 and 3 after 3 attempts (cap hit twice). The SQL has no condition on `zeitpunkt`, so the date fact check cannot help it; its three attempts all join `erzeugung` to `verbrauch` and return 0 rows (my reading, not tested: a join or filter problem, not a decline problem).
- The only part of this row that can be pinned on the loop is `u_08` (+1.00) and one rescued false decline on `t1_12` (run 2). The rest of the gain over R3 is within the 2 to 4 point run-to-run noise noted in section 1 of the progress file.
