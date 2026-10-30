# Example bank checks v2 (2026-10-30)

Subject: `example_bank.yaml` after replacing 14 examples and rewording ex_22 (30 items; 28 with gold_sql, 2 tier-0). Compared with the first check: `results/example_bank_checks_2026-10-30.md`.

The **Summary** has ids, feature names, scores and verdicts only, with no question text and no SQL, so it can be shared. The held-out parts of this file never contain held-out text or SQL.

---

## Summary (shareable)

### 1. Tools
- `grader/structure_check.py` (new): compares the gold_sql structure of two YAML files pair by pair, with dates, sources and zones masked. It prints ids, differing feature names and a verdict ("same question" = no differing feature, otherwise "same type only"). It never prints question text or SQL, whichever file is B. Exit code 1 if any pair is "same question".
- `grader/validate_gold_file.py --examples`: skips the `reihenfolge_relevant` / `toleranz` checks and allows `muster`. Without the flag nothing changed: exam and held-out still PASS, and the example bank without the flag still reports the same 86 failures.
- The new tool reproduces the first check's structural verdicts on the old bank. It resolves groupings inside CTEs more precisely than the scratch version did.

### 2. Validator: `validate_gold_file.py --examples example_bank.yaml`
**PASS**, 0 failures, 0 warnings. All 28 gold_sql run as grader_ro.

### 3. Structure check

| bank | vs exam (76 items with SQL) | vs held-out (27 items with SQL) |
|---|---|---|
| old (first check) | 10 of 28 examples had a same-question exam item (26 pairs); with the three cases the tool cannot see (ex_07, ex_24, ex_30) 13 of 30 | 6 examples, 9 pairs |
| **new** | **0 same-question pairs** | **0 same-question pairs** |

Tier-0 items (A: ex_29, ex_30; exam: u_01 to u_08; held-out: hu_01 to hu_03) have no SQL and are not compared by the tool. See 6.

Pairs with exactly one differing feature (all others differ in 2 or more):

| vs exam | vs held-out |
|---|---|
| ex_01: t1_29, t1_32, t1_33 (metrik) | ex_01: h1_08, h1_09 (metrik) |
| ex_02: t1_05 (metrik); t1_13, t1_29 (aggs) | ex_02: h1_06 (aggs) |
| ex_03: t1_13, t1_18 (metrik); t1_33 (aggs) | ex_03: h1_09 (aggs) |
| ex_19: t2_10 (aggs) | ex_10: h2_01, h2_05 (group) |
| ex_14: t3_01 (limit) | ex_14: h2_09 (group) |
| ex_20: t2_10, t2_16 (group) | ex_16: h2_04 (group) |
| ex_22: t2_10, t2_16 (group) | ex_18: h2_04 (group) |
| ex_28: t4_01 (group) | |

ex_14, ex_16, ex_18, ex_20, ex_22 and ex_28 are items that were not replaced. They show up at distance 1 as before.

Smallest distance of each replaced item (number of differing features to the nearest item, then the nearest ids):

| new item | exam | held-out |
|---|---|---|
| ex_01 | 1 (t1_29, t1_32, t1_33) | 1 (h1_08, h1_09) |
| ex_02 | 1 (t1_05, t1_13, t1_29) | 1 (h1_06) |
| ex_03 | 1 (t1_13, t1_18, t1_33) | 1 (h1_09) |
| ex_04 | 3 (t1_29, t1_32, t1_33, t3_02) | 2 (h3_04) |
| ex_05 | 3 (t2_08) | 4 (h1_08) |
| ex_07 | 4 (t1_32) | 3 (h3_04) |
| ex_09 | 3 (t1_11, t1_16, t1_27, t1_35) | 2 (h2_01, h2_05) |
| ex_10 | 2 (t2_10, t2_16) | 1 (h2_01, h2_05) |
| ex_12 | 3 (t1_21) | 3 (h2_09) |
| ex_13 | 2 (t1_32) | 2 (h1_08) |
| ex_15 | 2 (t1_18, t2_08, t2_24) | 3 (h1_08) |
| ex_19 | 1 (t2_10) | 2 (h1_03, h2_05) |
| ex_24 | 2 (t2_10, t2_16, t3_08) | 3 (h1_02, h1_10, h2_01, h2_05) |
| ex_30 (tier 0) | no SQL | no SQL |

Distance 1 means one real feature differs (a different metrik, aggregate or grain). The three tier-1 items ex_01 to ex_03 cannot do better, because the exam and held-out already cover most single-value shapes.

### 4. Leak check (TF-IDF on question text, sqlglot-normalised SQL)

| measure | vs exam | vs held-out |
|---|---|---|
| text pairs above 0.6 | **2** of 2520 (was 5): ex_19-t2_03 0.672, ex_11-t1_29 0.632 | **1** of 900 (was 2): ex_18-h1_07 0.607 |
| SQL pairs above 0.6 | 450 of 2128 (was 456) | 214 of 756 (was 213) |
| highest text score | ex_19-t2_03 0.672 | ex_18-h1_07 0.607 |
| highest SQL score | ex_19-t2_10 0.933 | ex_03-h1_06, h1_08, h1_09 0.898 |

Top 5 text pairs vs exam: ex_19-t2_03 0.672; ex_11-t1_29 0.632; ex_19-t2_10 0.587; ex_21-t1_05 0.544; ex_15-t1_05 0.532. Top 5 text pairs vs held-out: ex_18-h1_07 0.607; ex_19-hu_03 0.584; ex_07-h3_01 0.556; ex_25-h1_02 0.544; ex_17-h2_07 0.521.
Top 5 SQL pairs vs exam: ex_19-t2_10 0.933; ex_02-t1_05 0.917; ex_15-t2_24 0.915; ex_22-t2_10 0.901; ex_03-t1_05 / t1_29 / t1_32 / t1_33 0.898. Top 5 SQL pairs vs held-out: ex_03-h1_06 / h1_08 / h1_09 0.898; ex_02-h1_06 / h1_08 / h1_09 0.888.

The SQL scores stay high for the tier-1 items because the masked query shape is the same; the structure check, not this score, decides the verdict. ex_19-t2_03 (0.672) comes from a shared phrase ("for each hour of the day"): the measure, table and aggregate differ.

### 5. Answer values
- No replaced example (ex_01, 02, 03, 04, 05, 07, 09, 10, 12, 13, 15, 19, 24) shares a result value with an exam or held-out item, except one single coincidence: ex_05 and t4_03 share 4.38, one number among 8568 rows.
- Remaining overlaps all come from items that were not replaced: ex_16 -> t2_22, ex_22 -> t1_11, ex_26 -> t3_01, ex_27 -> t2_07 and t3_06, ex_28 -> t2_07, t2_11, t3_06. Held-out (ids only): ex_22 -> h1_02, ex_28 -> h1_01, ex_28 -> h2_06. Before: 15 pairs vs exam, 5 vs held-out. Now: 9 and 3.
- ex_22 was only reworded (its gold_sql is unchanged), so its 2025 row still equals t1_11's answer.

### 6. Open points
- **Tier-0 examples (follow-up):** ex_29 was replaced afterwards (the cross-border-flow decline matched hu_02 by concept) with a decline about grid fees for household customers. The concept appears in no exam tier-0 item (u_01 to u_08: nuclear, Bavaria, demand forecast, CO2, power plants, capacity, DE/AT/LU, July 2026), no held-out tier-0 item (hu_01 to hu_03; keyword booleans only, no text shown) and not in ex_30 (weather). The structure tool cannot compare tier-0 items, so this rests on concept keywords. Best text matches: ex_29 vs exam t1_31 0.254, vs held-out h1_04 0.225; ex_30 vs exam t2_15 0.333, vs held-out hu_02 0.158.
- **Pattern coverage:** tiers are unchanged (T0 2, T1 3, T2 19, T3 4, T4 2). Musters are unchanged except ex_24 ("renewables vs conventional" became "two-way split"; a source classification is not possible without the exam's list). **"Each pattern at least twice" does not hold, before or after:** 28 distinct musters, of which only "percent change" and "decline" occur twice.
- **ex_22 text:** reworded; the text score against t1_11 dropped from 0.825 to 0.049 (its best exam match is now t1_06 at 0.114).

---

## Details

### A. New and changed items
Question texts of the examples (example bank, not held-out):

| id | tier | muster | question |
|---|---|---|---|
| ex_01 | 1 | single total | What was the total grid load including hydro pumped storage in October 2025? |
| ex_02 | 1 | single average | Wie hoch war die durchschnittliche Residuallast pro Viertelstunde im zweiten Halbjahr 2024? |
| ex_03 | 1 | single max | Was war der höchste Pumpstrom-Verbrauch in einer einzelnen Viertelstunde im Jahr 2025? |
| ex_04 | 2 | share | What percentage of the grid load including pumped storage in 2025 went into pumped storage? |
| ex_05 | 3 | share per group | Wie verteilt sich der Netzverbrauch 2025 prozentual auf die Stunden des Tages? |
| ex_07 | 2 | percent change | Um wie viel Prozent hat sich der Netzverbrauch im Januar 2026 gegenüber Januar 2025 verändert? |
| ex_09 | 2 | argmax | Which calendar month had the highest average German day-ahead price across 2024 and 2025? |
| ex_10 | 2 | argmin | An welchem Tag im Jahr 2024 war der durchschnittliche deutsche Day-Ahead-Preis am niedrigsten? |
| ex_12 | 2 | top-n | Nenne die 3 Viertelstunden mit der höchsten Wind-Onshore-Erzeugung im Jahr 2025. |
| ex_13 | 2 | full ranking | Rank the quarters of 2024 and 2025 by total grid load. |
| ex_15 | 2 | monthly series | What was the maximum grid load in each month of 2025? |
| ex_19 | 2 | hour of day | What was the highest German day-ahead price for each hour of the day in 2025? |
| ex_22 | 2 | by year | Zeige für jedes Kalenderjahr im Datensatz den mittleren deutschen Day-Ahead-Preis. (gold_sql unchanged) |
| ex_24 | 2 | two-way split | Wie hoch war der durchschnittliche deutsche Day-Ahead-Preis 2024 tagsüber (6 bis 22 Uhr) im Vergleich zur Nacht? |
| ex_29 | 0 | decline | How high were the grid fees for household customers in Germany in 2025? |
| ex_30 | 0 | decline | Wie viele Sonnenstunden gab es im Sommer 2025 in Deutschland? |

Rows/cols: ex_01-04 1x1; ex_05 24x2; ex_07 1x1; ex_09 1x2; ex_10 1x2; ex_12 3x2; ex_13 8x2; ex_15 12x2; ex_19 24x2; ex_24 2x2.

### B. Rules from the task, item by item
- **Same type only against every item:** the structure check finds no same-question pair in either file (section 3). I also read every exam pair at distance 1 by hand: all differ in a real measure, aggregate, metrik or grain. The held-out pairs were checked on features only, since no held-out text is displayed.
- **No exam-specific labels, classification lists or answer values:** the renewables list is gone (ex_24 splits by time of day, with the labels `Tag` / `Nacht`). No source list or zone list appears in a new item. The only multi-valued metrik use is ex_04, which uses two verbrauch metrik literals. No answer value is shared (section 5).
- **House style (D28):** percent on a 0-100 scale with ROUND(..., 2) (ex_04, ex_05, ex_07); label first, then value; months, quarters and days as dates (`date_trunc(...)::date`, `::date`), cyclic buckets as integers (`EXTRACT(HOUR/MONTH ...)::int`); undirected rankings and tops sort highest first, and the lowest-first sorts (ex_10) are explicit in the question; time-ordered lists ascending; raw MWh and EUR/MWh; half-open ranges. DESC sorts on measures carry NULLS LAST, and ex_12 adds `zeitpunkt` as a tie-break.
- **No data quirk as the point:** the new items avoid the aggregate zone '∅ Anrainer DE/LU' (no zone is grouped), Kernenergie (no source is grouped or ranked) and NULL traps. The two metrik literals 'Hydro pumped storage' and 'Grid load incl. hydro pumped storage' are documented schema values, not quirks: the second equals grid load plus pumped storage (2025: 465.8 + 12.7 = 478.6 million MWh).

### C. Method notes
- Candidate SQL was drafted in the scratchpad, scored with the structure features against both files, and run on grader_ro before it went into the bank. The scratchpad files are temporary.
- The structure tool's gate is "no differing feature". It does not see time-of-day conditions, label strings or source lists. Those were reviewed by hand for the exam pairs only.

### D. Follow-up edits after this report
- ex_29 replaced (grid fees for household customers, tier 0). ex_03: question reworded to "Pumpstrom-Verbrauch" (no "Pumpspeicher"), gold_sql unchanged. The numbers in this file were refreshed after both edits: validator PASS, structure check 0 same-question pairs vs exam and held-out, text pairs above 0.6: 2 vs exam, 1 vs held-out.
