# Example bank checks (2026-10-30)

Subject: `example_bank.yaml` (30 items: 28 with gold_sql, 2 tier-0). Nothing else was modified.

The **Summary** has ids, scores and verdicts only, so it can be shared. The held-out parts of this file never contain held-out question text or SQL. The exam texts appear only in the Details section.

---

## Summary (shareable)

### 1. Validator: `python grader/validate_gold_file.py example_bank.yaml`
- RESULT: **FAIL**, 86 failures, 0 warnings, exit code 1.
- Expected: `unknown key(s) ['muster']` on all 30 items. The validator reports it as a FAIL, not a warning, because it treats every unknown key as a failure.
- **Not expected:** 28 items (every tier 1-4 item, ex_01 to ex_28) have no `reihenfolge_relevant` (28 failures) and no `toleranz` (28 failures). Tier-0 items ex_29 and ex_30 are fine: `gold_sql` is explicitly null.
- No other findings: the structure is OK, ids are unique, and all 28 gold_sql run as grader_ro (rows/cols listed in the Details). No SQL errors.
- Consequence if the bank is ever graded: the loader would fall back to `reihenfolge_relevant=False` and `toleranz=0.005` (the file has no `standard` block). The exam uses much tighter values on some items (t2_15: 1e-06; t2_07: 0.001).

### 2. Examples vs exam: same question (cover-up test against all 84 exam items)

**13 of 30 examples are the same question as at least one exam item.** The other 17 are same type only.

| example | same question as (exam) | note |
|---|---|---|
| ex_01 | t1_01 (closest by text, 0.562), t1_08, t1_09, t1_12, t1_14, t1_15, t1_17, t1_19, t1_23, t1_25, t1_28, t1_34 | 12 exam items |
| ex_02 | t1_11, t1_16, t1_27, t1_35 | |
| ex_03 | t1_18 | |
| ex_04 | t3_02 (SQL 0.969) | |
| ex_05 | t2_07 | same year, **same 12 share values**; 2 vs 3 columns (see 5) |
| ex_07 | t3_06 | t3_06 also asks for the absolute difference |
| ex_09 | t2_01 | |
| ex_12 | t2_14 | |
| ex_13 | t2_02 (text 0.643), t2_11, t2_22 | |
| ex_15 | t2_16 | |
| ex_19 | t2_03 (text 0.709) | |
| ex_24 | t2_15 | labels differ (see 3) |
| ex_30 | u_04 | tier 0, same missing concept and same year |

Same type only, but **borderline** (one difference; the exam answer is derivable from the example's output or SQL): ex_10 / t2_06 (direction flipped), ex_14 / t3_01 (top 3 vs top 1), ex_21 / t2_12 (all weekdays vs the top one), ex_22 / t1_11 (text 0.825; yearly series vs one year; the 2025 row is t1_11's answer).

### 3. ex_24 vs t2_15 classification: **same**
- Renewable (6, identical set): Biomasse, Photovoltaik, Sonstige Erneuerbare, Wasserkraft, Wind Offshore, Wind Onshore.
- Conventional (6, identical): Braunkohle, Erdgas, Kernenergie, Pumpspeicher, Sonstige Konventionelle, Steinkohle. Pumpspeicher is conventional in both.
- No source differs. t3_07 uses the same list.
- What does differ: the **labels**. ex_24 returns `Erneuerbare` / `Konventionelle`; t2_15's gold returns `Erneuerbar` / `Konventionell`. The comparator matches text exactly, so an agent that copies ex_24's labels fails t2_15 with a text mismatch, even with correct numbers. Order is irrelevant (t2_15 has reihenfolge_relevant=false).

### 4. Examples vs held-out (ids, scores, verdicts only)

Pairs compared: 756 SQL pairs (28 x 27) and 900 text pairs. TF-IDF pairs above 0.6: 2. SQL pairs above 0.6: 213.

**Same question (9 pairs; 6 examples, 9 held-out items):**

| example | held-out | text | SQL | verdict |
|---|---|---|---|---|
| ex_01 | h1_01 | 0.777 | 0.940 | same question |
| ex_01 | h1_04 | 0.292 | 0.940 | same question |
| ex_01 | h1_07 | 0.000 | 0.940 | same question |
| ex_02 | h1_02 | 0.608 | 0.895 | same question |
| ex_02 | h1_10 | 0.143 | 0.895 | same question |
| ex_04 | h2_03 | 0.460 | 0.937 | same question (borderline: the source set differs in size) |
| ex_07 | h3_01 | 0.582 | 0.646 | same question (SQL form differs, CTE vs none) |
| ex_10 | h2_10 | 0.078 | 0.803 | same question (borderline: zone selection differs) |
| ex_29 | hu_02 | n/a | n/a | same question (**concept-keyword match only, not a side-by-side**; please check by eye) |

**Same type only, closest pairs (one difference):**

| example | held-out | text | SQL | differs in |
|---|---|---|---|---|
| ex_02 | h1_03 | 0.037 | 0.900 | aggregate |
| ex_03 | h1_08 | 0.077 | 0.958 | aggregate |
| ex_13 | h2_06 | 0.210 | 0.857 | source restriction |
| ex_14 | h2_09 | 0.116 | 0.830 | grain |
| ex_16 | h2_04 | 0.000 | 0.859 | grain |
| ex_18 | h2_04 | 0.032 | 0.879 | grain |

**Remaining top-10 pairs from the leak check** (2-4 structural differences each): same type only. Ids: ex_18-h1_07 (text 0.587), ex_25-h1_02 (0.572), ex_11-h1_06 (0.534), ex_17-h2_07 (0.516), ex_24-h1_07 (0.511), ex_17-h1_08 (0.501), ex_04-h3_05 (0.466); ex_03-h1_06 and ex_03-h1_09 (SQL 0.958).

All other pairs differ in 2 or more structural features: same type only. hu_01 and hu_03 are same type only against ex_29 and ex_30 (all are declines; none is the same concept). 24 of the 30 examples have no same-question held-out match.

### 5. ex_05 columns vs t2_07
| item | columns | rows |
|---|---|---|
| ex_05 | **2**: energietraeger, anteil_prozent | 12 |
| t2_07 | **3**: energietraeger, mwh, anteil_prozent | 12 |

- Same question, same window (2025), same 12 sources. ex_05's rows equal t2_07's columns 1 and 3 exactly.
- The comparator checks column count and compares by position. An agent that copies ex_05's shape returns 2 columns and fails t2_07 with "column count mismatch: gold=3 agent=2".

---

## Details

### A. Validator
Rows/cols of the 28 gold_sql: ex_01-04, 06-08 1x1; ex_05 12x2; ex_09-11 1x2; ex_12 5x2; ex_13 12x2; ex_14 3x2; ex_15 12x2; ex_16 30x2; ex_17 14x2; ex_18 8x2; ex_19 24x2; ex_20 12x2; ex_21 7x2; ex_22 4x2; ex_23 2x2; ex_24 2x2; ex_25 1x1; ex_26 31x3; ex_27 12x2; ex_28 6x4.

Failure counts: unknown key `muster`: 30. `reihenfolge_relevant` missing: 28. `toleranz` missing: 28. Total: 86.

### B. Method
- **Exam:** I read every example against every exam question with dates, sources and zones covered up, and compared dimension, measure, aggregate, direction and shape. As a cross-check I extracted abstract features from each gold_sql (tables, aggregate, measure column, metrik, grouping grain, order direction, limit, CTE/join/window/FILTER/HAVING/ratio flags, source and zone selection kind, change-vs-share). The two agree on every pair except ex_07 / t3_06, where t3_06 returns extra columns. I counted that pair as the same question.
- **Held-out:** I ran the same feature comparison on all 756 SQL pairs and printed only ids, differing feature names and scores. I did not display any held-out text or SQL. Verdict rule: same question = no differing feature; otherwise same type only. The borderline cases are the ones where the *selection* of sources or zones differs. The tier-0 pair (ex_29 / hu_02) rests on concept keywords alone, so it is the least certain verdict.
- The feature extractor and its outputs are in the scratchpad (temporary), not in the repo.

### C. Exam: all 30 examples
| example | tier | verdict | closest exam item(s) | difference or note |
|---|---|---|---|---|
| ex_01 | 1 | same question | t1_01 and 11 others | total of one source over a period |
| ex_02 | 1 | same question | t1_11, t1_16, t1_27, t1_35 | average price in one zone |
| ex_03 | 1 | same question | t1_18 | "Highest grid load ever?" |
| ex_04 | 2 | same question | t3_02 | share of wind (on+off) of total generation |
| ex_05 | 3 | same question | t2_07 | 2 vs 3 columns, same values |
| ex_06 | 2 | same type only | t1_07, t3_02 | share of quarter-hours with negative price: a ratio of counts. t1_07 only counts. |
| ex_07 | 2 | same question | t3_06 | percent change of a source's total between two periods |
| ex_08 | 2 | same type only | t3_06 | same percent-change shape, but price average (preise) vs generation sum |
| ex_09 | 2 | same question | t2_01 | which source produced the most |
| ex_10 | 2 | same type only (borderline) | t2_06 | direction flipped (lowest vs highest). ex_10 also excludes '∅ Anrainer DE/LU'; t2_06 does not. The result is the same either way. |
| ex_11 | 2 | same type only | t3_12, t3_01 | day with the lowest total, but residual load (verbrauch), not generation |
| ex_12 | 2 | same question | t2_14 | top 5 quarter-hours by German price |
| ex_13 | 2 | same question | t2_02, t2_11, t2_22 | rank all sources by total |
| ex_14 | 2 | same type only (borderline) | t3_01 | per-day sum for one source, top 3 vs top 1 |
| ex_15 | 2 | same question | t2_16 | monthly average German price |
| ex_16 | 2 | same type only | t3_01, t2_04 | daily series for one source vs the single best day |
| ex_17 | 2 | same type only | t2_24, t2_04 | weekly demand series: no weekly series in the exam |
| ex_18 | 2 | same type only | t2_20, t2_13 | quarterly series vs the single best quarter |
| ex_19 | 2 | same question | t2_03 | average PV by hour of day |
| ex_20 | 2 | same type only | t2_19, t2_10 | price by calendar month: combines t2_19's grain with t2_10's measure |
| ex_21 | 3 | same type only (borderline) | t2_12 | average grid load per weekday, all seven vs the top one |
| ex_22 | 2 | same type only (borderline) | t1_11 | yearly series vs one year; text 0.825 |
| ex_23 | 2 | same type only | t3_08 | weekend vs workday split, but load vs price |
| ex_24 | 2 | same question | t2_15 | renewables vs conventional; see 3 |
| ex_25 | 3 | same type only | t3_11, t3_09 | price conditioned on another series; different condition and shape |
| ex_26 | 3 | same type only | t3_09, t3_11, t3_01 | daily join of PV and price |
| ex_27 | 4 | same type only | none close (t2_04) | the exam has no running total |
| ex_28 | 4 | same type only | t4_01 | top-k per group with window rank; grain and k differ |
| ex_29 | 0 | same type only | u_04, u_06 | decline for absent data (cross-border flows); no exam item has this concept |
| ex_30 | 0 | same question | u_04 | CO2 emissions of German generation in 2025 |

Exam texts for the same-question matches: t1_01 "How much electricity did solar produce in total in June 2025?"; t2_07 "Break down 2025 generation by source and show each one's share in percent."; t2_15 "Wie viel Ökostrom gab es 2025 im Vergleich zum konventionellen Strom?"; t3_06 "How did solar in 2025 compare to 2024, in absolute terms and percent?"; t1_11 "Durchschnittlicher Strompreis in Deutschland im Jahr 2025?"; u_04 "How much CO2 did German electricity generation emit in 2025?"

Leak-check top pairs (examples vs exam), for reference. Text: ex_22-t1_11 0.825, ex_19-t2_03 0.709, ex_04-t3_02 0.666, ex_13-t2_02 0.643, ex_11-t1_29 0.637 (different question: a day vs a total). SQL: ex_04-t3_02 0.969, ex_03-t1_05/t1_29/t1_32/t1_33 0.958 (shared shape only), ex_09-t2_05 0.957, ex_02-t1_11/t1_27/t1_35 0.956, ex_13-t2_02 0.955. Text pairs above 0.6: 5 of 2520. SQL pairs above 0.6: 456 of 2128.

### D. Answer overlap (relevant only if example *results* are ever shown to the agent)
Examples whose output contains an exam answer value (non-trivial numbers matched to 2 decimals): ex_05 -> t2_07 (the full share column); ex_01 -> t2_11, t3_06; ex_02 -> t2_16; ex_09 -> t2_07; ex_10 -> t2_25; ex_13 -> t1_15; ex_16 -> t2_22; ex_22 -> t1_11; ex_26 -> t3_01; ex_27 -> t2_07, t3_06; ex_28 -> t2_07, t2_11, t3_06. For the held-out set (ids only): ex_02 -> h4_02, ex_13 -> h1_07, ex_22 -> h1_02, ex_28 -> h1_01, ex_28 -> h2_06. None of the same-question pairs shares a full answer except ex_05 / t2_07. Many of these overlaps come from shared periods; I did not separate coincidence from design.

### E. Held-out: all 756 SQL pairs
Pairs with 0 or 1 differing feature are in the Summary (table 4). Every other pair has 2 or more differing features: same type only. Nothing in this report shows held-out text or SQL.
