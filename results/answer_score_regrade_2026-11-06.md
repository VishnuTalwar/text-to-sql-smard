# Answer score vs strict score: re-grade of all saved rows (2026-11-06)

Every question-run of every saved row (`results/*.jsonl`, held-out files skipped by name and never opened) was re-graded without any API call: its final SQL was run through the grader's execution path (`grader_ro`) and graded with the strict comparator (D19, unchanged) and with the answer comparator (`grader/answer_comparator.py`, required columns from `grader/answer_columns.yaml`), both on the same execution. Script: `grader/regrade_answer_score.py`. Tier 0 is graded the same in both.

## Per row (mean of the runs, out of 84)

`strict` is the score as recorded when the row was run. `answer` is the new score. `difference` = answer - strict.

| Row | Runs | Strict (recorded) | Answer | Difference | Strict per run | Answer per run |
|---|---:|---:|---:|---:|---|---|
| schema_linked_decline_t0 | 3 | 55.33 | 58.00 | +2.67 | 55, 55, 56 | 58, 58, 58 |
| v2a_t0 | 3 | 59.67 | 64.00 | +4.33 | 60, 59, 60 | 64, 63, 65 |
| v2b_t0 | 3 | 60.67 | 65.67 | +5.00 | 60, 61, 61 | 66, 66, 65 |
| v2c_t0 | 3 | 57.00 | 60.67 | +3.67 | 57, 57, 57 | 61, 60, 61 |
| v2b2_t0 | 3 | 58.67 | 64.67 | +6.00 | 60, 60, 56 | 66, 64, 64 |
| exa | 3 | 59.33 | 61.33 | +2.00 | 59, 59, 60 | 62, 60, 62 |
| exb | 3 | 56.33 | 57.00 | +0.67 | 55, 57, 57 | 56, 57, 58 |
| df | 3 | 52.00 | 58.00 | +6.00 | 52, 52, 52 | 59, 57, 58 |
| v2b_fresh | 3 | 60.00 | 66.33 | +6.33 | 60, 60, 60 | 67, 66, 66 |
| r1 | 3 | 59.33 | 67.00 | +7.67 | 58, 59, 61 | 65, 67, 69 |
| r2 | 3 | 59.67 | 67.67 | +8.00 | 60, 59, 60 | 68, 67, 68 |
| r3 | 3 | 59.67 | 66.00 | +6.33 | 60, 60, 59 | 65, 68, 65 |
| r3b | 3 | 61.67 | 68.00 | +6.33 | 62, 61, 62 | 69, 68, 67 |
| r3b_safe | 3 | 60.00 | 67.67 | +7.67 | 60, 61, 59 | 68, 68, 67 |

## Per tier (mean of the runs; strict recorded / answer)

| Row | Tier 0 (of 8) | Tier 1 (of 35) | Tier 2 (of 25) | Tier 3 (of 12) | Tier 4 (of 4) | Total |
|---|---|---|---|---|---|---|
| schema_linked_decline_t0 | 7.00 / 7.00 | 32.33 / 33.33 | 14.00 / 14.00 | 2.00 / 3.33 | 0.00 / 0.33 | 55.33 / 58.00 |
| v2a_t0 | 7.00 / 7.00 | 33.00 / 33.00 | 17.00 / 17.33 | 2.67 / 6.67 | 0.00 / 0.00 | 59.67 / 64.00 |
| v2b_t0 | 7.00 / 7.00 | 34.00 / 35.00 | 17.67 / 18.00 | 2.00 / 5.33 | 0.00 / 0.33 | 60.67 / 65.67 |
| v2c_t0 | 7.67 / 7.67 | 32.00 / 33.00 | 15.33 / 15.67 | 2.00 / 3.33 | 0.00 / 1.00 | 57.00 / 60.67 |
| v2b2_t0 | 7.00 / 7.00 | 33.33 / 34.33 | 16.00 / 17.33 | 2.33 / 5.67 | 0.00 / 0.33 | 58.67 / 64.67 |
| exa | 8.00 / 8.00 | 32.67 / 33.67 | 15.67 / 15.67 | 3.00 / 4.00 | 0.00 / 0.00 | 59.33 / 61.33 |
| exb | 7.00 / 7.00 | 31.67 / 32.33 | 15.67 / 15.67 | 2.00 / 2.00 | 0.00 / 0.00 | 56.33 / 57.00 |
| df | 8.00 / 8.00 | 26.33 / 28.00 | 14.67 / 15.33 | 3.00 / 6.67 | 0.00 / 0.00 | 52.00 / 58.00 |
| v2b_fresh | 7.00 / 7.00 | 34.00 / 35.00 | 15.33 / 17.00 | 3.67 / 7.33 | 0.00 / 0.00 | 60.00 / 66.33 |
| r1 | 7.00 / 7.00 | 33.67 / 34.67 | 16.00 / 17.00 | 2.67 / 6.33 | 0.00 / 2.00 | 59.33 / 67.00 |
| r2 | 7.00 / 7.00 | 34.33 / 35.00 | 16.00 / 17.00 | 2.33 / 6.67 | 0.00 / 2.00 | 59.67 / 67.67 |
| r3 | 6.33 / 6.33 | 34.33 / 35.00 | 16.33 / 17.33 | 2.67 / 6.00 | 0.00 / 1.33 | 59.67 / 66.00 |
| r3b | 8.00 / 8.00 | 34.00 / 35.00 | 17.00 / 18.00 | 2.67 / 5.67 | 0.00 / 1.33 | 61.67 / 68.00 |
| r3b_safe | 7.67 / 7.67 | 34.00 / 35.00 | 16.00 / 17.00 | 2.33 / 6.33 | 0.00 / 1.67 | 60.00 / 67.67 |

Question-runs graded: 3528 in 42 files; distinct SQL texts executed: 622. Every file has 84 questions.

## Limits of this comparison

- Each distinct SQL text was executed once and both verdicts use those rows. The comparison therefore does not re-sample queries whose result order or tie-breaking can vary between executions.
- `label_only` columns (t2_15, t3_08, t3_11) only have to group the rows the same way. The labels are aligned to the gold labels through the other needed columns, so an answer that attaches a wrong label to the right numbers would still pass.
- Neither score applies the unit hints of the gold file (MW instead of MWh with the unit named); only values are compared.
- A computed column that is not a gold column does not count (for example an absolute gap in t3_12 counts only through the gold columns of its alternative).
- Held-out files were not opened. Rows without a `.jsonl` file (the earliest `.log`-only runs) are not covered.

## Checks

### 1. Consistency: re-run strict verdict vs recorded `passed`

Differences: **0** of 3528 question-runs.

### 2. Monotonic: strict passes but answer fails

Cases: **0** (expected 0).

## Per question: strict fail, answer pass (flips)

218 question-runs flip, on 14 questions. The cell shows in how many of the runs of that row the question flips.

What the strict comparator said for these flips: column count mismatch (extra or missing column): 177; text mismatch (labels): 35; numeric or date mismatch: 6.

| Question | Tier | Flips | Rows (runs flipped) |
|---|---:|---:|---|
| t1_02 | 1 | 6 | schema_linked_decline_t0 3/3, exb 2/3, df 1/3 |
| t1_10 | 1 | 1 | df 1/3 |
| t1_18 | 1 | 31 | v2b_t0 3/3, v2c_t0 3/3, v2b2_t0 3/3, exa 3/3, df 3/3, v2b_fresh 3/3, r1 3/3, r2 2/3, r3 2/3, r3b 3/3, r3b_safe 3/3 |
| t2_01 | 2 | 6 | v2c_t0 1/3, v2b2_t0 1/3, df 2/3, v2b_fresh 2/3 |
| t2_06 | 2 | 22 | v2b_t0 1/3, v2b2_t0 3/3, v2b_fresh 3/3, r1 3/3, r2 3/3, r3 3/3, r3b 3/3, r3b_safe 3/3 |
| t2_12 | 2 | 1 | v2a_t0 1/3 |
| t3_04 | 3 | 28 | schema_linked_decline_t0 2/3, v2a_t0 3/3, v2b_t0 3/3, v2b2_t0 2/3, df 2/3, v2b_fresh 3/3, r1 3/3, r2 2/3, r3 3/3, r3b 2/3, r3b_safe 3/3 |
| t3_06 | 3 | 3 | schema_linked_decline_t0 1/3, v2b2_t0 1/3, r3b_safe 1/3 |
| t3_08 | 3 | 35 | v2a_t0 3/3, v2b_t0 3/3, v2c_t0 3/3, v2b2_t0 3/3, exa 2/3, df 3/3, v2b_fresh 3/3, r1 3/3, r2 3/3, r3 3/3, r3b 3/3, r3b_safe 3/3 |
| t3_09 | 3 | 20 | v2a_t0 3/3, v2b_t0 1/3, v2b2_t0 1/3, df 3/3, v2b_fresh 3/3, r1 2/3, r2 2/3, r3 1/3, r3b 2/3, r3b_safe 2/3 |
| t3_11 | 3 | 30 | schema_linked_decline_t0 1/3, v2a_t0 3/3, v2b_t0 3/3, v2b2_t0 3/3, exa 1/3, df 3/3, v2b_fresh 2/3, r1 3/3, r2 3/3, r3 3/3, r3b 2/3, r3b_safe 3/3 |
| t3_12 | 3 | 4 | v2c_t0 1/3, r2 3/3 |
| t4_02 | 4 | 16 | schema_linked_decline_t0 1/3, v2b_t0 1/3, v2b2_t0 1/3, r1 3/3, r2 3/3, r3 2/3, r3b 2/3, r3b_safe 3/3 |
| t4_04 | 4 | 15 | v2c_t0 3/3, r1 3/3, r2 3/3, r3 2/3, r3b 2/3, r3b_safe 2/3 |

### Flips of two rows in detail

**v2b_fresh**

- t1_18 (tier 1): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=1 agent=2; answer: ok (required: mwh)
- t2_01 (tier 2): runs [1, 3]; strict said: column count mismatch at row 0: gold=2 agent=1; answer: ok (required: energietraeger)
- t2_06 (tier 2): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=2 agent=1; answer: ok (required: preiszone)
- t3_04 (tier 3): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=3 agent=2; answer: ok (required: energietraeger, mwh)
- t3_08 (tier 3): runs [1, 2, 3]; strict said: cell mismatch row 0 col 0: text mismatch: gold='Werktag' agent='Weekday'; answer: ok (required: typ, eur_mwh)
- t3_09 (tier 3): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=2 agent=1; answer: ok (required: eur_mwh)
- t3_11 (tier 3): runs [1, 2]; strict said: column count mismatch at row 0: gold=3 agent=2; answer: ok (required: gruppe, eur_mwh)

**r3b_safe**

- t1_18 (tier 1): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=1 agent=2; answer: ok (required: mwh)
- t2_06 (tier 2): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=2 agent=1; answer: ok (required: preiszone)
- t3_04 (tier 3): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=3 agent=2; answer: ok (required: energietraeger, mwh)
- t3_06 (tier 3): runs [1]; strict said: column count mismatch at row 0: gold=4 agent=3; answer: ok (alternative 1: mwh_2024, mwh_2025, veraenderung_prozent)
- t3_08 (tier 3): runs [1, 2, 3]; strict said: cell mismatch row 0 col 0: text mismatch: gold='Werktag' agent='Weekday'; answer: ok (required: typ, eur_mwh)
- t3_09 (tier 3): runs [1, 3]; strict said: column count mismatch at row 0: gold=2 agent=1; answer: ok (required: eur_mwh)
- t3_11 (tier 3): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=3 agent=2; answer: ok (required: gruppe, eur_mwh)
- t4_02 (tier 4): runs [1, 2, 3]; strict said: column count mismatch at row 0: gold=4 agent=1; answer: ok (required: viertelstunden)
- t4_04 (tier 4): runs [2, 3]; strict said: column count mismatch at row 0: gold=4 agent=1; answer: ok (required: viertelstunden)

