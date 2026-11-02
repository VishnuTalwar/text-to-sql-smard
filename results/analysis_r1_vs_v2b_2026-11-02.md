# Row R1 (error retry on top of v2b) vs v2b, 2026-11-02

Sources: `results/r1_run{1,2,3}_2026-11-02.jsonl` and `results/v2b_t0_run{1,2,3}_2026-10-27.jsonl`; prediction and amendment in `results/r1_prediction_2026-11-01.md`. Same exam (84 questions), gpt-4o, temperature 0, seed 0, v2b prompt on attempt 1, at most 3 attempts.

**Headline:** the retry did almost nothing and gained nothing. It fired on 4 of 252 questions (1.6%); in all 4 the corrected SQL ran, and in all 4 it was still wrong (0 pass after retry). Mean score 59.33/84 against v2b's 60.67 (-1.33, inside the noise). All 5 questions whose pass count changed were never retried, so the difference comes from attempt 1 giving different replies to the same prompt, not from the loop.

## 1. Scores (passed questions out of 84; tiers: t0=8, t1=35, t2=25, t3=12, t4=4)

| Row | Run | Total | T0 | T1 | T2 | T3 | T4 |
|---|---|---:|---:|---:|---:|---:|---:|
| R1 | run 1 | 58 | 7 | 33 | 15 | 3 | 0 |
| R1 | run 2 | 59 | 7 | 34 | 16 | 2 | 0 |
| R1 | run 3 | 61 | 7 | 34 | 17 | 3 | 0 |
| **R1** | **mean** | **59.33** | **7.00** | **33.67** | **16.00** | **2.67** | **0.00** |
| v2b | run 1 | 60 | 7 | 34 | 17 | 2 | 0 |
| v2b | run 2 | 61 | 7 | 34 | 18 | 2 | 0 |
| v2b | run 3 | 61 | 7 | 34 | 18 | 2 | 0 |
| **v2b** | **mean** | **60.67** | **7.00** | **34.00** | **17.67** | **2.00** | **0.00** |

Mean total difference R1 minus v2b: -1.33. Noise on this exam is about 2 to 4 points per run.

## 2. Loop numbers per run

| Run | Retry rate | Mean attempts | Crashed on attempt 1 | SQL runs at the end | Pass after retry | Declined after error | Cap hits |
|---|---|---:|---|---:|---:|---:|---:|
| run 1 | 1/84 (1.2%) | 1.012 | 1 ['t4_04'] | 1 | 0 | 0 | 0 |
| run 2 | 1/84 (1.2%) | 1.012 | 1 ['t4_04'] | 1 | 0 | 0 | 0 |
| run 3 | 2/84 (2.4%) | 1.036 | 2 ['t4_02', 't4_04'] | 2 | 0 | 0 | 0 |
| **all 3** | **4/252 (1.6%)** | **1.020** | **4** | **4** | **0** | **0** | **0** |

For comparison, v2b had these SQL crashes in its 3 runs (5 in total): run 1: t4_02, t4_04; run 2: t4_04; run 3: t4_02, t4_04.

## 3. Every retried question

### Run 1, t4_04 (tier 4): What was the longest run of consecutive quarter-hours with a negative German price?

Attempt 1 (error: `column "consecutive_count" does not exist`):
```sql
SELECT MAX(consecutive_count) AS longest_negative_run
FROM (
  SELECT zeitpunkt, 
         preiszone, 
         preis_eur_mwh, 
         ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
         ROW_NUMBER() OVER (PARTITION BY preis_eur_mwh < 0 ORDER BY zeitpunkt) AS grp
  FROM preise
  WHERE preiszone = 'Deutschland/Luxemburg'
) subquery
WHERE preis_eur_mwh < 0
GROUP BY grp
ORDER BY longest_negative_run DESC
LIMIT 1;
```
Attempt 2 (ran without error):
```sql
SELECT MAX(run_length) AS longest_negative_run
FROM (
  SELECT COUNT(*) AS run_length
  FROM (
    SELECT zeitpunkt, 
           preiszone, 
           preis_eur_mwh, 
           ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
           ROW_NUMBER() OVER (PARTITION BY preis_eur_mwh < 0 ORDER BY zeitpunkt) AS grp
    FROM preise
    WHERE preiszone = 'Deutschland/Luxemburg'
  ) subquery
  WHERE preis_eur_mwh < 0
  GROUP BY grp
) final_subquery;
```
**Final answer: FAIL**, SQL runs, wrong column count (gold=4 agent=1).

### Run 2, t4_04 (tier 4): What was the longest run of consecutive quarter-hours with a negative German price?

Attempt 1 (error: `column "consecutive_count" does not exist`):
```sql
SELECT MAX(consecutive_count) AS longest_negative_run
FROM (
  SELECT zeitpunkt, 
         preiszone, 
         preis_eur_mwh, 
         ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
         ROW_NUMBER() OVER (PARTITION BY (preis_eur_mwh < 0) ORDER BY zeitpunkt) AS grp
  FROM preise
  WHERE preiszone = 'Deutschland/Luxemburg'
) subquery
WHERE preis_eur_mwh < 0
GROUP BY grp
ORDER BY longest_negative_run DESC
LIMIT 1;
```
Attempt 2 (ran without error):
```sql
SELECT MAX(run_length) AS longest_negative_run
FROM (
  SELECT COUNT(*) AS run_length
  FROM (
    SELECT zeitpunkt, 
           preiszone, 
           preis_eur_mwh, 
           ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
           ROW_NUMBER() OVER (PARTITION BY (preis_eur_mwh < 0) ORDER BY zeitpunkt) AS grp
    FROM preise
    WHERE preiszone = 'Deutschland/Luxemburg'
  ) subquery
  WHERE preis_eur_mwh < 0
  GROUP BY grp
) final_subquery;
```
**Final answer: FAIL**, SQL runs, wrong column count (gold=4 agent=1).

### Run 3, t4_02 (tier 4): What was the longest unbroken stretch where solar output was zero?

Attempt 1 (error: `column "zero_stretch" does not exist`):
```sql
SELECT MAX(zero_stretch) FROM (
  SELECT zeitpunkt, 
         ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
         ROW_NUMBER() OVER (PARTITION BY (mwh = 0) ORDER BY zeitpunkt) AS grp
  FROM erzeugung
  WHERE energietraeger = 'Photovoltaik'
) subquery
WHERE mwh = 0
GROUP BY grp;
```
Attempt 2 (error: `column "mwh" does not exist`):
```sql
SELECT MAX(count) FROM (
  SELECT COUNT(*) AS count
  FROM (
    SELECT zeitpunkt, 
           ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
           ROW_NUMBER() OVER (PARTITION BY (mwh = 0) ORDER BY zeitpunkt) AS grp
    FROM erzeugung
    WHERE energietraeger = 'Photovoltaik'
  ) subquery
  WHERE mwh = 0
  GROUP BY grp
) AS stretches;
```
Attempt 3 (ran without error):
```sql
SELECT MAX(count) FROM (
  SELECT COUNT(*) AS count
  FROM (
    SELECT zeitpunkt, 
           ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
           ROW_NUMBER() OVER (PARTITION BY (mwh IS NULL OR mwh = 0) ORDER BY zeitpunkt) AS grp,
           mwh
    FROM erzeugung
    WHERE energietraeger = 'Photovoltaik'
  ) subquery
  WHERE mwh IS NULL OR mwh = 0
  GROUP BY grp
) AS stretches;
```
**Final answer: FAIL**, SQL runs, wrong column count (gold=4 agent=1).

### Run 3, t4_04 (tier 4): What was the longest run of consecutive quarter-hours with a negative German price?

Attempt 1 (error: `column "consecutive_intervals" does not exist`):
```sql
SELECT MAX(consecutive_intervals) AS longest_negative_run
FROM (
  SELECT zeitpunkt, 
         preis_eur_mwh, 
         ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
         ROW_NUMBER() OVER (PARTITION BY (preis_eur_mwh < 0) ORDER BY zeitpunkt) AS grp
  FROM preise
  WHERE preiszone = 'Deutschland/Luxemburg'
) subquery
WHERE preis_eur_mwh < 0
GROUP BY grp
ORDER BY longest_negative_run DESC
LIMIT 1;
```
Attempt 2 (ran without error):
```sql
SELECT MAX(count) AS longest_negative_run
FROM (
  SELECT COUNT(*) AS count
  FROM (
    SELECT zeitpunkt, 
           preis_eur_mwh, 
           ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
           ROW_NUMBER() OVER (PARTITION BY (preis_eur_mwh < 0) ORDER BY zeitpunkt) AS grp
    FROM preise
    WHERE preiszone = 'Deutschland/Luxemburg'
  ) subquery
  WHERE preis_eur_mwh < 0
  GROUP BY grp
) final_subquery;
```
**Final answer: FAIL**, SQL runs, wrong column count (gold=4 agent=1).

## 4. Questions whose pass count changed (v2b to R1)

| id | Tier | v2b | R1 | Change | Retried in R1 | Marking |
|---|---:|---:|---:|---:|---|---|
| t2_06 | 2 | 2/3 | 0/3 | -2 | none | run-to-run noise |
| t2_12 | 2 | 3/3 | 1/3 | -2 | none | run-to-run noise |
| t3_06 | 3 | 0/3 | 2/3 | +2 | none | run-to-run noise |
| t1_12 | 1 | 3/3 | 2/3 | -1 | none | run-to-run noise |
| t2_09 | 2 | 3/3 | 2/3 | -1 | none | run-to-run noise |

5 questions changed; net -4 passes over 3 runs.

Every change is on a question that was never retried, so none of them is caused by the loop. Notes:
- **t2_06 (-2):** R1 answered with only `preiszone` (1 column, gold has 2) in 3/3 runs; v2b did the same in run 1 and added the `AVG` column in runs 2 and 3.
- **t2_12 (-2):** R1 runs 1 and 2 used `EXTRACT(DOW ...)` (a number) instead of `TO_CHAR(zeitpunkt, 'Day')` (the name) that v2b used 3/3.
- **t3_06 (+2):** R1 runs 1 and 3 returned one row with `CASE` sums (gold shape); v2b returned two rows with `UNION ALL` 3/3.
- **t1_12 (-1):** R1 run 1 declined ("Data for February 2026 is not available."), a false decline; v2b had none.
- **t2_09 (-1):** R1 run 1 used `TO_CHAR(zeitpunkt, 'YYYY-MM')` (text) instead of `DATE_TRUNC('month', ...)` (date).

**Why the same prompt gives different replies.** Attempt 1 is the same prompt as v2b (84/84 identical offline), but the reply text (fences and whitespace ignored) is identical to v2b's reply for the same question and run number in only 154 of 252 cases (61%). Between two runs of the same row it is identical in 59 to 65 of 84 (70 to 77%), for v2b and R1 alike. Temperature 0 and seed 0 therefore do not make the model deterministic. The cross-row figure (61%) is somewhat lower than the within-row figures (about 75%); that might be drift of the model behind `gpt-4o` between 27 October and 2 November, but the logs do not record a model fingerprint, so I cannot tell. Net effect on the score here: -1.33 against a run-to-run spread of 58 to 61.


## 5. Latency, tokens, cost (per question)

| Row | p50 / p95 model only (s) | p50 / p95 with SQL checks (s) | Mean model latency (s) | Prompt tokens | Completion tokens | Cost (USD) |
|---|---:|---|---:|---:|---:|---:|
| R1 run 1 | 1.047 / 1.736 | 1.107 / 1.860 | 1.128 | 637.6 | 60.2 | 0.00220 |
| R1 run 2 | 1.054 / 1.748 | 1.090 / 1.825 | 1.115 | 637.6 | 57.5 | 0.00217 |
| R1 run 3 | 1.019 / 2.357 | 1.084 / 2.415 | 1.277 | 653.4 | 61.2 | 0.00225 |
| **R1 all 3** | **1.036 / 2.106** | **1.092 / 2.263** | **1.173** | **642.9** | **59.6** | **0.00220** |
| **v2b all 3** | 1.385 / 2.112 | n/a (no SQL checks) | 1.478 | 629.3 | 58.8 | 0.00216 |

Cost = prompt tokens x $2.50 + completion tokens x $10.00 per 1M (gpt-4o prices set in `run_r1.py`; check them against the current OpenAI price page). Latency of v2b is the one model call; R1 sums the model calls of a question. Mean SQL-check time per question in R1: 0.058 s.

## 6. Prediction check

Original bullets (`results/r1_prediction_2026-11-01.md`, above the amendment):

| # | Prediction | Verdict | Deciding number |
|---|---|---|---|
| 1 | Attempt 1 is identical to v2b, so only questions whose SQL crashes can change | Not confirmed | The prompt is identical (84/84), but 5 questions changed their pass count and none of them was retried; attempt-1 replies match v2b's in only 61% of cases. |
| 2 | Highest possible gain about 1.7 points per run; total within noise of 60.67, roughly 59 to 63; earlier +2 to +4 was too high | Confirmed | Mean 59.33 (58, 59, 61), -1.33. Run 1 (58) is just below the range. Gain from the loop: 0 passes. |
| 3 | At least half of the crashes fixed ("crashed on attempt 1, fixed by retry") | Not confirmed (superseded by the amendment) | Pass after retry 0 of 4 crashes. SQL runs at the end: 4 of 4. |
| 4 | t4_02, t4_04 (wrong logic) do not change | Confirmed | Both 0/3 in v2b and in R1; tier 4 is 0/4 in all runs. |
| 5 | declined_after_error 0 or close to 0 | Confirmed | 0 in all 3 runs. |
| 6 | Tier 0 unchanged at 7/8 | Confirmed | 7, 7, 7 (v2b 7, 7, 7). |
| 7 | Retry rate under 10%; mean attempts close to 1.0 | Confirmed | 4/252 = 1.6%; mean 1.020 attempts. |

Amendment bullets:

| # | Prediction | Verdict | Deciding number |
|---|---|---|---|
| A1 | All 5 v2b crashes are invented column names in t4_02 and t4_04; the older list (t3_12, t3_04, t4_01) does not crash in v2b | Confirmed | v2b: 5 crashes, all `column "..." does not exist`, all t4_02 or t4_04. In R1 attempt 1 only t4_02 and t4_04 crashed (4 times). |
| A2 | "SQL runs at the end": at least 3 of 5; "pass after retry": 0 of 5 | Confirmed | 4 of 4 crashes ended with SQL that runs; 0 of 4 pass. The denominator is 4, not 5, because attempt 1 differs from run to run (run 1: only t4_04 crashed, not t4_02). |
| A3 | Total within noise of v2b, change about 0, roughly 59 to 63 | Confirmed | Mean 59.33, -1.33; run 1 (58) just outside the range. |
| A4 | "At least half fixed" replaced by the two numbers; "t4_02, t4_04 do not change" refers to passing | Confirmed | Same figures as A2 and bullet 4. |

What the retried questions show: the error message made the model fix the name of the column (`consecutive_count` became `run_length`, and so on), but the query then returned 1 column where the gold has 4 (t4_02 and t4_04, "wrong column count"). Making the SQL run was never the problem for these two questions; the logic and the answer shape are.
