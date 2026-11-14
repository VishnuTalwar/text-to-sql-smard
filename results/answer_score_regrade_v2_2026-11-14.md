# Answer score, version 2 (label_only needs meaning): re-grade of all saved rows (2026-11-14)

Same method as `results/answer_score_regrade_2026-11-06.md`, without any API call: every question-run of every saved row (`results/*.jsonl`; held-out files skipped by name, never opened) had its final SQL run once through the grader's path and graded on the same rows by three comparators: **strict** (D19, unchanged), **answer old** (the D42 comparator, loaded from git commit `0369782`: a label_only column only had to group the rows consistently) and **answer new** (D43: an agent label must contain a keyword of exactly one gold label, from `label_meanings` in `grader/answer_columns.yaml`, and the numbers next to it must match that gold label's row). Script: `grader/regrade_answer_score_v2.py`.

## Per row (mean of the runs, out of 84)

| Row | Strict (recorded) | Answer old | Answer new | Change (new - old) | Answer new per run |
|---|---:|---:|---:|---:|---|
| schema_linked_decline_t0 | 55.33 | 58.00 | 58.00 | +0.00 | 58, 58, 58 |
| v2a_t0 | 59.67 | 64.00 | 64.00 | +0.00 | 64, 63, 65 |
| v2b_t0 | 60.67 | 65.67 | 65.67 | +0.00 | 66, 66, 65 |
| v2c_t0 | 57.00 | 60.67 | 60.67 | +0.00 | 61, 60, 61 |
| v2b2_t0 | 58.67 | 64.67 | 64.67 | +0.00 | 66, 64, 64 |
| exa | 59.33 | 61.33 | 61.33 | +0.00 | 62, 60, 62 |
| exb | 56.33 | 57.00 | 57.00 | +0.00 | 56, 57, 58 |
| df | 52.00 | 58.00 | 58.00 | +0.00 | 59, 57, 58 |
| v2b_fresh | 60.00 | 66.33 | 66.33 | +0.00 | 67, 66, 66 |
| r1 | 59.33 | 67.00 | 67.00 | +0.00 | 65, 67, 69 |
| r2 | 59.67 | 67.67 | 67.67 | +0.00 | 68, 67, 68 |
| r3 | 59.67 | 66.00 | 66.00 | +0.00 | 65, 68, 65 |
| r3b | 61.67 | 68.00 | 68.00 | +0.00 | 69, 68, 67 |
| r3b_safe | 60.00 | 67.67 | 67.67 | +0.00 | 68, 68, 67 |

## Per tier (mean of the runs: strict recorded / answer old / answer new)

| Row | Tier 0 (of 8) | Tier 1 (of 35) | Tier 2 (of 25) | Tier 3 (of 12) | Tier 4 (of 4) |
|---|---|---|---|---|---|
| schema_linked_decline_t0 | 7.00 / 7.00 / 7.00 | 32.33 / 33.33 / 33.33 | 14.00 / 14.00 / 14.00 | 2.00 / 3.33 / 3.33 | 0.00 / 0.33 / 0.33 |
| v2a_t0 | 7.00 / 7.00 / 7.00 | 33.00 / 33.00 / 33.00 | 17.00 / 17.33 / 17.33 | 2.67 / 6.67 / 6.67 | 0.00 / 0.00 / 0.00 |
| v2b_t0 | 7.00 / 7.00 / 7.00 | 34.00 / 35.00 / 35.00 | 17.67 / 18.00 / 18.00 | 2.00 / 5.33 / 5.33 | 0.00 / 0.33 / 0.33 |
| v2c_t0 | 7.67 / 7.67 / 7.67 | 32.00 / 33.00 / 33.00 | 15.33 / 15.67 / 15.67 | 2.00 / 3.33 / 3.33 | 0.00 / 1.00 / 1.00 |
| v2b2_t0 | 7.00 / 7.00 / 7.00 | 33.33 / 34.33 / 34.33 | 16.00 / 17.33 / 17.33 | 2.33 / 5.67 / 5.67 | 0.00 / 0.33 / 0.33 |
| exa | 8.00 / 8.00 / 8.00 | 32.67 / 33.67 / 33.67 | 15.67 / 15.67 / 15.67 | 3.00 / 4.00 / 4.00 | 0.00 / 0.00 / 0.00 |
| exb | 7.00 / 7.00 / 7.00 | 31.67 / 32.33 / 32.33 | 15.67 / 15.67 / 15.67 | 2.00 / 2.00 / 2.00 | 0.00 / 0.00 / 0.00 |
| df | 8.00 / 8.00 / 8.00 | 26.33 / 28.00 / 28.00 | 14.67 / 15.33 / 15.33 | 3.00 / 6.67 / 6.67 | 0.00 / 0.00 / 0.00 |
| v2b_fresh | 7.00 / 7.00 / 7.00 | 34.00 / 35.00 / 35.00 | 15.33 / 17.00 / 17.00 | 3.67 / 7.33 / 7.33 | 0.00 / 0.00 / 0.00 |
| r1 | 7.00 / 7.00 / 7.00 | 33.67 / 34.67 / 34.67 | 16.00 / 17.00 / 17.00 | 2.67 / 6.33 / 6.33 | 0.00 / 2.00 / 2.00 |
| r2 | 7.00 / 7.00 / 7.00 | 34.33 / 35.00 / 35.00 | 16.00 / 17.00 / 17.00 | 2.33 / 6.67 / 6.67 | 0.00 / 2.00 / 2.00 |
| r3 | 6.33 / 6.33 / 6.33 | 34.33 / 35.00 / 35.00 | 16.33 / 17.33 / 17.33 | 2.67 / 6.00 / 6.00 | 0.00 / 1.33 / 1.33 |
| r3b | 8.00 / 8.00 / 8.00 | 34.00 / 35.00 / 35.00 | 17.00 / 18.00 / 18.00 | 2.67 / 5.67 / 5.67 | 0.00 / 1.33 / 1.33 |
| r3b_safe | 7.67 / 7.67 / 7.67 | 34.00 / 35.00 / 35.00 | 16.00 / 17.00 / 17.00 | 2.33 / 6.33 / 6.33 | 0.00 / 1.67 / 1.67 |

Question-runs graded: 3528 in 42 files; distinct SQL texts executed: 622.

## Checks

- **Monotonic (strict pass, answer new fail): 0** (expected 0).
- Monotonic for the old comparator: 0.
- Consistency (re-run strict verdict vs recorded `passed`): 0 differences in 3528 question-runs.
- Verdict changes old -> new: **0** question-runs (0 pass -> fail, 0 fail -> pass).

## Agent labels in t2_15, t3_08 and t3_11

Every distinct text value in any text column of the agent results for these three items (this includes the label column; other text columns, if any, would show as `none`). "Matched to" is what the keyword lists make of it. "Pass / fail" counts the question-runs (new verdict) in which the label appeared.

### t2_15 (`kategorie`; gold labels: Erneuerbar, Konventionell)

| Agent label | Matched to | Question-runs | Pass / fail (answer new) |
|---|---|---:|---|

### t3_08 (`typ`; gold labels: Werktag, Wochenende)

| Agent label | Matched to | Question-runs | Pass / fail (answer new) |
|---|---|---:|---|
| Weekday | Werktag | 38 | 35 / 3 |
| Weekend | Wochenende | 38 | 35 / 3 |
| Wochenende | Wochenende | 4 | 3 / 1 |
| Werktag | Werktag | 3 | 3 / 0 |
| Wochentag | none | 1 | 0 / 1 |

### t3_11 (`gruppe`; gold labels: viel Solar, wenig Solar)

| Agent label | Matched to | Question-runs | Pass / fail (answer new) |
|---|---|---:|---|
| 5000 MWh or below | wenig Solar | 30 | 30 / 0 |
| Above 5000 MWh | viel Solar | 30 | 30 / 0 |

### Question-runs without a usable label, and with an unmatched label

- **t2_15**: 36 question-runs with SQL; 36 returned no text column at all (for example one row with one value column per category), so there was no label to judge: answer new pass 0 / fail 36.
- **t3_08**: 42 question-runs with SQL; 0 returned no text column at all (for example one row with one value column per category), so there was no label to judge: answer new pass 0 / fail 0.
  - unmatched label in exa run 2: ['Wochenende', 'Wochentag']; answer old fail, answer new fail; reason (new): required [typ, eur_mwh]: no agent column means the labels of typ with the right numbers (agent label 'Wochentag' matches no gold label); reason (old): required [typ, eur_mwh]: no agent column has the values of eur_mwh
- **t3_11**: 37 question-runs with SQL; 7 returned no text column at all (for example one row with one value column per category), so there was no label to judge: answer new pass 0 / fail 7.

## Question-runs whose answer verdict changed (old -> new)

(none)

## Limits

- A label that the keyword lists do not know fails, even if a human would accept it (for example a count or a date as the group name). The lists were written blind, before this re-grade, from the question text and the gold labels.
- Each distinct SQL text was executed once; queries with unstable tie order are not re-sampled.
- Held-out files were not opened. Rows without a `.jsonl` file are not covered.
