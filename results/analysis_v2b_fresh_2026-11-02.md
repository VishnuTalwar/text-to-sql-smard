# Row v2b_fresh (v2b re-run with model logging) vs old v2b, 2026-11-02

Sources: `results/v2b_fresh_run{1,2,3}_2026-11-02.jsonl` (new, with `model` and `system_fingerprint`) and `results/v2b_t0_run{1,2,3}_2026-10-27.jsonl`. Same code and prompt as old v2b (`run_v2b.py --runs 3 --tag fresh`; model string "gpt-4o", temperature 0, seed 0 unchanged; mean prompt tokens 629.3 in both).

**Headline:** mean 60.00/84 (60, 60, 60) against 60.67 (60, 61, 61): the same score within noise. The logs show one model snapshot, `gpt-4o-2024-08-06`, with four system fingerprints. Replies still differ between runs (74% identical within a row) and more between 27 October and 2 November (61 to 63%), but the record cannot say why because the old rows logged no model information.

## 1. Scores (passed out of 84; tiers: t0=8, t1=35, t2=25, t3=12, t4=4)

| Row | Run | Total | T0 | T1 | T2 | T3 | T4 |
|---|---|---:|---:|---:|---:|---:|---:|
| v2b_fresh (2 Nov) | run 1 | 60 | 7 | 34 | 15 | 4 | 0 |
| v2b_fresh (2 Nov) | run 2 | 60 | 7 | 34 | 16 | 3 | 0 |
| v2b_fresh (2 Nov) | run 3 | 60 | 7 | 34 | 15 | 4 | 0 |
| **v2b_fresh (2 Nov)** | **mean** | **60.00** | **7.00** | **34.00** | **15.33** | **3.67** | **0.00** |
| v2b old (27 Oct) | run 1 | 60 | 7 | 34 | 17 | 2 | 0 |
| v2b old (27 Oct) | run 2 | 61 | 7 | 34 | 18 | 2 | 0 |
| v2b old (27 Oct) | run 3 | 61 | 7 | 34 | 18 | 2 | 0 |
| **v2b old (27 Oct)** | **mean** | **60.67** | **7.00** | **34.00** | **17.67** | **2.00** | **0.00** |

Mean total difference fresh minus old: -0.67.

## 2. Model version seen per call (new logging; old v2b has none)

| Run | model | system_fingerprint | Calls |
|---|---|---|---:|
| run 1 | gpt-4o-2024-08-06 | fp_625eb29508 | 56 |
| run 1 | gpt-4o-2024-08-06 | fp_e85bcce457 | 17 |
| run 1 | gpt-4o-2024-08-06 | fp_d44a43dee5 | 11 |
| run 2 | gpt-4o-2024-08-06 | fp_625eb29508 | 54 |
| run 2 | gpt-4o-2024-08-06 | fp_e85bcce457 | 17 |
| run 2 | gpt-4o-2024-08-06 | fp_d44a43dee5 | 11 |
| run 2 | gpt-4o-2024-08-06 | fp_4c910a9acf | 2 |
| run 3 | gpt-4o-2024-08-06 | fp_625eb29508 | 53 |
| run 3 | gpt-4o-2024-08-06 | fp_e85bcce457 | 17 |
| run 3 | gpt-4o-2024-08-06 | fp_d44a43dee5 | 11 |
| run 3 | gpt-4o-2024-08-06 | fp_4c910a9acf | 3 |
| **all 3** | **gpt-4o-2024-08-06** | **fp_625eb29508** | **163** |
| **all 3** | **gpt-4o-2024-08-06** | **fp_e85bcce457** | **51** |
| **all 3** | **gpt-4o-2024-08-06** | **fp_d44a43dee5** | **33** |
| **all 3** | **gpt-4o-2024-08-06** | **fp_4c910a9acf** | **5** |

Every call in all 3 runs reports the same model snapshot, `gpt-4o-2024-08-06` (the `"gpt-4o"` alias resolves to it). The fingerprint is not constant: 4 values over 252 calls. It is tied to the question rather than to the run: 79 of 84 questions got the same fingerprint in all 3 runs (the rest are the 5 calls of `fp_4c910a9acf`, seen only in runs 2 and 3). It does not explain the non-determinism: when two runs had the same fingerprint for a question the replies were identical in 180 of 242 cases (74%); with different fingerprints in 6 of 10 (too few to say anything). Old v2b has no fingerprints, so nothing can be compared across the two dates.

## 3. Agreement of reply text (fences and whitespace ignored), out of 84 questions per pair

| Comparison | Pair | Identical replies | Share |
|---|---|---:|---:|
| (a) fresh vs fresh | run 1 vs run 2 | 64 | 76.2% |
| (a) fresh vs fresh | run 1 vs run 3 | 60 | 71.4% |
| (a) fresh vs fresh | run 2 vs run 3 | 62 | 73.8% |
| **(a) fresh within-row** | **mean of 3 pairs** | **62.0** | **73.8%** |
| (b) fresh vs old, same run number | run 1 vs run 1 | 56 | 66.7% |
| (b) fresh vs old, same run number | run 2 vs run 2 | 52 | 61.9% |
| (b) fresh vs old, same run number | run 3 vs run 3 | 50 | 59.5% |
| **(b) fresh vs old** | **mean of 3 pairs** | **52.7** | **62.7%** |
| (c) old vs old | run 1 vs run 2 | 60 | 71.4% |
| (c) old vs old | run 1 vs run 3 | 65 | 77.4% |
| (c) old vs old | run 2 vs run 3 | 63 | 75.0% |
| **(c) old within-row** | **mean of 3 pairs** | **62.7** | **74.6%** |

For reference, all 9 fresh-vs-old pairs (any run numbers): mean 51.2/84 (61.0%). R1 (2 Nov) vs old v2b (same run number) was 154/252 = 61.1% in the R1 analysis.

**Additional comparison, same code and prompt on 2 November (R1 attempt 1 against fresh):** identical in 55, 60 and 58 of 84 for the same run number, mean over all 9 run pairs 57.8/84 (68.8%). R1 attempt 1 against old v2b: mean 52.3/84 (62.3%) over all 9 pairs. So agreement shrinks with the time between two runs: about 74% for runs started minutes apart in one invocation (within-row, fresh 73.8%, old 74.6%, R1 73.8%), about 69% for runs a few hours apart on the same day, and 61 to 63% for runs 6 days apart. This is suggestive, not proven: it is 84 questions per pair, and the old rows have no model or fingerprint record to check what changed. The model name is identical (`gpt-4o-2024-08-06`) in the new logs; whether it was the same on 27 October is unknown.

**What it means for scoring.** The mean of the six v2b runs (3 old, 3 fresh) is 60.33/84 (60, 61, 61, 60, 60, 60); the two sets of three differ by 0.67 points, inside the 2 to 4 point noise. The score is stable, but individual questions flip with the date (t2_12, t3_06, t2_01, t2_06, t3_02 below). Since R1, R2, R3 and later rows run after 2 November, compare them against the fresh base (60.00) rather than the old one (60.67), and ideally re-run the base on the same day as a new row.

## 4. Questions whose pass count changed (old v2b to v2b_fresh)

| id | Tier | old v2b | v2b_fresh | Change | Note |
|---|---:|---:|---:|---:|---|
| t2_12 | 2 | 3/3 | 0/3 | -3 | Fresh used `EXTRACT(DOW ...)` (a number) 3/3 instead of old v2b's `TO_CHAR(zeitpunkt, 'Day')` (the name); R1 on the same day did it in 2 of 3 runs. |
| t3_06 | 3 | 0/3 | 3/3 | +3 | Fresh returned one row with `CASE` sums 3/3 (gold shape); old returned two rows with `UNION ALL` 3/3; R1 got the one-row form in 2 of 3 runs. |
| t2_01 | 2 | 3/3 | 1/3 | -2 | Fresh runs 1 and 3 dropped the `SUM(mwh)` column (1 column, gold has 2); old v2b kept it 3/3. |
| t2_06 | 2 | 2/3 | 0/3 | -2 | Fresh returned only `preiszone` (1 column, gold has 2) in 3/3 runs; old did so in 1 of 3. |
| t3_02 | 3 | 0/3 | 2/3 | +2 | Fresh multiplied the share by 100 in runs 1 and 3 (matches gold 30.51); old returned the fraction 0.305 in 3/3. |

5 questions changed; net -2 passes over 3 runs.

## 5. Failure groups a to g (definitions as in `results/failure_inventory_r1_v2b_2026-11-02.md`)

| Group | v2b_fresh: sum (mean/run) | old v2b: sum (mean/run) |
|---|---:|---:|
| a. SQL crash (still crashing at the end) | 6 (2.00) | 5 (1.67) |
| b. False decline (NO_QUERY on tier 1-4) | 0 (0.00) | 0 (0.00) |
| c. Missed decline (SQL on tier 0) | 3 (1.00) | 3 (1.00) |
| d. Empty result (0 rows or only NULLs), gold not empty | 2 (0.67) | 2 (0.67) |
| e. Wrong column count | 22 (7.33) | 20 (6.67) |
| f. Wrong row count | 11 (3.67) | 13 (4.33) |
| g. Wrong values (same shape) | 28 (9.33) | 27 (9.00) |
| **All failures** | **72 (24.00)** | **70 (23.33)** |

Question ids for v2b_fresh (runs failed that way, of 3):

- **a. SQL crash (still crashing at the end):** t4_02 (3/3), t4_04 (3/3)
- **b. False decline (NO_QUERY on tier 1-4):** -
- **c. Missed decline (SQL on tier 0):** u_08 (3/3)
- **d. Empty result (0 rows or only NULLs), gold not empty:** t4_03 (2/3)
- **e. Wrong column count:** t1_18 (3/3), t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_12 (3/3), t2_01 (2/3), t3_11 (2/3)
- **f. Wrong row count:** t2_15 (3/3), t2_21 (3/3), t4_01 (3/3), t3_11 (1/3), t4_03 (1/3)
- **g. Wrong values (same shape):** t2_07 (3/3), t2_12 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t2_25 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3), t3_02 (1/3)

## 6. Latency, tokens, cost (per question, mean over 84 x 3)

| Row | Mean latency (s) | p50 / p95 (s) | Prompt tokens | Completion tokens | Cost (USD) |
|---|---:|---:|---:|---:|---:|
| v2b_fresh | 0.943 | 0.921 / 1.370 | 629.3 | 59.6 | 0.00217 |
| old v2b | 1.478 | 1.385 / 2.112 | 629.3 | 58.8 | 0.00216 |

Cost = prompt tokens x $2.50 + completion tokens x $10.00 per 1M (gpt-4o prices in `run_r1.py`; check against the current OpenAI price page). Latency is the one model call per question.
