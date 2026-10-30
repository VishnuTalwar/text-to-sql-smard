# ex-a vs v2b, exam (84 items), 3 runs each, 2026-10-31

v2b = `v2b_t0_run1_2026-10-27.jsonl` … runs 1-3 (2026-10-27). ex-a = `exa_run1_2026-10-31.jsonl` … runs 1-3. Same model, temperature 0, seed 0; the only prompt difference is the static 8-example block (ex_06, 07, 11, 13, 16, 20, 24, 26). Exam only; the held-out set was not run.

## 1. Totals per run and per tier

| tier | n | v2b r1 | r2 | r3 | v2b mean | ex-a r1 | r2 | r3 | ex-a mean | Δ mean |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 8 | 7 | 7 | 7 | 7.00 | 8 | 8 | 8 | 8.00 | +1.00 |
| 1 | 35 | 34 | 34 | 34 | 34.00 | 32 | 33 | 33 | 32.67 | -1.33 |
| 2 | 25 | 17 | 18 | 18 | 17.67 | 16 | 15 | 16 | 15.67 | -2.00 |
| 3 | 12 | 2 | 2 | 2 | 2.00 | 3 | 3 | 3 | 3.00 | +1.00 |
| 4 | 4 | 0 | 0 | 0 | 0.00 | 0 | 0 | 0 | 0.00 | +0.00 |
| **all** | 84 | 60 | 61 | 61 | 60.67 | 59 | 59 | 60 | 59.33 | -1.33 |

Run-to-run range: v2b 60-61, ex-a 59-60.

## 2. Questions that changed

### 0/3 → 3/3 (4)

| id | tier | v2b passes | ex-a passes | v2b failures (grader) | ex-a failures (grader) |
|---|---|---|---|---|---|
| t2_20 | 2 | 0/3 | 3/3 | r1:value; r2:value; r3:value | r1:pass; r2:pass; r3:pass |
| t2_25 | 2 | 0/3 | 3/3 | r1:value; r2:value; r3:value | r1:pass; r2:pass; r3:pass |
| t3_02 | 3 | 0/3 | 3/3 | r1:value; r2:value; r3:value | r1:pass; r2:pass; r3:pass |
| u_08 | 0 | 0/3 | 3/3 | r1:tier 0: SQL instead of decline; r2:tier 0: SQL instead of decline; r3:tier 0: SQL instead of decline | r1:pass; r2:pass; r3:pass |

### 3/3 → 0/3 (5)

| id | tier | v2b passes | ex-a passes | v2b failures (grader) | ex-a failures (grader) |
|---|---|---|---|---|---|
| t2_09 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:value; r2:value; r3:value |
| t2_12 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:decline |
| t2_16 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:value; r2:value; r3:value |
| t2_24 | 2 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:value; r2:value; r3:value |
| t3_05 | 3 | 3/3 | 0/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:decline |

### Partial changes (6): pass count differs, not 0↔3

| id | tier | v2b passes | ex-a passes | v2b failures (grader) | ex-a failures (grader) |
|---|---|---|---|---|---|
| t1_25 | 1 | 3/3 | 1/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:decline; r3:pass |
| t1_26 | 1 | 3/3 | 1/3 | r1:pass; r2:pass; r3:pass | r1:decline; r2:pass; r3:decline |
| t2_03 | 2 | 3/3 | 2/3 | r1:pass; r2:pass; r3:pass | r1:pass; r2:decline; r3:pass |
| t2_06 | 2 | 2/3 | 3/3 | r1:cols; r2:pass; r3:pass | r1:pass; r2:pass; r3:pass |
| t3_06 | 3 | 0/3 | 2/3 | r1:rows; r2:rows; r3:rows | r1:rows; r2:pass; r3:pass |
| t3_09 | 3 | 0/3 | 1/3 | r1:cols; r2:cols; r3:cols | r1:pass; r2:value; r3:value |

Grader reason detail (first distinct failing reason per side, truncated):

- **t2_20** v2b: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.date(2025, 10, 1) agent=Decimal('4') | ex-a: -
- **t2_25** v2b: cell mismatch row 0 col 0: text mismatch: gold='Polen' agent='Schweden 4' | ex-a: -
- **t3_02** v2b: cell mismatch row 0 col 0: numeric mismatch: gold=30.51 agent=0.3050639518164282 (toleranz=0.001) | ex-a: -
- **u_08** v2b: tier 0: agent returned SQL when it should have declined | ex-a: -
- **t2_09** v2b: - | ex-a: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.date(2026, 5, 1) agent=Decimal('5')
- **t2_12** v2b: - | ex-a: declined (no SQL)
- **t2_16** v2b: - | ex-a: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.date(2025, 1, 1) agent=1
- **t2_24** v2b: - | ex-a: cell mismatch row 0 col 0: datetime mismatch: gold=datetime.date(2025, 1, 1) agent=1
- **t3_05** v2b: - | ex-a: declined (no SQL)
- **t1_25** v2b: - | ex-a: declined (no SQL)
- **t1_26** v2b: - | ex-a: declined (no SQL)
- **t2_03** v2b: - | ex-a: declined (no SQL)
- **t2_06** v2b: column count mismatch at row 0: gold=2 agent=1 | ex-a: -
- **t3_06** v2b: row count mismatch: gold=1 agent=2 | ex-a: row count mismatch: gold=1 agent=2
- **t3_09** v2b: column count mismatch at row 0: gold=2 agent=1 | ex-a: cell mismatch row 0 col 1: numeric mismatch: gold=45.29291666666666 agent=35.04 (toleranz=1e-06)

Unchanged always-failing (0/3 both): 17 → t1_18, t2_07, t2_14, t2_15, t2_18, t2_21, t3_03, t3_04, t3_07, t3_08, t3_10, t3_11, t3_12, t4_01, t4_02, t4_03, t4_04

## 3. Failures by kind (sum over 3 runs, per-run in brackets)

| kind | v2b | ex-a |
|---|---|---|
| wrong column count | 20 (7, 7, 6) | 11 (5, 3, 3) |
| wrong row count | 15 (5, 5, 5) | 5 (2, 2, 1) |
| wrong value | 27 (9, 9, 9) | 23 (7, 8, 8) |
| SQL error | 5 (2, 1, 2) | 0 (0, 0, 0) |
| wrong decline | 0 (0, 0, 0) | 35 (11, 12, 12) |
| tier 0: SQL instead of decline | 3 (1, 1, 1) | 0 (0, 0, 0) |
| total failures | 70 | 74 |

## 4. Table check: agent queries using a table not shown in that question's prompt

Counted over agent queries (non-empty SQL) per run: v2b [0, 0, 0] (total 0), ex-a [0, 0, 0] (total 0).

v2b: none.

ex-a: none.

## 5. Copy check: agent SQL (sqlglot-normalised, SequenceMatcher) vs the 8 examples, ratio > 0.9

v2b (control, never saw the examples): 0 hits. ex-a: 3 hits. Highest ratio overall: v2b 0.744, ex-a 0.979.

| run | question | example | ratio | passed |
|---|---|---|---|---|
| r1 | t2_16 | ex_20 | 0.979 | no |
| r2 | t2_16 | ex_20 | 0.979 | no |
| r3 | t2_16 | ex_20 | 0.979 | no |

Top 5 ex-a ratios: t2_16 r3~ex_20 0.979; t2_16 r2~ex_20 0.979; t2_16 r1~ex_20 0.979; t2_10 r3~ex_20 0.867; t2_10 r2~ex_20 0.867

## 6. Wrong declines (tier 1-4 declined)

v2b: [0, 0, 0] per run; r1: -; r2: -; r3: -
ex-a: [11, 12, 12] per run; r1: t1_25, t1_26, t2_12, t2_15, t3_04, t3_05, t3_12, t4_01, t4_02, t4_03, t4_04; r2: t1_25, t2_03, t2_12, t3_04, t3_05, t3_07, t3_11, t3_12, t4_01, t4_02, t4_03, t4_04; r3: t1_26, t2_12, t2_15, t3_04, t3_05, t3_07, t3_11, t3_12, t4_01, t4_02, t4_03, t4_04
Tier 0 correctly declined: v2b [7, 7, 7] of 8 per run, ex-a [8, 8, 8] of 8 per run.

## 7. Latency and tokens (per API call, all 3 runs pooled; 252 calls each)

| | v2b | ex-a |
|---|---|---|
| mean latency (s) | 1.48 | 1.09 |
| p95 latency (s) | 2.10 | 1.48 |
| mean prompt tokens | 629 | 1624 |
| mean completion tokens | 59 | 50 |

Prompt tokens are the API's usage counts (OpenAI tokenizer, includes message overhead), so they sit a few tokens above the tiktoken counts quoted when ex-a was built (v2b 622, ex-a 1617).

## 8. Notes on the two large effects

**Wrong declines (35 over 3 runs, 0 for v2b).** All ex-a declines are of the form "NO_QUERY: the table does not contain information about X" or "the question does not specify Y". Run 1 examples: t2_12 "no information about the day of the week", t3_05 "no information about the highest and lowest grid load per day", t4_04 "no information about consecutive intervals", t2_15 "does not specify which sources are renewable", t3_04 "does not specify a date range or price zone". These are derivable or computable from the schema, so they are over-declines, not missing data. Declined in all 3 runs: t2_12, t3_04, t3_05, t3_12, t4_01, t4_02, t4_03, t4_04. Declined in 2 of 3 runs: t2_15, t3_07, t3_11 (and t1_25, t1_26 in 2 of 3 via different runs). Of the 17 questions that fail 0/3 in both rows, 9 involve ex-a declines (t3_04, t3_12, t4_01 to t4_04 in all 3 runs; t2_15, t3_07, t3_11 in 2 of 3), so for them the failure kind changed (wrong columns/rows/value or SQL error → decline) without a gain. t2_12 and t3_05 (both 3/3 in v2b) became 0/3 purely through declines.
The cause was not tested here. The comparison only shows that adding the block moved the model from "attempt and be wrong" to "decline" on hard items, and fixed u_08 (tier 0) in all 3 runs.

**Copy of ex_20.** t2_16 reproduces ex_20 (cyclic month as integer, `EXTRACT(MONTH …)::int`) at ratio 0.979 in all 3 runs, and fails because the gold wants a calendar-month date (gold `2025-01-01`, agent `1`). t2_24 and t2_09 fail the same way (date expected, integer returned). t2_10 is at 0.867 against ex_20. v2b never exceeded 0.744 against any example. The three 3/3 → 0/3 value failures are therefore a grain/format choice (cyclic vs calendar month) that the examples pull toward the cyclic form.

**Table check.** No agent query in either row used a table missing from its prompt, so the mismatch between the shown tables and the example tables did not lead to out-of-prompt queries.

**Caveats.** 3 runs per row at temperature 0 and seed 0; v2b runs differ by at most 1 item and ex-a by 1, so per-question 0↔3 flips are the real signal and the −1.33 mean is within what a handful of such flips produces. The exam was used for this comparison; the held-out set was not run.
