# False-decline inventory for O14 (read-only analysis), 2026-10-31

Scope: every `NO_QUERY` reply on a tier 1-4 question in `results/exa_run{1,2,3}_2026-10-31.jsonl` and `results/exb_run{1,2,3}_2026-10-31.jsonl`. A decline = `extracted_sql` is null and the raw output starts with `NO_QUERY`. All of these are false declines (tiers 1-4 are answerable). No code changed, no API calls, held-out files not opened.

## Summary: false declines by group and row (3 runs each, counts are decline events, not distinct questions)

| Group | exa | exb | Total |
|---|---:|---:|---:|
| A. Date/period claimed not in the data | 0 | 6 | 6 |
| B. Column/info claimed not to exist (but calculable) | 29 | 36 | 65 |
| C. Question called ambiguous/unclear/underspecified | 5 | 7 | 12 |
| D. Anything else | 1 | 2 | 3 |
| **Total** | **35** | **51** | **86** |

Grouping rule: first fitting group in order A, B, C, D. Where a reason also fits a later group, or the call is borderline, the Note column says so. Judgement calls are mine: a reason is A only if it says the period/date is absent from the data; "time period is not specified" is about the question and goes to C.

## Tier-0 questions (v2b, 3 runs)

Source: `gold_set_smard.yaml` (tier 0) and `results/v2b_t0_run{1,2,3}_2026-10-27.jsonl`. "Declined" = of the 3 runs, how many replied `NO_QUERY`.

| id | Question | Declined (of 3) | Decline reason, run 1 |
|---|---|---:|---|
| u_01 | How much nuclear power was produced in June 2025? | 3/3 | There is no data for nuclear power after 2024-01-30. |
| u_02 | How much electricity did Bavaria produce last year? | 3/3 | The tables do not contain information specific to Bavaria's electricity production. |
| u_03 | What will demand be next winter? | 3/3 | Future demand data is not available in the table. |
| u_04 | How much CO2 did German electricity generation emit in 2025? | 3/3 | Emission factors for each energy source are missing. |
| u_05 | Which power plant produced the most electricity? | 3/3 | The table does not contain information about specific power plants, only energy sources. |
| u_06 | How much solar capacity is installed in Germany? | 3/3 | The table does not contain information about installed solar capacity. |
| u_07 | What was the average price in the DE/AT/LU zone in 2025? | 3/3 | The DE/AT/LU zone has no price data in the dataset. |
| u_08 | How much wind did we generate in July 2026? | 0/3 | none (run 1 answered with SQL) |

## All false declines (tier 1-4)

Reason = text after `NO_QUERY:`, verbatim.

| Row | Run | Id | Tier | Group | Question | Reason | Note |
|---|---:|---|---:|---|---|---|---|
| exa | 1 | t1_25 | 1 | C | How much other renewables generation in total? | The time period for the total other renewables generation is missing. | "time period" is missing from the question, not claimed missing from the data; a keyword match would put it in A |
| exa | 1 | t1_26 | 1 | B | Was war der höchste Sonnenstrom-Wert im Mai 2025? | The table does not provide a direct way to identify the highest value for Sonnenstrom (solar power) in May 2025. | borderline: claims no direct way to get the highest value (a MAX); could be D |
| exa | 1 | t2_12 | 2 | B | Which day of the week has the highest average consumption? | The table does not contain information about the day of the week. |  |
| exa | 1 | t2_15 | 2 | C | Wie viel Ökostrom gab es 2025 im Vergleich zum konventionellen Strom? | The question does not specify which energy sources are considered "Ökostrom" (renewable) and which are "konventionell" (conventional). |  |
| exa | 1 | t3_04 | 3 | C | On the day electricity was most expensive, what was the generation mix? | The question does not specify a date range or price zone to determine the day electricity was most expensive. |  |
| exa | 1 | t3_05 | 3 | B | Which day had the biggest swing between its highest and lowest grid load? | The table does not contain information about the highest and lowest grid load per day. |  |
| exa | 1 | t3_12 | 3 | B | Which day had the lowest total generation, and how far below the daily average was it? | The table does not contain information about the daily average generation needed for comparison. |  |
| exa | 1 | t4_01 | 4 | B | For each week, which source was the top producer? | The table does not have a direct way to determine the top producer for each week. |  |
| exa | 1 | t4_02 | 4 | B | What was the longest unbroken stretch where solar output was zero? | The table does not contain information about continuous time intervals with zero solar output. |  |
| exa | 1 | t4_03 | 4 | B | Which hours had more generation than consumption? | The tables do not provide hourly aggregated data for generation and consumption. |  |
| exa | 1 | t4_04 | 4 | B | What was the longest run of consecutive quarter-hours with a negative German price? | The table does not contain information about consecutive intervals. |  |
| exa | 2 | t1_25 | 1 | C | How much other renewables generation in total? | The time period for the total generation of other renewables is not specified. | "time period" is missing from the question, not claimed missing from the data; a keyword match would put it in A |
| exa | 2 | t2_03 | 2 | B | What was the average solar output for each hour of the day? | The table does not contain hourly aggregated data for solar output. |  |
| exa | 2 | t2_12 | 2 | B | Which day of the week has the highest average consumption? | The table does not contain information about the day of the week. |  |
| exa | 2 | t3_04 | 3 | B | On the day electricity was most expensive, what was the generation mix? | The specific day when electricity was most expensive is not provided. | "specific day ... not provided": the day is computable (day of max price) |
| exa | 2 | t3_05 | 3 | B | Which day had the biggest swing between its highest and lowest grid load? | The table does not contain information about the highest and lowest grid load per day. |  |
| exa | 2 | t3_07 | 3 | D | What share of consumption was covered by renewables in 2025? | Information on which energy sources are considered renewables is missing. | asks for a renewable/conventional mapping; not a calculable column, and does not call the question unclear |
| exa | 2 | t3_11 | 3 | B | In 2025, was the price different in quarter-hours with a lot of solar, say above 5000 MWh, compared to the rest? | The question requires a comparison of prices based on solar generation, but the tables do not directly link generation levels to price differences. |  |
| exa | 2 | t3_12 | 3 | B | Which day had the lowest total generation, and how far below the daily average was it? | The table does not contain information about the daily average generation needed to determine how far below the average the lowest total generation was. |  |
| exa | 2 | t4_01 | 4 | B | For each week, which source was the top producer? | The tables do not contain weekly aggregated data or a direct way to determine the top producer for each week. |  |
| exa | 2 | t4_02 | 4 | B | What was the longest unbroken stretch where solar output was zero? | The table does not contain continuous time intervals or information to determine unbroken stretches. |  |
| exa | 2 | t4_03 | 4 | B | Which hours had more generation than consumption? | The tables do not provide hourly aggregated data for generation and consumption. |  |
| exa | 2 | t4_04 | 4 | B | What was the longest run of consecutive quarter-hours with a negative German price? | The table does not contain information about consecutive intervals. |  |
| exa | 3 | t1_26 | 1 | B | Was war der höchste Sonnenstrom-Wert im Mai 2025? | The table does not provide a direct way to identify the highest value for Sonnenstrom (solar power) in May 2025. | borderline: claims no direct way to get the highest value (a MAX); could be D |
| exa | 3 | t2_12 | 2 | B | Which day of the week has the highest average consumption? | The table does not contain information about the day of the week. |  |
| exa | 3 | t2_15 | 2 | C | Wie viel Ökostrom gab es 2025 im Vergleich zum konventionellen Strom? | The question does not specify which energy sources are considered "Ökostrom" (renewable) and which are "konventionell" (conventional). |  |
| exa | 3 | t3_04 | 3 | B | On the day electricity was most expensive, what was the generation mix? | The specific day when electricity was most expensive is not provided. | "specific day ... not provided": the day is computable (day of max price) |
| exa | 3 | t3_05 | 3 | B | Which day had the biggest swing between its highest and lowest grid load? | The table does not contain information about the highest and lowest grid load per day. |  |
| exa | 3 | t3_07 | 3 | B | What share of consumption was covered by renewables in 2025? | The question requires data on total renewable generation, which is not directly available in the tables. |  |
| exa | 3 | t3_11 | 3 | B | In 2025, was the price different in quarter-hours with a lot of solar, say above 5000 MWh, compared to the rest? | The question requires a comparison of prices based on solar generation, but the tables do not directly link generation and prices for specific intervals. |  |
| exa | 3 | t3_12 | 3 | B | Which day had the lowest total generation, and how far below the daily average was it? | The table does not provide information on daily average generation. |  |
| exa | 3 | t4_01 | 4 | B | For each week, which source was the top producer? | The tables do not contain weekly aggregated data or a direct way to determine the top producer for each week. |  |
| exa | 3 | t4_02 | 4 | B | What was the longest unbroken stretch where solar output was zero? | The table does not contain information about continuous time periods or stretches of zero solar output. |  |
| exa | 3 | t4_03 | 4 | B | Which hours had more generation than consumption? | The tables do not provide hourly aggregated data for generation and consumption. |  |
| exa | 3 | t4_04 | 4 | B | What was the longest run of consecutive quarter-hours with a negative German price? | The table does not contain information about consecutive intervals. |  |
| exb | 1 | t1_12 | 1 | A | Wie viel Strom kam im Februar 2026 aus Gaskraftwerken? | The table does not contain data for the year 2026. |  |
| exb | 1 | t1_19 | 1 | C | Wie viel Strom kam im November 2025 aus Speicherkraftwerken? | The term "Speicherkraftwerken" is ambiguous and not clearly defined in the provided tables. |  |
| exb | 1 | t1_22 | 1 | A | What was the German power price at midday on 3 March 2025? | The exact price at midday on 3 March 2025 is missing. | also reads as B (claims a piece of information is missing); first fit A. Borderline: a point in time, not a period |
| exb | 1 | t2_01 | 2 | C | Which energy source produced the most overall? | The time period for the query is not specified. | "time period" is missing from the question, not claimed missing from the data; a keyword match would put it in A |
| exb | 1 | t2_03 | 2 | B | What was the average solar output for each hour of the day? | The table does not contain information about hourly solar output. |  |
| exb | 1 | t2_11 | 2 | D | Welche Stromquelle hat 2024 wie viel geliefert? Bitte absteigend sortieren. | The question is missing. | garbled; closest to C but does not say the question is ambiguous |
| exb | 1 | t2_18 | 2 | B | How many negative-price quarter-hours were there each year? | The table does not contain information about the year for each timestamp. |  |
| exb | 1 | t3_04 | 3 | B | On the day electricity was most expensive, what was the generation mix? | The specific day when electricity was most expensive is not provided. | "specific day ... not provided": the day is computable (day of max price) |
| exb | 1 | t3_05 | 3 | B | Which day had the biggest swing between its highest and lowest grid load? | The table does not contain daily maximum and minimum grid load values needed to calculate the swing. |  |
| exb | 1 | t3_07 | 3 | B | What share of consumption was covered by renewables in 2025? | The share of consumption covered by renewables requires data on renewable generation and total consumption, but the tables do not directly provide this comparison. |  |
| exb | 1 | t3_09 | 3 | B | On the windiest day for onshore wind, what was the average German price? | The question requires identifying the windiest day, which needs additional data or calculations not provided in the tables. |  |
| exb | 1 | t3_10 | 3 | B | Monat für Monat: wie hoch war der Sonnenstrom-Anteil an der Gesamterzeugung 2025? | The table does not contain information about the total electricity generation for all energy sources. |  |
| exb | 1 | t3_11 | 3 | B | In 2025, was the price different in quarter-hours with a lot of solar, say above 5000 MWh, compared to the rest? | The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to correlate solar generation with prices. |  |
| exb | 1 | t3_12 | 3 | B | Which day had the lowest total generation, and how far below the daily average was it? | The table does not provide information on daily averages for comparison. |  |
| exb | 1 | t4_01 | 4 | C | For each week, which source was the top producer? | The question requires identifying the top producer per week, but the necessary logic to determine the top producer is not specified. | borderline: "logic ... not specified" is underspecification wording; could be D |
| exb | 1 | t4_02 | 4 | B | What was the longest unbroken stretch where solar output was zero? | The table does not contain information about unbroken stretches or durations. |  |
| exb | 1 | t4_03 | 4 | B | Which hours had more generation than consumption? | The tables do not provide a direct way to compare total generation and consumption for each hour. |  |
| exb | 1 | t4_04 | 4 | B | What was the longest run of consecutive quarter-hours with a negative German price? | Information about consecutive quarter-hours is missing. |  |
| exb | 2 | t1_12 | 1 | A | Wie viel Strom kam im Februar 2026 aus Gaskraftwerken? | Data for February 2026 is not available in the table. |  |
| exb | 2 | t1_19 | 1 | C | Wie viel Strom kam im November 2025 aus Speicherkraftwerken? | The term "Speicherkraftwerken" is ambiguous and not directly represented in the tables. |  |
| exb | 2 | t1_22 | 1 | A | What was the German power price at midday on 3 March 2025? | The specific timestamp for midday on 3 March 2025 is missing. | also reads as B (claims a piece of information is missing); first fit A. Borderline: a point in time, not a period |
| exb | 2 | t2_03 | 2 | B | What was the average solar output for each hour of the day? | The table does not contain information about hourly solar output. |  |
| exb | 2 | t2_15 | 2 | C | Wie viel Ökostrom gab es 2025 im Vergleich zum konventionellen Strom? | The question does not specify which energy sources are considered "Ökostrom" and which are "konventionell". |  |
| exb | 2 | t2_18 | 2 | B | How many negative-price quarter-hours were there each year? | The table does not contain information about the year for each timestamp. |  |
| exb | 2 | t3_04 | 3 | B | On the day electricity was most expensive, what was the generation mix? | The specific day when electricity was most expensive is not provided. | "specific day ... not provided": the day is computable (day of max price) |
| exb | 2 | t3_05 | 3 | B | Which day had the biggest swing between its highest and lowest grid load? | The table does not contain daily aggregated data to calculate the swing between highest and lowest grid load for each day. |  |
| exb | 2 | t3_07 | 3 | D | What share of consumption was covered by renewables in 2025? | The table does not provide direct information on which energy sources are considered renewables. | asks for a renewable/conventional mapping; not a calculable column, and does not call the question unclear |
| exb | 2 | t3_09 | 3 | B | On the windiest day for onshore wind, what was the average German price? | The date of the windiest day for onshore wind is missing. |  |
| exb | 2 | t3_10 | 3 | B | Monat für Monat: wie hoch war der Sonnenstrom-Anteil an der Gesamterzeugung 2025? | The table does not contain information about the total electricity generation for all energy sources. |  |
| exb | 2 | t3_11 | 3 | B | In 2025, was the price different in quarter-hours with a lot of solar, say above 5000 MWh, compared to the rest? | The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to compare prices with solar generation levels. |  |
| exb | 2 | t3_12 | 3 | B | Which day had the lowest total generation, and how far below the daily average was it? | The table does not provide information on daily averages for comparison. |  |
| exb | 2 | t4_01 | 4 | B | For each week, which source was the top producer? | The question requires weekly aggregation, but the table does not have a direct way to determine the top producer per week without additional context or data. |  |
| exb | 2 | t4_03 | 4 | B | Which hours had more generation than consumption? | The tables do not provide direct information on hourly generation versus consumption comparison. |  |
| exb | 2 | t4_04 | 4 | B | What was the longest run of consecutive quarter-hours with a negative German price? | Information about consecutive quarter-hours is missing. |  |
| exb | 3 | t1_12 | 1 | A | Wie viel Strom kam im Februar 2026 aus Gaskraftwerken? | The table does not contain data for the year 2026. |  |
| exb | 3 | t1_22 | 1 | A | What was the German power price at midday on 3 March 2025? | The specific timestamp for midday on 3 March 2025 is missing. | also reads as B (claims a piece of information is missing); first fit A. Borderline: a point in time, not a period |
| exb | 3 | t2_03 | 2 | B | What was the average solar output for each hour of the day? | The table does not have information on hourly solar output. |  |
| exb | 3 | t2_11 | 2 | C | Welche Stromquelle hat 2024 wie viel geliefert? Bitte absteigend sortieren. | The question does not specify the energy sources to be included. |  |
| exb | 3 | t2_15 | 2 | C | Wie viel Ökostrom gab es 2025 im Vergleich zum konventionellen Strom? | The question does not specify which energy sources are considered "Ökostrom" and which are "konventionell". |  |
| exb | 3 | t2_18 | 2 | B | How many negative-price quarter-hours were there each year? | The table does not contain information about the year for each timestamp. |  |
| exb | 3 | t3_04 | 3 | B | On the day electricity was most expensive, what was the generation mix? | The specific day when electricity was most expensive is not provided. | "specific day ... not provided": the day is computable (day of max price) |
| exb | 3 | t3_05 | 3 | B | Which day had the biggest swing between its highest and lowest grid load? | The table does not contain daily high and low grid load values to calculate the swing. |  |
| exb | 3 | t3_07 | 3 | B | What share of consumption was covered by renewables in 2025? | The question requires data on renewable generation, which is not directly available in the tables. |  |
| exb | 3 | t3_09 | 3 | B | On the windiest day for onshore wind, what was the average German price? | The specific date of the windiest day for onshore wind is missing. |  |
| exb | 3 | t3_10 | 3 | B | Monat für Monat: wie hoch war der Sonnenstrom-Anteil an der Gesamterzeugung 2025? | The table does not contain information about the total electricity generation for all energy sources. |  |
| exb | 3 | t3_11 | 3 | B | In 2025, was the price different in quarter-hours with a lot of solar, say above 5000 MWh, compared to the rest? | The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to correlate solar generation with prices. |  |
| exb | 3 | t3_12 | 3 | B | Which day had the lowest total generation, and how far below the daily average was it? | The table does not provide information on daily averages for comparison. |  |
| exb | 3 | t4_01 | 4 | B | For each week, which source was the top producer? | The question requires weekly aggregation of generation data, which is not directly available in the tables. |  |
| exb | 3 | t4_02 | 4 | B | What was the longest unbroken stretch where solar output was zero? | The table does not contain information about unbroken stretches or durations. |  |
| exb | 3 | t4_03 | 4 | B | Which hours had more generation than consumption? | The tables do not provide direct information on hourly generation versus consumption comparison. |  |
| exb | 3 | t4_04 | 4 | B | What was the longest run of consecutive quarter-hours with a negative German price? | Information about consecutive quarter-hours is missing. |  |
