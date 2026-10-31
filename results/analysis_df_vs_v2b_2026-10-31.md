# Row df (decline fix on top of v2b) vs v2b, 2026-10-31

Sources: `results/df_run{1,2,3}_2026-10-31.jsonl` and `results/v2b_t0_run{1,2,3}_2026-10-27.jsonl`. Same exam (84 questions), model gpt-4o, temperature 0, seed 0. Runs 1 and 2 came from `run_df.py --runs 3`, which stopped in run 3 when the OpenAI credits ran out. Run 3 was repeated on its own after a top-up (`RUN_TAG=run3 python run_df.py`), with the same code and settings. The crashed attempt left no result files.

**Headline:** df did not fix the false declines, it created them. Mean score 52.00/84 against v2b's 60.67 (-8.67, identical 52 in all three runs, far outside the 2 to 4 point noise). v2b had 0 false declines on tiers 1-4; df has 10 per run (30 in total). 21 of the 30 say a year or month "is missing from the table" for questions about 2024, 2025 or 2026, which v2b answered correctly 3/3. The same behaviour is also why u_08 (July 2026) is now declined 3/3, so that gain is not evidence of better judgement.

## 1. Scores (passed questions, out of 84; tiers: t0=8, t1=35, t2=25, t3=12, t4=4)

| Row | Run | Total | T0 | T1 | T2 | T3 | T4 |
|---|---|---:|---:|---:|---:|---:|---:|
| df | run 1 | 52 | 8 | 26 | 15 | 3 | 0 |
| df | run 2 | 52 | 8 | 27 | 14 | 3 | 0 |
| df | run 3 | 52 | 8 | 26 | 15 | 3 | 0 |
| **df** | **mean** | **52.00** | **8.00** | **26.33** | **14.67** | **3.00** | **0.00** |
| v2b | run 1 | 60 | 7 | 34 | 17 | 2 | 0 |
| v2b | run 2 | 61 | 7 | 34 | 18 | 2 | 0 |
| v2b | run 3 | 61 | 7 | 34 | 18 | 2 | 0 |
| **v2b** | **mean** | **60.67** | **7.00** | **34.00** | **17.67** | **2.00** | **0.00** |

Mean total difference df minus v2b: -8.67. Noise on this exam is about 2 to 4 points per run.

## 2. Tier 0 (unanswerable), runs that declined out of 3

| id | Question | df declined | v2b declined | df reason, run 1 |
|---|---|---:|---:|---|
| u_01 | How much nuclear power was produced in June 2025? | 3/3 | 3/3 | Nuclear power data is missing after January 2024. |
| u_02 | How much electricity did Bavaria produce last year? | 3/3 | 3/3 | The tables do not contain information about specific regions like Bavaria. |
| u_03 | What will demand be next winter? | 3/3 | 3/3 | Future demand data is missing. |
| u_04 | How much CO2 did German electricity generation emit in 2025? | 3/3 | 3/3 | The CO2 emission factors for each energy source are missing. |
| u_05 | Which power plant produced the most electricity? | 3/3 | 3/3 | The table does not contain information about specific power plants, only energy sources. |
| u_06 | How much solar capacity is installed in Germany? | 3/3 | 3/3 | The table does not provide information on installed solar capacity. |
| u_07 | What was the average price in the DE/AT/LU zone in 2025? | 3/3 | 3/3 | The DE/AT/LU zone has no price data in the dataset. |
| u_08 | How much wind did we generate in July 2026? | 3/3 | 0/3 | Data for July 2026 is missing. |

Tier 0 passes: df [8, 8, 8] (mean 8.00), v2b [7, 7, 7] (mean 7.00).

## 3. False declines on tiers 1-4

Count per run: run 1: 10, run 2: 10, run 3: 10 (df); v2b: [0, 0, 0].

| Run | id | Question | Reason (word for word) |
|---:|---|---|---|
| 1 | t1_12 | Wie viel Strom kam im Februar 2026 aus Gaskraftwerken? | The table does not contain data for February 2026. |
| 1 | t1_19 | Wie viel Strom kam im November 2025 aus Speicherkraftwerken? | The tables do not specify which generation sources are considered "Speicherkraftwerken" (storage power plants). |
| 1 | t1_22 | What was the German power price at midday on 3 March 2025? | The dataset does not contain data for the year 2025. |
| 1 | t1_27 | average Dutch price in 2024? | The table does not contain data for the year 2024. |
| 1 | t1_31 | How high did the German price get in 2024 at most? | The table does not contain data for the year 2024. |
| 1 | t1_34 | wie viel windkraft an land gab es am 1. januar 2026? | Data for 2026 is not available in the table. |
| 1 | t1_35 | What was the average price in Austria in December 2025? | The data for December 2025 is missing. |
| 1 | t2_25 | Rank the neighbouring countries by their average price in 2025. | Data for 2025 is missing. |
| 1 | t3_12 | Which day had the lowest total generation, and how far below the daily average was it? | The table does not provide enough data to calculate the daily average generation. |
| 1 | t4_04 | What was the longest run of consecutive quarter-hours with a negative German price? | The table does not contain any data to determine the longest run of consecutive quarter-hours with a negative German price. |
| 2 | t1_12 | Wie viel Strom kam im Februar 2026 aus Gaskraftwerken? | Data for February 2026 is not available in the table. |
| 2 | t1_19 | Wie viel Strom kam im November 2025 aus Speicherkraftwerken? | The tables do not specify which power plants are storage power plants. |
| 2 | t1_22 | What was the German power price at midday on 3 March 2025? | The table does not contain data for the year 2025. |
| 2 | t1_31 | How high did the German price get in 2024 at most? | The table does not contain data for the year 2024. |
| 2 | t1_34 | wie viel windkraft an land gab es am 1. januar 2026? | Data for 2026 is not available in the table. |
| 2 | t1_35 | What was the average price in Austria in December 2025? | The data for December 2025 is missing. |
| 2 | t2_16 | Average German price month by month in 2025. | The dataset does not contain any data for the year 2025. |
| 2 | t2_25 | Rank the neighbouring countries by their average price in 2025. | The table does not contain data for the year 2025. |
| 2 | t3_04 | On the day electricity was most expensive, what was the generation mix? | The question requires identifying the day with the highest electricity price, but the preise table does not contain any data for the DE/AT/LU price zone, which is entirely empty. |
| 2 | t4_04 | What was the longest run of consecutive quarter-hours with a negative German price? | The table does not contain any data to determine the longest run of consecutive quarter-hours with a negative German price. |
| 3 | t1_12 | Wie viel Strom kam im Februar 2026 aus Gaskraftwerken? | Data for February 2026 is not available in the table. |
| 3 | t1_17 | How much solar did we get on Christmas Day 2024? | Data for Kernenergie is missing after 2024-01-30, but the question is about Photovoltaik on Christmas Day 2024, which is available. |
| 3 | t1_19 | Wie viel Strom kam im November 2025 aus Speicherkraftwerken? | The tables do not specify which power plants are storage power plants. |
| 3 | t1_22 | What was the German power price at midday on 3 March 2025? | The dataset does not contain data for the year 2025. |
| 3 | t1_27 | average Dutch price in 2024? | The table does not contain data for the year 2024. |
| 3 | t1_31 | How high did the German price get in 2024 at most? | The table does not contain data for the year 2024. |
| 3 | t1_34 | wie viel windkraft an land gab es am 1. januar 2026? | Data for 2026 is not available in the table. |
| 3 | t1_35 | What was the average price in Austria in December 2025? | The data for December 2025 is missing. |
| 3 | t2_25 | Rank the neighbouring countries by their average price in 2025. | Data for 2025 is missing. |
| 3 | t4_04 | What was the longest run of consecutive quarter-hours with a negative German price? | The table does not contain any data to determine the longest run of consecutive quarter-hours with a negative German price. |

## 4. Shape failures (column count + row count + SQL error), summed over 3 runs

| Row | Column count | Row count | SQL error | Total | Per run |
|---|---:|---:|---:|---:|---:|
| df | 24 | 16 | 3 | 43 | [14, 15, 14] |
| v2b | 20 | 15 | 5 | 40 | [14, 13, 13] |

## 5. Questions whose pass count changed (v2b to df)

| id | Tier | v2b | df | Change |
|---|---:|---:|---:|---:|
| t1_12 | 1 | 3/3 | 0/3 | -3 |
| t1_19 | 1 | 3/3 | 0/3 | -3 |
| t1_22 | 1 | 3/3 | 0/3 | -3 |
| t1_31 | 1 | 3/3 | 0/3 | -3 |
| t1_34 | 1 | 3/3 | 0/3 | -3 |
| t1_35 | 1 | 3/3 | 0/3 | -3 |
| t2_09 | 2 | 3/3 | 0/3 | -3 |
| t2_24 | 2 | 3/3 | 0/3 | -3 |
| t3_02 | 3 | 0/3 | 3/3 | +3 |
| u_08 | 0 | 0/3 | 3/3 | +3 |
| t1_27 | 1 | 3/3 | 1/3 | -2 |
| t2_01 | 2 | 3/3 | 1/3 | -2 |
| t1_02 | 1 | 3/3 | 2/3 | -1 |
| t1_10 | 1 | 3/3 | 2/3 | -1 |
| t1_17 | 1 | 3/3 | 2/3 | -1 |
| t2_06 | 2 | 2/3 | 3/3 | +1 |
| t2_16 | 2 | 3/3 | 2/3 | -1 |
| t2_17 | 2 | 3/3 | 2/3 | -1 |

18 questions changed; net -26 passes summed over 3 runs (-8.67 per run).

### What changed in the SQL for questions that moved by 2 or more

**Became false declines (v2b 3/3 passes, df 0/3 or 1/3): t1_12, t1_22, t1_27, t1_31, t1_34, t1_35.** v2b wrote a plain date filter (for example `zeitpunkt >= '2026-02-01' AND zeitpunkt < '2026-03-01'`) and passed. df replies `NO_QUERY` with "the table does not contain data for [year or month]" (2024, 2025, Feb 2026, Jan 2026, Dec 2025). The data exists for all of these (v2b's answers matched the gold SQL). t1_27 is the only one where df sometimes answers (run 2, with `EXTRACT(YEAR FROM zeitpunkt) = 2024`).

**t1_19 (Speicherkraftwerken), 3/3 to 0/3.** v2b mapped the word to `energietraeger = 'Pumpspeicher'`. df declines with "the tables do not specify which power plants are storage power plants". Different cause from the date declines: the new "not in the tables at all" wording makes the model refuse a word-to-value mapping it used to make.

**t2_09 (month with highest solar), 3/3 to 0/3, no decline.** v2b grouped by `DATE_TRUNC('month', zeitpunkt)` (2 columns). df writes `EXTRACT(YEAR ...)` and `EXTRACT(MONTH ...)` as two separate columns (3 columns), so the column count no longer matches (gold=2, agent=3).

**t2_24 (average residual load per month in 2025), 3/3 to 0/3, no decline.** v2b used `DATE_TRUNC('month', zeitpunkt)` (a date). df uses `EXTRACT(MONTH FROM zeitpunkt)` (the number 1 to 12), so the first column no longer matches the gold date. t2_09 and t2_24 look like a side effect of listing "year, month, day, weekday, hour" as parts of zeitpunkt in the new instruction: it points the model at EXTRACT. This is my reading of the SQL; I did not test it.

**t2_01 (top source overall), 3/3 to 1/3, no decline.** Runs 1 and 3 select only `energietraeger` and order by `SUM(mwh)` (1 column, gold has 2); run 2 keeps the `SUM(mwh)` column like v2b. Nothing in the new wording is about this, so I cannot attribute it; it may be instability.

**Moves in df's favour:**
- **u_08 (0/3 to 3/3):** v2b answered with a July 2026 query; df declines with "Data for July 2026 is missing". This comes from the same date-claim behaviour as the t1_12 and t1_34 declines above.
- **t3_02 (0/3 to 3/3):** v2b returned the wind share as a fraction (0.305) where gold has a percentage (30.51); df multiplies by 100 (and filters with EXTRACT year/month). Nothing in the new wording mentions percent, so I do not attribute this to the fix.

Net over all 18 changed questions: -26 passes over 3 runs (-8.67 per run). Eight tier 1-2 questions lost all 3 passes; two questions gained 3.

## 6. Latency and tokens per question (mean over 84 questions x 3 runs)

| Row | Latency (s) | Prompt tokens | Completion tokens |
|---|---:|---:|---:|
| df | 1.009 | 715.3 | 52.6 |
| v2b | 1.478 | 629.3 | 58.8 |

## 7. Prediction check (points from `results/df_prediction_2026-10-31.md`)

| # | Prediction | Verdict | Deciding number |
|---|---|---|---|
| 1 | Tier 0 stays at 7/8 on average; u_01 and u_07 still declined; small risk u_04 is answered | Partly | Tier 0 mean 8.00/8 (v2b 7.00), so "stays at 7/8" is wrong. u_01 and u_07 declined 3/3 (confirmed). u_04 declined 3/3 (the risk did not occur). |
| 2 | u_08 still 0/3 | Not confirmed | u_08 passes 3/3 (declined, "Data for July 2026 is missing"). |
| 3 | False declines on tiers 1-4 stay near 0 (v2b had 0) | Not confirmed | 10, 10 and 10 per run (30 in total). |
| 4 | Total within noise of v2b's 60.67, roughly 58 to 63 | Not confirmed | Mean 52.00 (52, 52, 52); -8.67 against v2b. |
| 5 | Real test is ex-a and ex-b re-run on top of df | Not tested here | df as built is not a usable base for them: it introduces 30 false declines of its own (v2b had none) and lowers the score by 8.67. |
| 6 | Known risk: wording written after reading exam failures; held-out run (O13) is the real check | Not tested here | No held-out file was opened. The exam itself already shows the wording does not generalise: it lost 26 passes net on the exam it was shaped by. |

Point 5's second half is a judgement, not a measurement: ex-a and ex-b were not re-run.
