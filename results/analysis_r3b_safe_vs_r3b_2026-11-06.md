# Analysis: r3b_safe (R3b + safe runner, D41) vs R3b

Date: 2026-11-06. Row r3b_safe = `configs/r3b_safe.yaml` (identical to `configs/r3b.yaml` except `safe_runner: true`), 3 runs, model gpt-4o-2024-08-06, temperature 0, seed 0. Prediction (written and committed before the run, commit 7e5ff5e): `results/r3b_safe_prediction_2026-11-06.md`. Files: `results/r3b_safe_run{1,2,3}_2026-11-06.{log,jsonl,manifest.json}`. R3b = `results/r3b_run{1,2,3}_2026-11-05.jsonl`; v2b_fresh = `results/v2b_fresh_run{1,2,3}_2026-11-02.jsonl`. The held-out files were not opened.

**Short version.** Mean 60.00 (60, 61, 59) against R3b 61.67 (62, 61, 62): -1.67. **The safe runner blocked nothing in any run** (241 SQL queries checked, 0 blocked), so none of the four questions whose pass count changed was affected by a block; they are run-to-run variation. Time cost of the walls: +0.018 s per question on average.

## a. Scores

| Row | Run | Total | T0 | T1 | T2 | T3 | T4 |
|---|---|---:|---:|---:|---:|---:|---:|
| r3b_safe | run 1 | 60 | 7 | 34 | 17 | 2 | 0 |
| r3b_safe | run 2 | 61 | 8 | 34 | 16 | 3 | 0 |
| r3b_safe | run 3 | 59 | 8 | 34 | 15 | 2 | 0 |
| **r3b_safe** | **mean** | **60.00** | **7.67** | **34.00** | **16.00** | **2.33** | **0.00** |
| R3b | run 1 | 62 | 8 | 34 | 17 | 3 | 0 |
| R3b | run 2 | 61 | 8 | 34 | 17 | 2 | 0 |
| R3b | run 3 | 62 | 8 | 34 | 17 | 3 | 0 |
| **R3b** | **mean** | **61.67** | **8.00** | **34.00** | **17.00** | **2.67** | **0.00** |
| v2b_fresh | run 1 | 60 | 7 | 34 | 15 | 4 | 0 |
| v2b_fresh | run 2 | 60 | 7 | 34 | 16 | 3 | 0 |
| v2b_fresh | run 3 | 60 | 7 | 34 | 15 | 4 | 0 |
| **v2b_fresh** | **mean** | **60.00** | **7.00** | **34.00** | **15.33** | **3.67** | **0.00** |

Difference r3b_safe - R3b (mean): -1.67; per tier: T0 -0.33, T1 +0.00, T2 -1.00, T3 -0.33, T4 +0.00

## b. Safe runner

| Run | SQL queries checked | Blocked | Wall 1 | Wall 2 | Wall 3 | Blocks that were the final answer |
|---|---:|---:|---:|---:|---:|---:|
| run 1 | 81 | 0 | 0 | 0 | 0 | 0 |
| run 2 | 80 | 0 | 0 | 0 | 0 | 0 |
| run 3 | 80 | 0 | 0 | 0 | 0 | 0 |
| **all 3** | **241** | **0** | | | | |

Blocked by wall and reason:

(no query was blocked in any run)

Every block:

Blocked queries identical to the final SQL of a passing R3b answer: 0 (expected none).

## c. Loop numbers

| Row | Run | Retry rate | Mean attempts | Error retries | Empty retries (rows / NULL) | System declines (ids) | Reviews fired (ids) | Cap hits |
|---|---|---:|---:|---:|---:|---|---|---:|
| r3b_safe | run 1 | 3/84 (3.6%) | 1.048 | 3 | 0 / 1 | u_08 | t1_12 | 0 |
| r3b_safe | run 2 | 2/84 (2.4%) | 1.036 | 3 | 0 / 1 | u_08 | - | 0 |
| r3b_safe | run 3 | 2/84 (2.4%) | 1.036 | 3 | 0 / 1 | u_08 | - | 0 |
| R3b | run 1 | 3/84 (3.6%) | 1.071 | 4 | 3 / 1 | u_08 | - | 1 |
| R3b | run 2 | 2/84 (2.4%) | 1.024 | 1 | 0 / 1 | u_08 | t1_12 | 0 |
| R3b | run 3 | 3/84 (3.6%) | 1.060 | 3 | 3 / 1 | u_08 | - | 1 |

## d. Questions whose pass count changed, R3b -> r3b_safe

| id | Tier | R3b | r3b_safe | Change | Loop activity r3b_safe / R3b | Marking |
|---|---:|---:|---:|---:|---|---|
| t2_09 | 2 | 3/3 | 2/3 | -1 | - / - | run-to-run variation |
| t2_12 | 2 | 3/3 | 1/3 | -2 | - / - | run-to-run variation |
| t3_06 | 3 | 2/3 | 1/3 | -1 | - / - | run-to-run variation |
| u_05 | 0 | 3/3 | 2/3 | -1 | - / - | run-to-run variation |

4 questions changed; net -5 passes over 3 runs (0 caused by the safe runner).
Attempt-1 reply differs from R3b (same run number, same question) in 106 of 252 question-runs (attempt 1 is identical in prompt; the safe runner cannot influence it).

## e. Failure groups

| Group | r3b_safe: sum (mean/run) | R3b: sum (mean/run) | v2b_fresh: sum (mean/run) |
|---|---:|---:|---:|
| a. SQL crash (still crashing, or blocked, at the end) | 0 (0.00) | 0 (0.00) | 6 (2.00) |
| b. False decline (NO_QUERY on tier 1-4) | 0 (0.00) | 0 (0.00) | 0 (0.00) |
| c. Missed decline (SQL on tier 0) | 1 (0.33) | 0 (0.00) | 3 (1.00) |
| d. Empty result (0 rows or only NULLs), gold not empty | 0 (0.00) | 2 (0.67) | 2 (0.67) |
| e. Wrong column count | 28 (9.33) | 26 (8.67) | 22 (7.33) |
| f. Wrong row count | 13 (4.33) | 12 (4.00) | 11 (3.67) |
| g. Wrong values (same shape) | 30 (10.00) | 27 (9.00) | 28 (9.33) |
| **All failures** | **72 (24.00)** | **67 (22.33)** | **72 (24.00)** |

Question ids for r3b_safe (runs failed that way, of 3):

- **a.** -
- **b.** -
- **c.** u_05 (1/3)
- **d.** -
- **e.** t1_18 (3/3), t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_11 (3/3), t3_12 (3/3), t4_02 (3/3), t4_04 (3/3), t3_06 (1/3)
- **f.** t2_15 (3/3), t2_21 (3/3), t4_01 (3/3), t4_03 (3/3), t3_06 (1/3)
- **g.** t2_07 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t2_25 (3/3), t3_02 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3), t2_12 (2/3), t2_09 (1/3)

Question ids for R3b (runs failed that way, of 3):

- **a.** -
- **b.** -
- **c.** -
- **d.** t4_03 (2/3)
- **e.** t1_18 (3/3), t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_12 (3/3), t4_02 (3/3), t4_04 (3/3), t3_11 (2/3)
- **f.** t2_15 (3/3), t2_21 (3/3), t4_01 (3/3), t3_06 (1/3), t4_03 (1/3), t3_11 (1/3)
- **g.** t2_07 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t2_25 (3/3), t3_02 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3)

## f. Time, tokens, cost (per question, 84 x 3)

`check_seconds` = time the loop spends executing SQL. In R3b that is `executor.run_query`; in r3b_safe it is `safe_execute` (static check + EXPLAIN + the read-only run with the server-side cursor), so the difference is the cost of the walls.

| Row | Checks mean (s) | Checks p95 (s) | Checks p50 (s) | Total p50 / p95 (model + checks, s) | Model-only p50 / p95 (s) | Prompt tokens | Completion tokens | Cost (USD) |
|---|---:|---:|---:|---|---|---:|---:|---:|
| r3b_safe | 0.0889 | 0.2332 | 0.0780 | 1.320 / 2.555 | 1.242 / 2.475 | 657.0 | 63.4 | 0.00228 |
| R3b | 0.0707 | 0.1418 | 0.0620 | 1.276 / 2.545 | 1.216 / 2.465 | 677.2 | 64.4 | 0.00234 |
| v2b_fresh | n/a | n/a | n/a | n/a | 0.921 / 1.370 | 629.3 | 59.6 | 0.00217 |

Total API cost of the 3 r3b_safe runs: $0.5738.
Per executed query: r3b_safe 0.0929 s, R3b 0.0733 s.

## g. Model, fingerprints, manifests

| model | system_fingerprint | Calls |
|---|---|---:|
| gpt-4o-2024-08-06 | fp_625eb29508 | 172 |
| gpt-4o-2024-08-06 | fp_e665f1271d | 87 |
| gpt-4o-2024-08-06 | fp_4c910a9acf | 3 |

Total calls: 262; all `gpt-4o-2024-08-06`: True
R3b: fp_7c2c459cd0 (210), fp_e665f1271d (55)
v2b_fresh: fp_625eb29508 (163), fp_e85bcce457 (51), fp_d44a43dee5 (33), fp_4c910a9acf (5)

| Manifest | working_tree_clean | commit | modified tracked files | switches | limits | start | end |
|---|---|---|---|---|---|---|---|
| r3b_safe_run1_2026-11-06.manifest.json | True | 7e5ff5e | [] | error_retry,empty_retry,decline_review,empty_fact_decline,safe_runner | {'max_plan_cost': 15533613.4, 'max_rows': 20000, 'timeout_ms': 30000} | 2026-11-06T19:33:21 | 2026-11-06T19:37:08 |
| r3b_safe_run2_2026-11-06.manifest.json | True | 7e5ff5e | [] | error_retry,empty_retry,decline_review,empty_fact_decline,safe_runner | {'max_plan_cost': 15533613.4, 'max_rows': 20000, 'timeout_ms': 30000} | 2026-11-06T19:37:08 | 2026-11-06T19:40:49 |
| r3b_safe_run3_2026-11-06.manifest.json | True | 7e5ff5e | [] | error_retry,empty_retry,decline_review,empty_fact_decline,safe_runner | {'max_plan_cost': 15533613.4, 'max_rows': 20000, 'timeout_ms': 30000} | 2026-11-06T19:40:49 | 2026-11-06T19:44:26 |

## Extra checks (no API calls, made after the run)

These test whether anything other than a block could explain the -1.67.

1. **Same rows on both execution paths?** All 241 SQL queries of r3b_safe were run through `executor.run_query` and through `safe_execute`. 234 gave identical results (rows or error). 7 differed, all from three questions that have no total order in their query: t2_14 (`ORDER BY preis_eur_mwh DESC LIMIT 5` with tied prices, 3 queries), t2_21 (3 queries) and t3_06 (1 query). On repeated runs of the same t2_14 SQL, the plain path returned 5 different results in 6 executions (tie order at the LIMIT is not stable on the plain path itself), the safe path 1. A likely reason (not tested) is that the safe path reads through a server-side cursor, and PostgreSQL does not use parallel plans for cursors. For t2_21 and t3_06 I could not reproduce a difference in 6 repeats of one SQL variant. This does not touch the score: the grader still compares the agent SQL through `executor.run_query`, and the loop uses the safe-path rows only to decide "empty or not" (row count), which is not affected by order. It matters later for the UI, where the displayed rows would come from the safe path.
2. **Empty-result decisions.** The 5 distinct SQL texts that were empty or only NULL in R3b (t4_03, u_08) give the same result on the safe path (0 rows for t4_03; 1 NULL row for u_08), so the empty-retry and system-decline logic would have decided the same. R3b's extra empty retries on t4_03 (runs 1 and 3) came from a different attempt-1 SQL (0 rows in R3b runs 1 and 3, 80 rows in all three r3b_safe runs), i.e. model variation.
3. **Attempt 1 is not influenced by the safe runner.** Prompt and settings are identical to R3b, so the attempt-1 replies can differ only through the API's non-determinism (fingerprints differ between sets). They differ from R3b in 106 of 252 question-runs, about the same as R3b vs R3 (111 of 252).
4. **u_08** was a system decline on attempt 1 in all three runs (1 attempt each); nothing reached the "reads no table" rule.

## h. Prediction check

| Bullet of the prediction | Verdict | Deciding number |
|---|---|---|
| Base: R3b 61.67 (62, 61, 62), v2b_fresh 60.00, model gpt-4o-2024-08-06 | confirmed (reference values as stated; model as stated) | all 262 calls report gpt-4o-2024-08-06 |
| No answer that would pass is blocked | confirmed | 0 of 241 queries blocked; 0 blocked queries equal a passing R3b answer (gold: 76/76 pass, see D41) |
| Blocks: 0 to 2 per run, all wall 1; 0 at walls 2 and 3 | confirmed, at the low end; the "mostly unparseable t4_02/t4_04 attempts" part could not be tested | 0, 0, 0 blocks per run; no unparseable attempt occurred (t4_02 and t4_04 had no retry) |
| u_08 is still declined by the system decline on attempt 1, so "reads no table" does not fire | confirmed | u_08: system decline, 1 attempt, in 3 of 3 runs; 0 blocks |
| Total within noise of R3b (roughly 59 to 64); expected change about 0 | **partly** | runs 60 / 61 / 59 are inside 59 to 64 (59 is at the edge), but the mean change is -1.67, not about 0. 0 of 4 changed questions caused by the safe runner |
| Time per question rises by the EXPLAIN call only (well under 0.1 s) | confirmed | time in checks per question 0.0889 s vs 0.0707 s (+0.018 s); per executed query +0.020 s; p95 of the checks 0.2332 s vs 0.1418 s (+0.091 s, just under 0.1) |

## Reading

- With no block, r3b_safe and R3b run the same loop on the same prompts; the only difference is the execution path in front of the model's retry decisions (extra checks 1 and 2: same rows apart from tie order, same empty-result decisions). The -1.67 is therefore run-to-run variation of the model, not an effect of the walls. This fits the picture from earlier rows: R3 59.67, v2b_fresh 60.00, r3b_safe 60.00, R3b 61.67; the noise is about 2 to 4 points per run (PROJECT_PROGRESS.md), and R3b's 61.67 may have been on the high side.
- This is an inference from "no block fired and the paths agree", not a separate measurement of the safe runner's effect on accuracy; a single set of 3 runs cannot show a difference smaller than the noise.
- The prediction "change about 0" was too tight for this noise level; the roughly 59 to 64 range in the same bullet was right.
- Failure groups (sums over 3 runs, r3b_safe minus R3b): c +1, d -2, e +2, f +1, g +3. Explained by the four changed questions (t2_09 and t2_12 give g +3, u_05 gives c +1, t3_06 gives e +1) plus two questions that failed in both rows but with a different attempt-1 SQL: t4_03 (R3b: empty result in 2 runs; r3b_safe: wrong row count in all 3, so d -2, f +2) and t3_11 (f to e, so e +1, f -1). None of this involves a block.
- Cost per question is unchanged (about $0.0023); total API cost of the three runs $0.5738.
- Open (not caused by this run): the safe path can order tied rows differently from the grader's path (extra check 1).
