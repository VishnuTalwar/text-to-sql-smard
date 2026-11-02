# Date finder dry run on existing results (read only), 2026-11-02

Code: `grader/date_facts.py`, tests: `grader/tests/test_date_facts.py`. No API call, no change to the loop. Rows are shown as e/v/p = rows in erzeugung / verbrauch / preise for the period. "Review fires" = `decline_review_decision`: a period is found in the reason, the wording is not open-ended, and every period has rows. Sources: df, ex-a, ex-b (2026-10-31), v2b_fresh and R2 (2026-11-02), all 3 runs each; every `NO_QUERY` reply, tier 0 and tiers 1-4.

## Summary (3c)

| Row | (i) False declines tiers 1-4 | (i) review fires on | (ii) Correct tier-0 declines | (ii) review fires on | (iii) Empty results where the empty fact fires |
|---|---:|---:|---:|---:|---|
| df | 30 | 21 | 24 | 0 | not computed |
| ex-a | 35 | 2 | 24 | 0 | not computed |
| ex-b | 51 | 6 | 21 | 0 | not computed |
| v2b_fresh | 0 | 0 | 21 | 0 | u_08 (run 1), u_08 (run 2), u_08 (run 3) |
| R2 | 0 | 0 | 21 | 0 | u_08 (run 1), u_08 (run 2), u_08 (run 3) |

**Tier-0 declines where the review would fire (must be 0):** none.

### False declines the review would NOT fire on

| Row | Count | By reason of not firing | Question ids |
|---|---:|---|---|
| df | 9 | 8 x no period found; 1 x open-ended wording | t1_17 (1), t1_19 (3), t3_04 (1), t3_12 (1), t4_04 (3) |
| ex-a | 33 | 33 x no period found | t1_25 (2), t2_03 (1), t2_12 (3), t2_15 (2), t3_04 (3), t3_05 (3), t3_07 (2), t3_11 (2), t3_12 (3), t4_01 (3), t4_02 (3), t4_03 (3), t4_04 (3) |
| ex-b | 45 | 45 x no period found | t1_19 (2), t2_01 (1), t2_03 (3), t2_11 (2), t2_15 (2), t2_18 (3), t3_04 (3), t3_05 (3), t3_07 (3), t3_09 (3), t3_10 (3), t3_11 (3), t3_12 (3), t4_01 (3), t4_02 (2), t4_03 (3), t4_04 (3) |
| v2b_fresh | 0 | - | - |
| R2 | 0 | - | - |

## 3a. Every NO_QUERY reply

| Row | Run | Id | Tier | Reason | Periods found, rows (e/v/p) | Open-ended | Review fires |
|---|---:|---|---:|---|---|---|---|
| df | 1 | t1_12 | 1 | The table does not contain data for February 2026. | 2026-02-01..2026-03-01: e32256/v10752/p45696 | no | **yes** |
| df | 1 | t1_19 | 1 | The tables do not specify which generation sources are considered "Speicherkraftwerken" (storage power plants). | - | no | no |
| df | 1 | t1_22 | 1 | The dataset does not contain data for the year 2025. | 2025-01-01..2026-01-01: e420480/v140160/p595680 | no | **yes** |
| df | 1 | t1_27 | 1 | The table does not contain data for the year 2024. | 2024-01-01..2025-01-01: e421632/v140544/p597312 | no | **yes** |
| df | 1 | t1_31 | 1 | The table does not contain data for the year 2024. | 2024-01-01..2025-01-01: e421632/v140544/p597312 | no | **yes** |
| df | 1 | t1_34 | 1 | Data for 2026 is not available in the table. | 2026-01-01..2027-01-01: e175056/v58352/p247996 | no | **yes** |
| df | 1 | t1_35 | 1 | The data for December 2025 is missing. | 2025-12-01..2026-01-01: e35712/v11904/p50592 | no | **yes** |
| df | 1 | t2_25 | 2 | Data for 2025 is missing. | 2025-01-01..2026-01-01: e420480/v140160/p595680 | no | **yes** |
| df | 1 | t3_12 | 3 | The table does not provide enough data to calculate the daily average generation. | - | no | no |
| df | 1 | t4_04 | 4 | The table does not contain any data to determine the longest run of consecutive quarter-hours with a negative German price. | - | no | no |
| df | 1 | u_01 | 0 | Nuclear power data is missing after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| df | 1 | u_02 | 0 | The tables do not contain information about specific regions like Bavaria. | - | no | no |
| df | 1 | u_03 | 0 | Future demand data is missing. | - | no | no |
| df | 1 | u_04 | 0 | The CO2 emission factors for each energy source are missing. | - | no | no |
| df | 1 | u_05 | 0 | The table does not contain information about specific power plants, only energy sources. | - | no | no |
| df | 1 | u_06 | 0 | The table does not provide information on installed solar capacity. | - | no | no |
| df | 1 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| df | 1 | u_08 | 0 | Data for July 2026 is missing. | 2026-07-01..2026-08-01: e0/v0/p0 | no | no |
| df | 2 | t1_12 | 1 | Data for February 2026 is not available in the table. | 2026-02-01..2026-03-01: e32256/v10752/p45696 | no | **yes** |
| df | 2 | t1_19 | 1 | The tables do not specify which power plants are storage power plants. | - | no | no |
| df | 2 | t1_22 | 1 | The table does not contain data for the year 2025. | 2025-01-01..2026-01-01: e420480/v140160/p595680 | no | **yes** |
| df | 2 | t1_31 | 1 | The table does not contain data for the year 2024. | 2024-01-01..2025-01-01: e421632/v140544/p597312 | no | **yes** |
| df | 2 | t1_34 | 1 | Data for 2026 is not available in the table. | 2026-01-01..2027-01-01: e175056/v58352/p247996 | no | **yes** |
| df | 2 | t1_35 | 1 | The data for December 2025 is missing. | 2025-12-01..2026-01-01: e35712/v11904/p50592 | no | **yes** |
| df | 2 | t2_16 | 2 | The dataset does not contain any data for the year 2025. | 2025-01-01..2026-01-01: e420480/v140160/p595680 | no | **yes** |
| df | 2 | t2_25 | 2 | The table does not contain data for the year 2025. | 2025-01-01..2026-01-01: e420480/v140160/p595680 | no | **yes** |
| df | 2 | t3_04 | 3 | The question requires identifying the day with the highest electricity price, but the preise table does not contain any data for the DE/AT/LU price zone, which is entirely empty. | - | no | no |
| df | 2 | t4_04 | 4 | The table does not contain any data to determine the longest run of consecutive quarter-hours with a negative German price. | - | no | no |
| df | 2 | u_01 | 0 | Nuclear power data is missing after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| df | 2 | u_02 | 0 | The tables do not contain information about specific regions like Bavaria. | - | no | no |
| df | 2 | u_03 | 0 | Future demand data is missing. | - | no | no |
| df | 2 | u_04 | 0 | The CO2 emission factors for each energy source are missing. | - | no | no |
| df | 2 | u_05 | 0 | The table does not contain information about specific power plants, only energy sources. | - | no | no |
| df | 2 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| df | 2 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| df | 2 | u_08 | 0 | Data for July 2026 is missing. | 2026-07-01..2026-08-01: e0/v0/p0 | no | no |
| df | 3 | t1_12 | 1 | Data for February 2026 is not available in the table. | 2026-02-01..2026-03-01: e32256/v10752/p45696 | no | **yes** |
| df | 3 | t1_17 | 1 | Data for Kernenergie is missing after 2024-01-30, but the question is about Photovoltaik on Christmas Day 2024, which is available. | 2024-01-01..2025-01-01: e421632/v140544/p597312; 2024-01-30..2024-01-31: e1152/v384/p1632 | yes | no |
| df | 3 | t1_19 | 1 | The tables do not specify which power plants are storage power plants. | - | no | no |
| df | 3 | t1_22 | 1 | The dataset does not contain data for the year 2025. | 2025-01-01..2026-01-01: e420480/v140160/p595680 | no | **yes** |
| df | 3 | t1_27 | 1 | The table does not contain data for the year 2024. | 2024-01-01..2025-01-01: e421632/v140544/p597312 | no | **yes** |
| df | 3 | t1_31 | 1 | The table does not contain data for the year 2024. | 2024-01-01..2025-01-01: e421632/v140544/p597312 | no | **yes** |
| df | 3 | t1_34 | 1 | Data for 2026 is not available in the table. | 2026-01-01..2027-01-01: e175056/v58352/p247996 | no | **yes** |
| df | 3 | t1_35 | 1 | The data for December 2025 is missing. | 2025-12-01..2026-01-01: e35712/v11904/p50592 | no | **yes** |
| df | 3 | t2_25 | 2 | Data for 2025 is missing. | 2025-01-01..2026-01-01: e420480/v140160/p595680 | no | **yes** |
| df | 3 | t4_04 | 4 | The table does not contain any data to determine the longest run of consecutive quarter-hours with a negative German price. | - | no | no |
| df | 3 | u_01 | 0 | Nuclear power data is missing after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| df | 3 | u_02 | 0 | The tables do not contain information about specific regions like Bavaria. | - | no | no |
| df | 3 | u_03 | 0 | Future demand data is missing. | - | no | no |
| df | 3 | u_04 | 0 | The CO2 emission factors for each energy source are missing. | - | no | no |
| df | 3 | u_05 | 0 | The table does not contain information about specific power plants, only energy sources. | - | no | no |
| df | 3 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| df | 3 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| df | 3 | u_08 | 0 | Data for July 2026 is missing. | 2026-07-01..2026-08-01: e0/v0/p0 | no | no |
| ex-a | 1 | t1_25 | 1 | The time period for the total other renewables generation is missing. | - | no | no |
| ex-a | 1 | t1_26 | 1 | The table does not provide a direct way to identify the highest value for Sonnenstrom (solar power) in May 2025. | 2025-05-01..2025-06-01: e35712/v11904/p50592 | no | **yes** |
| ex-a | 1 | t2_12 | 2 | The table does not contain information about the day of the week. | - | no | no |
| ex-a | 1 | t2_15 | 2 | The question does not specify which energy sources are considered "Ökostrom" (renewable) and which are "konventionell" (conventional). | - | no | no |
| ex-a | 1 | t3_04 | 3 | The question does not specify a date range or price zone to determine the day electricity was most expensive. | - | no | no |
| ex-a | 1 | t3_05 | 3 | The table does not contain information about the highest and lowest grid load per day. | - | no | no |
| ex-a | 1 | t3_12 | 3 | The table does not contain information about the daily average generation needed for comparison. | - | no | no |
| ex-a | 1 | t4_01 | 4 | The table does not have a direct way to determine the top producer for each week. | - | no | no |
| ex-a | 1 | t4_02 | 4 | The table does not contain information about continuous time intervals with zero solar output. | - | no | no |
| ex-a | 1 | t4_03 | 4 | The tables do not provide hourly aggregated data for generation and consumption. | - | no | no |
| ex-a | 1 | t4_04 | 4 | The table does not contain information about consecutive intervals. | - | no | no |
| ex-a | 1 | u_01 | 0 | The data for Kernenergie is NULL after 2024-01-30, so no nuclear power was produced in June 2025. | 2024-01-30..2024-01-31: e1152/v384/p1632; 2025-06-01..2025-07-01: e34560/v11520/p48960 | yes | no |
| ex-a | 1 | u_02 | 0 | The tables do not contain information about electricity production by region or state such as Bavaria. | - | no | no |
| ex-a | 1 | u_03 | 0 | The question is about future demand, which cannot be answered with the provided historical data. | - | no | no |
| ex-a | 1 | u_04 | 0 | The CO2 emissions data for German electricity generation is missing. | - | no | no |
| ex-a | 1 | u_05 | 0 | The table does not contain information about individual power plants. | - | no | no |
| ex-a | 1 | u_06 | 0 | The installed solar capacity information is missing. | - | no | no |
| ex-a | 1 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| ex-a | 1 | u_08 | 0 | Data for July 2026 is not available. | 2026-07-01..2026-08-01: e0/v0/p0 | no | no |
| ex-a | 2 | t1_25 | 1 | The time period for the total generation of other renewables is not specified. | - | no | no |
| ex-a | 2 | t2_03 | 2 | The table does not contain hourly aggregated data for solar output. | - | no | no |
| ex-a | 2 | t2_12 | 2 | The table does not contain information about the day of the week. | - | no | no |
| ex-a | 2 | t3_04 | 3 | The specific day when electricity was most expensive is not provided. | - | no | no |
| ex-a | 2 | t3_05 | 3 | The table does not contain information about the highest and lowest grid load per day. | - | no | no |
| ex-a | 2 | t3_07 | 3 | Information on which energy sources are considered renewables is missing. | - | no | no |
| ex-a | 2 | t3_11 | 3 | The question requires a comparison of prices based on solar generation, but the tables do not directly link generation levels to price differences. | - | no | no |
| ex-a | 2 | t3_12 | 3 | The table does not contain information about the daily average generation needed to determine how far below the average the lowest total generation was. | - | no | no |
| ex-a | 2 | t4_01 | 4 | The tables do not contain weekly aggregated data or a direct way to determine the top producer for each week. | - | no | no |
| ex-a | 2 | t4_02 | 4 | The table does not contain continuous time intervals or information to determine unbroken stretches. | - | no | no |
| ex-a | 2 | t4_03 | 4 | The tables do not provide hourly aggregated data for generation and consumption. | - | no | no |
| ex-a | 2 | t4_04 | 4 | The table does not contain information about consecutive intervals. | - | no | no |
| ex-a | 2 | u_01 | 0 | The table does not contain data for nuclear power after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| ex-a | 2 | u_02 | 0 | The tables do not contain information about electricity production by region or state such as Bavaria. | - | no | no |
| ex-a | 2 | u_03 | 0 | The question is about future demand predictions, which cannot be answered with the given historical data tables. | - | no | no |
| ex-a | 2 | u_04 | 0 | The CO2 emissions data for German electricity generation is missing. | - | no | no |
| ex-a | 2 | u_05 | 0 | The table does not contain information about individual power plants. | - | no | no |
| ex-a | 2 | u_06 | 0 | The installed solar capacity information is missing from the provided tables. | - | yes | no |
| ex-a | 2 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| ex-a | 2 | u_08 | 0 | Data for July 2026 is not available. | 2026-07-01..2026-08-01: e0/v0/p0 | no | no |
| ex-a | 3 | t1_26 | 1 | The table does not provide a direct way to identify the highest value for Sonnenstrom (solar power) in May 2025. | 2025-05-01..2025-06-01: e35712/v11904/p50592 | no | **yes** |
| ex-a | 3 | t2_12 | 2 | The table does not contain information about the day of the week. | - | no | no |
| ex-a | 3 | t2_15 | 2 | The question does not specify which energy sources are considered "Ökostrom" (renewable) and which are "konventionell" (conventional). | - | no | no |
| ex-a | 3 | t3_04 | 3 | The specific day when electricity was most expensive is not provided. | - | no | no |
| ex-a | 3 | t3_05 | 3 | The table does not contain information about the highest and lowest grid load per day. | - | no | no |
| ex-a | 3 | t3_07 | 3 | The question requires data on total renewable generation, which is not directly available in the tables. | - | no | no |
| ex-a | 3 | t3_11 | 3 | The question requires a comparison of prices based on solar generation, but the tables do not directly link generation and prices for specific intervals. | - | no | no |
| ex-a | 3 | t3_12 | 3 | The table does not provide information on daily average generation. | - | no | no |
| ex-a | 3 | t4_01 | 4 | The tables do not contain weekly aggregated data or a direct way to determine the top producer for each week. | - | no | no |
| ex-a | 3 | t4_02 | 4 | The table does not contain information about continuous time periods or stretches of zero solar output. | - | no | no |
| ex-a | 3 | t4_03 | 4 | The tables do not provide hourly aggregated data for generation and consumption. | - | no | no |
| ex-a | 3 | t4_04 | 4 | The table does not contain information about consecutive intervals. | - | no | no |
| ex-a | 3 | u_01 | 0 | The table does not contain data for nuclear power generation after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| ex-a | 3 | u_02 | 0 | The tables do not contain information about electricity production by region or state such as Bavaria. | - | no | no |
| ex-a | 3 | u_03 | 0 | The table does not contain future data to predict next winter's demand. | - | no | no |
| ex-a | 3 | u_04 | 0 | The CO2 emissions data for German electricity generation is missing. | - | no | no |
| ex-a | 3 | u_05 | 0 | The table does not contain information about individual power plants. | - | no | no |
| ex-a | 3 | u_06 | 0 | The installed solar capacity information is missing from the provided tables. | - | yes | no |
| ex-a | 3 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| ex-a | 3 | u_08 | 0 | Data for July 2026 is not available. | 2026-07-01..2026-08-01: e0/v0/p0 | no | no |
| ex-b | 1 | t1_12 | 1 | The table does not contain data for the year 2026. | 2026-01-01..2027-01-01: e175056/v58352/p247996 | no | **yes** |
| ex-b | 1 | t1_19 | 1 | The term "Speicherkraftwerken" is ambiguous and not clearly defined in the provided tables. | - | no | no |
| ex-b | 1 | t1_22 | 1 | The exact price at midday on 3 March 2025 is missing. | 2025-03-03..2025-03-04: e1152/v384/p1632 | no | **yes** |
| ex-b | 1 | t2_01 | 2 | The time period for the query is not specified. | - | no | no |
| ex-b | 1 | t2_03 | 2 | The table does not contain information about hourly solar output. | - | no | no |
| ex-b | 1 | t2_11 | 2 | The question is missing. | - | no | no |
| ex-b | 1 | t2_18 | 2 | The table does not contain information about the year for each timestamp. | - | no | no |
| ex-b | 1 | t3_04 | 3 | The specific day when electricity was most expensive is not provided. | - | no | no |
| ex-b | 1 | t3_05 | 3 | The table does not contain daily maximum and minimum grid load values needed to calculate the swing. | - | no | no |
| ex-b | 1 | t3_07 | 3 | The share of consumption covered by renewables requires data on renewable generation and total consumption, but the tables do not directly provide this comparison. | - | no | no |
| ex-b | 1 | t3_09 | 3 | The question requires identifying the windiest day, which needs additional data or calculations not provided in the tables. | - | no | no |
| ex-b | 1 | t3_10 | 3 | The table does not contain information about the total electricity generation for all energy sources. | - | no | no |
| ex-b | 1 | t3_11 | 3 | The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to correlate solar generation with prices. | - | no | no |
| ex-b | 1 | t3_12 | 3 | The table does not provide information on daily averages for comparison. | - | no | no |
| ex-b | 1 | t4_01 | 4 | The question requires identifying the top producer per week, but the necessary logic to determine the top producer is not specified. | - | no | no |
| ex-b | 1 | t4_02 | 4 | The table does not contain information about unbroken stretches or durations. | - | no | no |
| ex-b | 1 | t4_03 | 4 | The tables do not provide a direct way to compare total generation and consumption for each hour. | - | no | no |
| ex-b | 1 | t4_04 | 4 | Information about consecutive quarter-hours is missing. | - | no | no |
| ex-b | 1 | u_01 | 0 | There is no nuclear power data available after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| ex-b | 1 | u_02 | 0 | The tables do not contain information about electricity production by region or state such as Bavaria. | - | no | no |
| ex-b | 1 | u_03 | 0 | Future demand predictions require data not present in the table. | - | no | no |
| ex-b | 1 | u_04 | 0 | The CO2 emissions data is not available in the provided tables. | - | no | no |
| ex-b | 1 | u_05 | 0 | The table does not contain information about specific power plants. | - | no | no |
| ex-b | 1 | u_06 | 0 | The installed solar capacity information is missing from the provided tables. | - | yes | no |
| ex-b | 1 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| ex-b | 2 | t1_12 | 1 | Data for February 2026 is not available in the table. | 2026-02-01..2026-03-01: e32256/v10752/p45696 | no | **yes** |
| ex-b | 2 | t1_19 | 1 | The term "Speicherkraftwerken" is ambiguous and not directly represented in the tables. | - | no | no |
| ex-b | 2 | t1_22 | 1 | The specific timestamp for midday on 3 March 2025 is missing. | 2025-03-03..2025-03-04: e1152/v384/p1632 | no | **yes** |
| ex-b | 2 | t2_03 | 2 | The table does not contain information about hourly solar output. | - | no | no |
| ex-b | 2 | t2_15 | 2 | The question does not specify which energy sources are considered "Ökostrom" and which are "konventionell". | - | no | no |
| ex-b | 2 | t2_18 | 2 | The table does not contain information about the year for each timestamp. | - | no | no |
| ex-b | 2 | t3_04 | 3 | The specific day when electricity was most expensive is not provided. | - | no | no |
| ex-b | 2 | t3_05 | 3 | The table does not contain daily aggregated data to calculate the swing between highest and lowest grid load for each day. | - | no | no |
| ex-b | 2 | t3_07 | 3 | The table does not provide direct information on which energy sources are considered renewables. | - | no | no |
| ex-b | 2 | t3_09 | 3 | The date of the windiest day for onshore wind is missing. | - | no | no |
| ex-b | 2 | t3_10 | 3 | The table does not contain information about the total electricity generation for all energy sources. | - | no | no |
| ex-b | 2 | t3_11 | 3 | The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to compare prices with solar generation levels. | - | no | no |
| ex-b | 2 | t3_12 | 3 | The table does not provide information on daily averages for comparison. | - | no | no |
| ex-b | 2 | t4_01 | 4 | The question requires weekly aggregation, but the table does not have a direct way to determine the top producer per week without additional context or data. | - | no | no |
| ex-b | 2 | t4_03 | 4 | The tables do not provide direct information on hourly generation versus consumption comparison. | - | no | no |
| ex-b | 2 | t4_04 | 4 | Information about consecutive quarter-hours is missing. | - | no | no |
| ex-b | 2 | u_01 | 0 | There is no nuclear power production data after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| ex-b | 2 | u_02 | 0 | The tables do not contain information about electricity production by region or state such as Bavaria. | - | no | no |
| ex-b | 2 | u_03 | 0 | Future demand predictions require forecasting models or additional data not present in the table. | - | no | no |
| ex-b | 2 | u_04 | 0 | The CO2 emissions data is not available in the provided tables. | - | no | no |
| ex-b | 2 | u_05 | 0 | The table does not contain information about specific power plants. | - | no | no |
| ex-b | 2 | u_06 | 0 | The installed solar capacity information is missing. | - | no | no |
| ex-b | 2 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| ex-b | 3 | t1_12 | 1 | The table does not contain data for the year 2026. | 2026-01-01..2027-01-01: e175056/v58352/p247996 | no | **yes** |
| ex-b | 3 | t1_22 | 1 | The specific timestamp for midday on 3 March 2025 is missing. | 2025-03-03..2025-03-04: e1152/v384/p1632 | no | **yes** |
| ex-b | 3 | t2_03 | 2 | The table does not have information on hourly solar output. | - | no | no |
| ex-b | 3 | t2_11 | 2 | The question does not specify the energy sources to be included. | - | no | no |
| ex-b | 3 | t2_15 | 2 | The question does not specify which energy sources are considered "Ökostrom" and which are "konventionell". | - | no | no |
| ex-b | 3 | t2_18 | 2 | The table does not contain information about the year for each timestamp. | - | no | no |
| ex-b | 3 | t3_04 | 3 | The specific day when electricity was most expensive is not provided. | - | no | no |
| ex-b | 3 | t3_05 | 3 | The table does not contain daily high and low grid load values to calculate the swing. | - | no | no |
| ex-b | 3 | t3_07 | 3 | The question requires data on renewable generation, which is not directly available in the tables. | - | no | no |
| ex-b | 3 | t3_09 | 3 | The specific date of the windiest day for onshore wind is missing. | - | no | no |
| ex-b | 3 | t3_10 | 3 | The table does not contain information about the total electricity generation for all energy sources. | - | no | no |
| ex-b | 3 | t3_11 | 3 | The question requires a comparison of prices based on solar generation, but the tables do not provide a direct way to correlate solar generation with prices. | - | no | no |
| ex-b | 3 | t3_12 | 3 | The table does not provide information on daily averages for comparison. | - | no | no |
| ex-b | 3 | t4_01 | 4 | The question requires weekly aggregation of generation data, which is not directly available in the tables. | - | no | no |
| ex-b | 3 | t4_02 | 4 | The table does not contain information about unbroken stretches or durations. | - | no | no |
| ex-b | 3 | t4_03 | 4 | The tables do not provide direct information on hourly generation versus consumption comparison. | - | no | no |
| ex-b | 3 | t4_04 | 4 | Information about consecutive quarter-hours is missing. | - | no | no |
| ex-b | 3 | u_01 | 0 | There is no nuclear power production data after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| ex-b | 3 | u_02 | 0 | The tables do not contain information about electricity production by region or state such as Bavaria. | - | no | no |
| ex-b | 3 | u_03 | 0 | Future demand predictions require forecasting models or additional data not present in the table. | - | no | no |
| ex-b | 3 | u_04 | 0 | Emission factors for each energy source are missing. | - | no | no |
| ex-b | 3 | u_05 | 0 | The table does not contain information about specific power plants. | - | no | no |
| ex-b | 3 | u_06 | 0 | The installed solar capacity information is missing. | - | no | no |
| ex-b | 3 | u_07 | 0 | The DE/AT/LU zone has no data (all NULL) in the dataset. | - | no | no |
| v2b_fresh | 1 | u_01 | 0 | There is no data for nuclear power after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| v2b_fresh | 1 | u_02 | 0 | The tables do not contain information specific to Bavaria's electricity production. | - | no | no |
| v2b_fresh | 1 | u_03 | 0 | Future demand data is not available in the table. | - | no | no |
| v2b_fresh | 1 | u_04 | 0 | Emission factors for each energy source are missing. | - | no | no |
| v2b_fresh | 1 | u_05 | 0 | The table does not contain information about specific power plants. | - | no | no |
| v2b_fresh | 1 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| v2b_fresh | 1 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| v2b_fresh | 2 | u_01 | 0 | There is no data for nuclear power after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| v2b_fresh | 2 | u_02 | 0 | The tables do not contain information specific to Bavaria's electricity production. | - | no | no |
| v2b_fresh | 2 | u_03 | 0 | Future demand data is not available in the table. | - | no | no |
| v2b_fresh | 2 | u_04 | 0 | Emission factors for each energy source are missing. | - | no | no |
| v2b_fresh | 2 | u_05 | 0 | The table does not contain information about specific power plants. | - | no | no |
| v2b_fresh | 2 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| v2b_fresh | 2 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| v2b_fresh | 3 | u_01 | 0 | There is no data for nuclear power after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| v2b_fresh | 3 | u_02 | 0 | The tables do not contain information specific to Bavaria's electricity production. | - | no | no |
| v2b_fresh | 3 | u_03 | 0 | Future demand data is not available in the table. | - | no | no |
| v2b_fresh | 3 | u_04 | 0 | The CO2 emissions data for each energy source is missing. | - | no | no |
| v2b_fresh | 3 | u_05 | 0 | The table does not contain information about specific power plants. | - | no | no |
| v2b_fresh | 3 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| v2b_fresh | 3 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| R2 | 1 | u_01 | 0 | Data for nuclear power after January 2024 is NULL. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| R2 | 1 | u_02 | 0 | The tables do not contain information specific to Bavaria's electricity production. | - | no | no |
| R2 | 1 | u_03 | 0 | Future demand data is not available in the table. | - | no | no |
| R2 | 1 | u_04 | 0 | Emission factors for each energy source are missing. | - | no | no |
| R2 | 1 | u_05 | 0 | The table does not contain information about specific power plants, only energy sources. | - | no | no |
| R2 | 1 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| R2 | 1 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| R2 | 2 | u_01 | 0 | There is no data for nuclear power after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| R2 | 2 | u_02 | 0 | The tables do not contain information specific to Bavaria's electricity production. | - | no | no |
| R2 | 2 | u_03 | 0 | Future demand predictions require forecasting models or additional data not present in the table. | - | no | no |
| R2 | 2 | u_04 | 0 | Emission factors for each energy source are missing. | - | no | no |
| R2 | 2 | u_05 | 0 | The table does not contain information about specific power plants, only energy sources. | - | no | no |
| R2 | 2 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| R2 | 2 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |
| R2 | 3 | u_01 | 0 | There is no data for nuclear power after January 2024. | 2024-01-01..2024-02-01: e35712/v11904/p50592 | yes | no |
| R2 | 3 | u_02 | 0 | The tables do not contain information specific to Bavaria's electricity production. | - | no | no |
| R2 | 3 | u_03 | 0 | Future demand predictions are not available in the provided data. | - | no | no |
| R2 | 3 | u_04 | 0 | Emission factors for each energy source are missing. | - | no | no |
| R2 | 3 | u_05 | 0 | The table does not contain information about specific power plants, only energy sources. | - | no | no |
| R2 | 3 | u_06 | 0 | The table does not contain information about installed solar capacity. | - | no | no |
| R2 | 3 | u_07 | 0 | The DE/AT/LU zone has no price data in the dataset. | - | no | no |

## 3b. Empty final results in v2b_fresh and R2 (and u_08 attempt-1 SQL)

| Row | Run | Id | Tier | SQL | Result | Period found in the SQL, rows (e/v/p) | Empty fact fires |
|---|---:|---|---:|---|---|---|---|
| v2b_fresh | 1 | t4_03 | 4 | final | 0 rows | - | no |
| v2b_fresh | 1 | u_08 | 0 | final | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| v2b_fresh | 2 | t4_03 | 4 | final | 0 rows | - | no |
| v2b_fresh | 2 | u_08 | 0 | final | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| v2b_fresh | 3 | u_08 | 0 | final | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 1 | t4_03 | 4 | final | 0 rows | - | no |
| R2 | 1 | u_08 | 0 | final = attempt 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 2 | t4_03 | 4 | final | 0 rows | - | no |
| R2 | 2 | u_08 | 0 | final = attempt 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 3 | t4_03 | 4 | final | 0 rows | - | no |
| R2 | 3 | u_08 | 0 | final = attempt 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |

## How the tier-0 safety works (read this before building R3)

Of the 111 tier-0 declines in these files, 90 name no period at all (for example Bavaria, CO2, power plants, installed capacity, DE/AT/LU, "future demand"), 15 name a period but use open-ended wording ("after January 2024", all of them u_01, nuclear power), and 6 name a period that really has no rows (u_08, "Data for July 2026 is missing"). So 15 correct declines are protected only by the open-ended word rule. The rows-per-table test does not protect u_01: June 2025 has rows in every table, because other energy sources have values. A reason such as "There is no nuclear power data for June 2025." would make the review fire and send a correct decline back. None of the 111 replies is worded that way, but it is a gap to keep in mind (a possible extra test: look for values of the named energy source, not for rows in the table).

## What the dry run shows

- The review would fire on 21 of the 30 false declines in df, 2 of 35 in ex-a and 6 of 51 in ex-b, and on none of the tier-0 declines, in any row.
- It catches only date claims. The false declines of ex-a and ex-b are mostly "the table has no information about ..." (day of the week, hourly data, consecutive intervals) and name no period (33 of 35 and 45 of 51 not caught). v2b_fresh and R2 have no false declines at all, so on the current base the review has nothing to fix.
- Not caught in df: t1_19 (Speicherkraftwerken, 3), t4_04 (3), t3_04, t3_12, and t1_17 run 3, whose reason mentions "after 2024-01-30" (open-ended).
- The empty fact fires on u_08 in all 6 runs (v2b_fresh and R2; period 2026-07-01 to 2026-08-01, no rows in any table), and it does not fire on t4_03 (0 rows, but the SQL has no condition on zeitpunkt).
