# Analysis: did the quirk notes reach the prompt, and were they followed?

Generated 2026-10-24. Read-only: no OpenAI calls, no agent re-runs, no existing file modified. Only SELECTs against the database (as `grader_ro`).

## 0. Log format (so you can trust the parsing)

Each log (`*_t0_runN_2026-10-21.log`) has three sections, split on `=== ` header lines:
1. **Per-tier results** + `Overall` + `Valid-SQL rate`.
2. **Per-question table**, one line per question: `ID  Tier  [Retrieved tables]  PASS | FAIL (<comparator reason>)`. Schema-linked logs have the `Retrieved` column; naive logs do not. This is what I used for every PASS/FAIL.
3. **Failures**: one block per FAILED question only (`--- id (tier N) ---`, then `Question`, `Gold SQL`, `Agent SQL` (multi-line), `Reason`).

**Important limit:** the agent's SQL is stored **only for failed questions**. For a run where a question passed, the SQL is not in any log (checked `results/_stdout_*.txt` too, same). So 'did it use NULLS LAST' cannot be checked on a passing run.
Parsing sanity check: every run gives one per-question line per exam question and one failure block per FAIL line (naive r1: 84/39, naive r2: 84/37, naive r3: 84/38, schema r1: 84/38, schema r2: 84/36, schema r3: 84/38 lines/blocks), and the PASS counts reproduce the logged Overall totals (naive r1: 45, naive r2: 47, naive r3: 46, schema r1: 46, schema r2: 48, schema r3: 46).

## Part A: Did the quirk notes reach the prompt?

Rebuilt locally with `catalog_retriever.get_relevant_tables` + `prompt_template_schema_linked.build_prompt` (no API call).

| Question | Retriever selected | Needed note present? |
|---|---|---|
| t2_02 | ['erzeugung'] | Kernenergie NULL note: **YES** |
| t2_05 | ['erzeugung', 'verbrauch', 'preise'] | Kernenergie NULL note: **YES** |
| t2_22 | ['erzeugung', 'verbrauch', 'preise'] | Kernenergie NULL note: **YES** |
| t2_06 | ['preise'] | DE/AT/LU empty-zone note: **YES** |
| t2_25 | ['preise'] | DE/AT/LU empty-zone note: **YES** |

Questions:
- t2_02: 'Rank all sources by total output in July 2025.'
- t2_05: 'What were the top 3 sources over the 2024/25 winter, December through February?'
- t2_22: 'On 21 June 2025, how much did each source produce? sorted highest first'
- t2_06: 'Which price zone had the highest average price over the whole period?'
- t2_25: 'Rank the neighbouring countries by their average price in 2025.'

Exact note text found in the prompts (as rendered after the `•` bullet):

Kernenergie note (erzeugung quirk #1):
```
Kernenergie is NULL after 2024-01-30, not zero. Use NULLS LAST on any ORDER BY ... DESC over this column, or Kernenergie sorts to the top incorrectly.
```
DE/AT/LU note (preise quirk #1):
```
DE/AT/LU is a valid preiszone value but is entirely empty (all NULL) for the whole dataset — exclude it from any aggregate with HAVING COUNT(preis_eur_mwh) > 0, or it will appear as a false extreme value.
```
Where in the prompt it sits (t2_05, first 40 lines of the erzeugung block shown is not needed; the note is the first bullet under 'Data quirks:' of its table).

Note: in the prompt, `Kernenergie is NULL after 2024-01-30` is text in a bullet list of 4 notes per table; the instruction at the end of the prompt (`Return exactly one PostgreSQL SELECT ...`) is unchanged and says nothing about the notes.

## Part B: Did the model follow the notes?

### B1. PASS/FAIL, 5 questions x 6 runs

| Question | naive r1 | naive r2 | naive r3 | schema r1 | schema r2 | schema r3 |
|---|---|---|---|---|---|---|
| t2_02 | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| t2_05 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| t2_22 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| t2_06 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| t2_25 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |

### B2. Agent SQL per question, and the note check

The log keeps SQL only for failures. 'not logged' = that run passed.


#### t2_02: Rank all sources by total output in July 2025.

Gold SQL:
```sql
SELECT energietraeger, SUM(mwh) AS mwh FROM erzeugung WHERE zeitpunkt >= '2025-07-01' AND zeitpunkt < '2025-08-01' GROUP BY energietraeger ORDER BY mwh DESC NULLS LAST;
```

**naive**: 1 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL is **identical** in all logged runs

Runs naive r1, naive r2, naive r3:
```sql
SELECT energietraeger, SUM(mwh) AS total_output
FROM erzeugung
WHERE zeitpunkt >= '2025-07-01' AND zeitpunkt < '2025-08-01'
GROUP BY energietraeger
ORDER BY total_output DESC;
```

**schema**: 2 distinct SQL variant(s) across logged runs; not logged (passed): schema r2; SQL **differs** between runs

Runs schema r1:
```sql
SELECT energietraeger, SUM(mwh) AS total_output
FROM erzeugung
WHERE zeitpunkt >= '2025-07-01' AND zeitpunkt < '2025-08-01'
GROUP BY energietraeger
ORDER BY total_output DESC
```

Runs schema r3:
```sql
SELECT energietraeger, SUM(mwh) AS total_output
FROM erzeugung
WHERE zeitpunkt >= '2025-07-01' AND zeitpunkt < '2025-08-01'
GROUP BY energietraeger
ORDER BY total_output DESC;
```

**Schema-linked note check:**

| Run | Result | Note followed? | Evidence |
|---|---|---|---|
| schema r1 | FAIL | **NO** | none of the accepted patterns found |
| schema r2 | PASS | n/a (SQL not logged) | passing implies result matched gold |
| schema r3 | FAIL | **NO** | none of the accepted patterns found |

#### t2_05: What were the top 3 sources over the 2024/25 winter, December through February?

Gold SQL:
```sql
SELECT energietraeger, SUM(mwh) AS mwh FROM erzeugung WHERE zeitpunkt >= '2024-12-01' AND zeitpunkt < '2025-03-01' GROUP BY energietraeger ORDER BY mwh DESC NULLS LAST LIMIT 3;
```

**naive**: 1 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL is **identical** in all logged runs

Runs naive r1, naive r2, naive r3:
```sql
SELECT energietraeger, SUM(mwh) AS total_mwh
FROM erzeugung
WHERE zeitpunkt >= '2024-12-01' AND zeitpunkt < '2025-03-01'
GROUP BY energietraeger
ORDER BY total_mwh DESC
LIMIT 3;
```

**schema**: 1 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL is **identical** in all logged runs

Runs schema r1, schema r2, schema r3:
```sql
SELECT energietraeger, SUM(mwh) AS total_mwh
FROM erzeugung
WHERE zeitpunkt >= '2024-12-01' AND zeitpunkt < '2025-03-01'
GROUP BY energietraeger
ORDER BY total_mwh DESC
LIMIT 3;
```

**Schema-linked note check:**

| Run | Result | Note followed? | Evidence |
|---|---|---|---|
| schema r1 | FAIL | **NO** | none of the accepted patterns found |
| schema r2 | FAIL | **NO** | none of the accepted patterns found |
| schema r3 | FAIL | **NO** | none of the accepted patterns found |

#### t2_22: On 21 June 2025, how much did each source produce? sorted highest first

Gold SQL:
```sql
SELECT energietraeger, SUM(mwh) AS mwh FROM erzeugung WHERE zeitpunkt >= '2025-06-21' AND zeitpunkt < '2025-06-22' GROUP BY energietraeger ORDER BY mwh DESC NULLS LAST;
```

**naive**: 1 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL is **identical** in all logged runs

Runs naive r1, naive r2, naive r3:
```sql
SELECT energietraeger, SUM(mwh) AS total_mwh
FROM erzeugung
WHERE zeitpunkt::date = '2025-06-21'
GROUP BY energietraeger
ORDER BY total_mwh DESC;
```

**schema**: 3 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL **differs** between runs

Runs schema r1:
```sql
SELECT 
    energietraeger, 
    SUM(mwh) AS total_mwh
FROM 
    erzeugung
WHERE 
    zeitpunkt >= '2025-06-21 00:00' 
    AND zeitpunkt < '2025-06-22 00:00'
GROUP BY 
    energietraeger
ORDER BY 
    total_mwh DESC;
```

Runs schema r2:
```sql
SELECT 
    energietraeger, 
    SUM(mwh) AS total_mwh
FROM 
    erzeugung
WHERE 
    zeitpunkt::date = '2025-06-21'
GROUP BY 
    energietraeger
ORDER BY 
    total_mwh DESC;
```

Runs schema r3:
```sql
SELECT 
    energietraeger, 
    SUM(mwh) AS total_mwh
FROM 
    erzeugung
WHERE 
    zeitpunkt >= '2025-06-21 00:00:00' 
    AND zeitpunkt < '2025-06-22 00:00:00'
GROUP BY 
    energietraeger
ORDER BY 
    total_mwh DESC;
```

**Schema-linked note check:**

| Run | Result | Note followed? | Evidence |
|---|---|---|---|
| schema r1 | FAIL | **NO** | none of the accepted patterns found |
| schema r2 | FAIL | **NO** | none of the accepted patterns found |
| schema r3 | FAIL | **NO** | none of the accepted patterns found |

#### t2_06: Which price zone had the highest average price over the whole period?

Gold SQL:
```sql
SELECT preiszone, AVG(preis_eur_mwh) AS eur_mwh FROM preise GROUP BY preiszone HAVING COUNT(preis_eur_mwh) > 0 ORDER BY eur_mwh DESC LIMIT 1;
```

**naive**: 2 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL **differs** between runs

Runs naive r1:
```sql
SELECT preiszone
FROM preise
GROUP BY preiszone
ORDER BY AVG(preis_eur_mwh) DESC
LIMIT 1;
```

Runs naive r2, naive r3:
```sql
SELECT preiszone, AVG(preis_eur_mwh) AS avg_price
FROM preise
GROUP BY preiszone
ORDER BY avg_price DESC
LIMIT 1;
```

**schema**: 1 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL is **identical** in all logged runs

Runs schema r1, schema r2, schema r3:
```sql
SELECT preiszone
FROM preise
WHERE preiszone != 'DE/AT/LU'
GROUP BY preiszone
HAVING COUNT(preis_eur_mwh) > 0
ORDER BY AVG(preis_eur_mwh) DESC
LIMIT 1;
```

**Schema-linked note check:**

| Run | Result | Note followed? | Evidence |
|---|---|---|---|
| schema r1 | FAIL | **YES** | excludes DE/AT/LU explicitly, HAVING COUNT(preis_eur_mwh) > 0 |
| schema r2 | FAIL | **YES** | excludes DE/AT/LU explicitly, HAVING COUNT(preis_eur_mwh) > 0 |
| schema r3 | FAIL | **YES** | excludes DE/AT/LU explicitly, HAVING COUNT(preis_eur_mwh) > 0 |

#### t2_25: Rank the neighbouring countries by their average price in 2025.

Gold SQL:
```sql
SELECT preiszone, AVG(preis_eur_mwh) AS eur_mwh
FROM preise
WHERE zeitpunkt >= '2025-01-01' AND zeitpunkt < '2026-01-01'
  AND preiszone NOT IN ('Deutschland/Luxemburg', 'DE/AT/LU', '∅ Anrainer DE/LU')
GROUP BY preiszone HAVING COUNT(preis_eur_mwh) > 0
ORDER BY eur_mwh DESC;
```

**naive**: 1 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL is **identical** in all logged runs

Runs naive r1, naive r2, naive r3:
```sql
SELECT preiszone, AVG(preis_eur_mwh) AS avg_price
FROM preise
WHERE preiszone IN ('Belgien', 'Dänemark 1', 'Dänemark 2', 'Frankreich', 'Niederlande', 'Norwegen 2', 'Österreich', 'Polen', 'Schweden 4', 'Schweiz', 'Tschechien', 'Italien (Nord)', 'Slowenien', 'Ungarn')
  AND EXTRACT(YEAR FROM zeitpunkt) = 2025
GROUP BY preiszone
ORDER BY avg_price;
```

**schema**: 2 distinct SQL variant(s) across logged runs; all 3 runs logged; SQL **differs** between runs

Runs schema r1:
```sql
SELECT preiszone, AVG(preis_eur_mwh) AS avg_price
FROM preise
WHERE EXTRACT(YEAR FROM zeitpunkt) = 2025
  AND preiszone IN ('∅ Anrainer DE/LU', 'Belgien', 'Dänemark 1', 'Dänemark 2', 'Frankreich', 'Niederlande', 'Norwegen 2', 'Österreich', 'Polen', 'Schweden 4', 'Schweiz', 'Tschechien', 'Italien (Nord)', 'Slowenien', 'Ungarn')
GROUP BY preiszone
HAVING COUNT(preis_eur_mwh) > 0
ORDER BY avg_price;
```

Runs schema r2, schema r3:
```sql
SELECT preiszone, AVG(preis_eur_mwh) AS avg_price
FROM preise
WHERE EXTRACT(YEAR FROM zeitpunkt) = 2025
  AND preiszone IN ('∅ Anrainer DE/LU', 'Belgien', 'Dänemark 1', 'Dänemark 2', 'Frankreich', 'Niederlande', 'Norwegen 2', 'Österreich', 'Polen', 'Schweden 4', 'Schweiz', 'Tschechien', 'Italien (Nord)', 'Slowenien', 'Ungarn')
GROUP BY preiszone
HAVING COUNT(preis_eur_mwh) > 0
ORDER BY avg_price DESC;
```

**Schema-linked note check:**

| Run | Result | Note followed? | Evidence |
|---|---|---|---|
| schema r1 | FAIL | **YES** | HAVING COUNT(preis_eur_mwh) > 0, explicit IN-list that omits DE/AT/LU |
| schema r2 | FAIL | **YES** | HAVING COUNT(preis_eur_mwh) > 0, explicit IN-list that omits DE/AT/LU |
| schema r3 | FAIL | **YES** | HAVING COUNT(preis_eur_mwh) > 0, explicit IN-list that omits DE/AT/LU |

### B3. For each FAIL where the note WAS followed: what else went wrong

- **t2_06 / schema r1**: followed via excludes DE/AT/LU explicitly, HAVING COUNT(preis_eur_mwh) > 0. Comparator: `column count mismatch at row 0: gold=2 agent=1`
- **t2_06 / schema r2**: followed via excludes DE/AT/LU explicitly, HAVING COUNT(preis_eur_mwh) > 0. Comparator: `column count mismatch at row 0: gold=2 agent=1`
- **t2_06 / schema r3**: followed via excludes DE/AT/LU explicitly, HAVING COUNT(preis_eur_mwh) > 0. Comparator: `column count mismatch at row 0: gold=2 agent=1`
- **t2_25 / schema r1**: followed via HAVING COUNT(preis_eur_mwh) > 0, explicit IN-list that omits DE/AT/LU. Comparator: `row count mismatch: gold=14 agent=15`
- **t2_25 / schema r2**: followed via HAVING COUNT(preis_eur_mwh) > 0, explicit IN-list that omits DE/AT/LU. Comparator: `row count mismatch: gold=14 agent=15`
- **t2_25 / schema r3**: followed via HAVING COUNT(preis_eur_mwh) > 0, explicit IN-list that omits DE/AT/LU. Comparator: `row count mismatch: gold=14 agent=15`



**What else went wrong where the note WAS followed (one sentence each):**

- **t2_06 (all 3 schema-linked runs):** the note was followed twice over (`WHERE preiszone != 'DE/AT/LU'` and `HAVING COUNT(preis_eur_mwh) > 0`), but the query returns only `preiszone` while the gold returns `preiszone, AVG(...)`, so the comparator stops at `column count 2 vs 1` (whether the zone itself was right was never checked by the grader).
- **t2_25 (all 3 schema-linked runs):** the note was followed (`HAVING COUNT(...) > 0` plus an IN-list without DE/AT/LU), but the IN-list includes `'∅ Anrainer DE/LU'` (an average-of-neighbours zone, not a country) that the gold excludes, giving 15 rows instead of 14; run 1 also sorts ascending, so it would fail on order too. No note covers the `∅ Anrainer DE/LU` zone.

**Evidence that the DE/AT/LU note did change behaviour:** in the naive runs, t2_06 run 2 failed with `agent='DE/AT/LU'` (the trap fired: a NULL average sorts first under DESC). In all three schema-linked runs that trap no longer fires.

**Evidence that the Kernenergie note changed nothing:** t2_05 schema-linked SQL is byte-for-byte the same query as the naive SQL (same ORDER BY ... DESC, no NULLS LAST), in all 3 runs of both setups.

**Caveat on t2_02 schema r2 (1 pass out of 9 schema-linked Kernenergie-question runs):** its SQL is not stored in the log, so I cannot say whether it used NULLS LAST. The wording of my check list (IS NOT NULL / COALESCE / excluding Kernenergie) was applied only to the 8 failing schema-linked runs, and none matched.



## Part C: What do all failures look like?

Categories, checked in your order: sql_error, no_sql, wrong_column_count, wrong_row_count, wrong_values.
**Two deviations, both needed to be exact:**
1. The comparator checks row count *before* column count, so a log reason of 'row count mismatch' can hide a column-count difference. To follow your order, for every 'row count mismatch' failure I re-ran the stored agent SQL and the gold SQL (read-only SELECTs) and compared column counts. Reclassified cases are listed below.
2. Tier 0 failures ('agent returned SQL when it should have declined') fit none of your five categories, because the grader never executes SQL for tier 0. I put them in a sixth bucket, `tier0_should_have_declined`, and also show totals without it.

### C1. Count table (mean of 3 runs)

| Category | naive (mean) | schema-linked (mean) | naive r1/r2/r3 | schema r1/r2/r3 |
|---|---|---|---|---|
| sql_error | 0.67 | 3.33 | 0/1/1 | 4/3/3 |
| no_sql | 0.00 | 0.00 | 0/0/0 | 0/0/0 |
| wrong_column_count | 13.33 | 11.33 | 15/12/13 | 11/11/12 |
| wrong_row_count | 1.33 | 3.00 | 2/1/1 | 3/3/3 |
| wrong_values | 14.67 | 11.67 | 14/15/15 | 12/11/12 |
| tier0_should_have_declined | 8.00 | 8.00 | 8/8/8 | 8/8/8 |
| **total failures** | 38.00 | 37.33 | 39/37/38 | 38/36/38 |
| failures excluding tier 0 | 30.00 | 29.33 | | |

### C2. Cases reclassified by re-running SQL (row-count log reason, but column count also differs)

- naive r1 / t2_17: rows gold=12 agent=1263600; cols gold=2 agent=3
- naive r1 / t2_21: rows gold=16 agent=17; cols gold=2 agent=1
- naive r1 / t4_03: rows gold=8568 agent=0; cols gold=4 agent=1
- naive r2 / t2_21: rows gold=16 agent=17; cols gold=2 agent=1
- naive r2 / t3_06: rows gold=1 agent=2; cols gold=4 agent=2
- naive r2 / t4_03: rows gold=8568 agent=0; cols gold=4 agent=1
- naive r3 / t2_21: rows gold=16 agent=17; cols gold=2 agent=1
- naive r3 / t3_06: rows gold=1 agent=2; cols gold=4 agent=5
- naive r3 / t4_03: rows gold=8568 agent=0; cols gold=4 agent=1
- schema r1 / t3_06: rows gold=1 agent=2; cols gold=4 agent=2
- schema r1 / t4_03: rows gold=8568 agent=0; cols gold=4 agent=1
- schema r2 / t3_06: rows gold=1 agent=2; cols gold=4 agent=2
- schema r2 / t4_03: rows gold=8568 agent=0; cols gold=4 agent=1
- schema r3 / t3_06: rows gold=1 agent=2; cols gold=4 agent=2
- schema r3 / t4_03: rows gold=8568 agent=0; cols gold=4 agent=1

### C3. Stable vs flaky failures

**Stable failures (fail in all 6 runs): 34**

t1_02, t1_32, t2_05, t2_06, t2_07, t2_09, t2_12, t2_14, t2_15, t2_18, t2_20, t2_22, t2_25, t3_03, t3_04, t3_06, t3_07, t3_08, t3_09, t3_10, t3_11, t3_12, t4_01, t4_02, t4_03, t4_04, u_01, u_02, u_03, u_04, u_05, u_06, u_07, u_08

Of those, tier 0 (IDs `u_01`..`u_08`): 8 (u_01, u_02, u_03, u_04, u_05, u_06, u_07, u_08). Non-tier-0 stable failures: 26.

Stable failures by category (category in schema-linked run 1):

wrong_column_count: 8, wrong_values: 11, wrong_row_count: 3, sql_error: 4, tier0_should_have_declined: 8

**Flaky (fail in some runs, not all): 6**

| Question | naive r1 r2 r3 | schema r1 r2 r3 |
|---|---|---|
| t1_10 | F P F | P P P |
| t1_18 | F F F | F P P |
| t2_01 | P P P | F F F |
| t2_02 | F F F | F P F |
| t2_17 | F P P | F P F |
| t2_21 | F F F | P F F |

Never failed: 44 questions.

## Part D: metrik and preiszone labels, database vs code

Queries run (read-only):
```sql
SELECT DISTINCT metrik FROM verbrauch ORDER BY 1;
SELECT DISTINCT preiszone FROM preise ORDER BY 1;
-- extra, same idea:
SELECT DISTINCT energietraeger FROM erzeugung ORDER BY 1;
```
Database values (repr, so hidden whitespace or odd characters would show):

- metrik (4): 'grid load', 'Grid load incl. hydro pumped storage', 'Hydro pumped storage', 'Residual load'
- preiszone (17): '∅ Anrainer DE/LU', 'Belgien', 'Dänemark 1', 'Dänemark 2', 'DE/AT/LU', 'Deutschland/Luxemburg', 'Frankreich', 'Italien (Nord)', 'Niederlande', 'Norwegen 2', 'Österreich', 'Polen', 'Schweden 4', 'Schweiz', 'Slowenien', 'Tschechien', 'Ungarn'
- energietraeger (12): 'Biomasse', 'Braunkohle', 'Erdgas', 'Kernenergie', 'Photovoltaik', 'Pumpspeicher', 'Sonstige Erneuerbare', 'Sonstige Konventionelle', 'Steinkohle', 'Wasserkraft', 'Wind Offshore', 'Wind Onshore'

### D1. prompt_template.py (naive prompt) and D2. schema_catalog.py

- prompt_template.py / metrik: **exact match** (4 values, character for character)
- prompt_template.py / preiszone: **exact match** (17 values, character for character)
- prompt_template.py / energietraeger: **exact match** (12 values, character for character)
- schema_catalog.py / metrik: **exact match** (4 values, character for character)
- schema_catalog.py / preiszone: **exact match** (17 values, character for character)
- schema_catalog.py / energietraeger: **exact match** (12 values, character for character)

### D3. Literals in gold_set_smard.yaml (gold_sql of all 84 questions)

- metrik: 3 distinct literal(s) used in gold SQL; **all exist exactly in the DB**
- preiszone: 6 distinct literal(s) used in gold SQL; **all exist exactly in the DB**
- energietraeger: 11 distinct literal(s) used in gold SQL; **all exist exactly in the DB**
- Case/Unicode near-misses anywhere in gold SQL (literal that equals a DB label only after case-folding): none

**Total mismatches found in Part D: 0**

## Summary (5 lines)

1. **Reason 1 (note not in prompt) is ruled out for all 5 questions:** the retriever selected a table set containing the needed table every time, and the exact Kernenergie and DE/AT/LU note text is present in each rebuilt prompt.
2. **Kernenergie note (t2_02, t2_05, t2_22) = reason 2, in the prompt but ignored:** none of the 8 failing schema-linked SQLs uses NULLS LAST, IS NOT NULL, COALESCE or excludes Kernenergie; t2_05's SQL is identical to the naive one; the one pass (t2_02 r2) has no stored SQL.
3. **DE/AT/LU note (t2_06, t2_25) = reason 3, followed but other failures dominate:** followed in 6 of 6 runs (and it removed the naive DE/AT/LU trap), yet both questions still fail on output shape (t2_06: 1 column instead of 2) or an unrelated wrong row (t2_25: includes `∅ Anrainer DE/LU`).
4. **Overall failures barely moved (naive 38.0 vs schema-linked 37.3 per run);** 8 are tier 0 in every run, and of the other ~30, wrong_values (~12-15) and wrong_column_count (~11-13) dominate; 26 non-tier-0 questions fail in all 6 runs, while SQL errors rose from 0.7 to 3.3 per run with the catalog.
5. **Part D found 0 label mismatches:** the 4 metrik, 17 preiszone and 12 energietraeger values in the database match prompt_template.py and schema_catalog.py exactly (including `∅` and umlauts), and every metrik/preiszone/energietraeger literal in the 84 gold SQLs exists in the DB exactly.
