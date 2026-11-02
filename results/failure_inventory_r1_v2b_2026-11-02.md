# Failure inventory for R1 and v2b, 2026-11-02

Sources: `results/r1_run{1,2,3}_2026-11-02.jsonl` and `results/v2b_t0_run{1,2,3}_2026-10-27.jsonl` (84 questions x 3 runs each; final SQL of each question). Read-only analysis: no API call; the failing SQL was re-run against the read-only database (grader_ro) to detect empty results. Each failed question-run is put in exactly one group, first fit in the order a to g.

## Group counts (failed question-runs, summed over 3 runs; mean per run in brackets)

| Group | R1 | v2b |
|---|---:|---:|
| a. SQL crash (still crashing at the end) | 0 (0.00) | 5 (1.67) |
| b. False decline (NO_QUERY on tier 1-4) | 3 (1.00) | 0 (0.00) |
| c. Missed decline (SQL on tier 0) | 3 (1.00) | 3 (1.00) |
| d. Empty result (0 rows or only NULLs), gold not empty | 3 (1.00) | 2 (0.67) |
| e. Wrong column count | 27 (9.00) | 20 (6.67) |
| f. Wrong row count | 8 (2.67) | 13 (4.33) |
| g. Wrong values (same shape) | 30 (10.00) | 27 (9.00) |
| **All failures** | **74 (24.67)** | **70 (23.33)** |

Failures = 84 x 3 minus passes: R1 74, v2b 70.

## Question ids per group (id (runs failed that way, of 3))

**a. SQL crash (still crashing at the end)**

- R1: -
- v2b: t4_04 (3/3), t4_02 (2/3)

**b. False decline (NO_QUERY on tier 1-4)**

- R1: t2_15 (2/3), t1_12 (1/3)
- v2b: -

**c. Missed decline (SQL on tier 0)**

- R1: u_08 (3/3)
- v2b: u_08 (3/3)

**d. Empty result (0 rows or only NULLs), gold not empty**

- R1: t4_03 (3/3)
- v2b: t4_03 (2/3)

**e. Wrong column count**

- R1: t1_18 (3/3), t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_11 (3/3), t3_12 (3/3), t4_02 (3/3), t4_04 (3/3)
- v2b: t1_18 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_11 (3/3), t3_12 (3/3), t2_06 (1/3), t4_02 (1/3)

**f. Wrong row count**

- R1: t2_21 (3/3), t4_01 (3/3), t2_15 (1/3), t3_06 (1/3)
- v2b: t2_15 (3/3), t2_21 (3/3), t3_06 (3/3), t4_01 (3/3), t4_03 (1/3)

**g. Wrong values (same shape)**

- R1: t2_07 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t2_25 (3/3), t3_02 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3), t2_12 (2/3), t2_09 (1/3)
- v2b: t2_07 (3/3), t2_14 (3/3), t2_18 (3/3), t2_20 (3/3), t2_25 (3/3), t3_02 (3/3), t3_03 (3/3), t3_08 (3/3), t3_10 (3/3)

## Group e split: agent has fewer or more columns than gold

- Agent has FEWER columns than gold, R1: 24 failures; t2_06 (3/3), t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_11 (3/3), t3_12 (3/3), t4_02 (3/3), t4_04 (3/3)
- Agent has FEWER columns than gold, v2b: 17 failures; t3_04 (3/3), t3_07 (3/3), t3_09 (3/3), t3_11 (3/3), t3_12 (3/3), t2_06 (1/3), t4_02 (1/3)

- Agent has MORE columns than gold, R1: 3 failures; t1_18 (3/3)
- Agent has MORE columns than gold, v2b: 3 failures; t1_18 (3/3)

## Gold queries that legitimately return 0 rows or only NULL (needed before R2)

None of the 76 gold queries returns 0 rows or only NULL.

76 gold queries were run; the 8 tier-0 questions have no gold SQL, so they are not part of this count.

Group e/f/a here are not the same as the "shape failures" (column count + row count + SQL errors) quoted before: groups a, d, e, f for v2b add up to 5 + 2 + 20 + 13 = 40, the same total, but 2 of the former row-count failures are now in group d because the agent's SQL returned 0 rows (t4_03).

### What this means for R2 (empty-result retry)
- No gold query is empty or all-NULL, so on this exam a correct answer is never an empty result; R2 cannot "correct" a correct answer here. (Real questions can still have legitimately empty answers; the exam just has none.)
- Empty results among the failures: t4_03 (agent SQL returns 0 rows, 3/3 in R1, 2/3 in v2b; gold has rows) and the tier-0 question u_08, whose answered SQL returns a single NULL (`SUM(mwh)` over July 2026) in all 6 runs of R1 and v2b. u_08 is group c (missed decline), not group d, because tier 0 is classified first.
- So R2 has two targets on the exam: t4_03 and u_08 (an empty result could lead to a correct decline).

## Model version check (read-only)

Question: do the logs record which model answered (the `model` field of the OpenAI response, for example a dated name such as `gpt-4o-2024-08-06`) and the `system_fingerprint`?

**Result files.** Every `.jsonl` record has the same fields: id, tier, question, retrieved_tables, raw_model_output, extracted_sql, passed, comparator_reason, latency_seconds, prompt_tokens, completion_tokens (R1 adds the loop fields and an `attempts` list with the same per-call fields). No `model` and no `system_fingerprint` field exists in any of them.

| Row | Files checked | Model name | system_fingerprint |
|---|---|---|---|
| schema_linked_decline (Step G) | run 1, 2, 3 | not recorded | not recorded |
| v2a | run 1, 2, 3 | not recorded | not recorded |
| v2b | run 1, 2, 3 | not recorded | not recorded |
| v2c | run 1, 2, 3 | not recorded | not recorded |
| v2b2 | run 1, 2, 3 | not recorded | not recorded |
| ex-a | run 1, 2, 3 | not recorded | not recorded |
| ex-b | run 1, 2, 3 | not recorded | not recorded |
| df | run 1, 2, 3 | not recorded | not recorded |
| R1 | run 1, 2, 3 (also in each `attempts` entry) | not recorded | not recorded |
| baseline and schema-linked (earlier rows) | only `.log` files, no `.jsonl` | not recorded | not recorded |
| held-out v2b (6 files) | not opened, as instructed | not recorded, by the code path: they were written by `run_v2b.py` through the same `result_logging.make_record` | not recorded, same reason |

The `.log` files and the `_stdout_*.txt` files contain only report text and the `httpx` line `POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"`, which has no model name.

**Code.**
- `grader/naive_agent.py`: sends `model="gpt-4o"` (the constant `MODEL`), temperature 0, seed 0. That is the alias, not a dated snapshot, so OpenAI decides which snapshot answers.
- `grader/result_logging.py` (used by every row up to df): the recorder keeps `choices[0].message.content`, latency, `usage.prompt_tokens` and `usage.completion_tokens`. It does not read `response.model` or `response.system_fingerprint`.
- `grader/agent_loop.py` (R1): `call_openai` sends `model=MODEL` (the same `"gpt-4o"`) and returns the same four values. It also does not read `response.model` or `response.system_fingerprint`.

**Conclusion.** Nothing in the logs says which snapshot of `gpt-4o` produced any result, so a change of the model behind the alias between 27 October and 2 November can be neither confirmed nor ruled out. The API normally returns both fields on every response, so recording them is a small change in `result_logging.py` and `agent_loop.py` (not made here). It would only help for future runs.
