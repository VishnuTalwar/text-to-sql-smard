# Answer columns: draft for review (2026-11-06)

Rules: `results/answer_columns_rules_2026-11-06.md`. Data: `grader/answer_columns.yaml`. Drafted from the question text, the gold SQL and the gold result column names only. **No results file was opened**, so the marking is blind to what any agent answered. `gold_set_smard.yaml` and the held-out files were not touched.

## Summary

- Items with SQL: **76**.
- All gold columns required (no change from the strict column check): **59**.
- Fewer columns required than the gold has: **17**.
- With alternatives (rule 6): **4** (t3_06, t3_12, t4_02, t4_04).
- Items in the table below (fewer columns or alternatives): **17**. Items I was unsure about: **11** entries (list further down).

| Tier | Items | All gold columns required | Fewer required | With alternatives |
|---|---:|---:|---:|---:|
| 1 | 35 | 35 | 0 | 0 |
| 2 | 25 | 20 | 5 | 0 |
| 3 | 12 | 4 | 8 | 2 |
| 4 | 4 | 0 | 4 | 2 |
| **all** | **76** | **59** | **17** | **4** |

Tier 1 (35 items) is one value each, so nothing changes there. Fewer required columns occur in tiers 2 to 4 only (17 items); most are "which" questions where the gold also carries the value it was chosen by (rule 1).

## Items where required differs from the gold columns, or alternatives exist

`alternatives`: any one list of columns counts instead of `required`. Columns of the gold that are neither required nor in an alternative are optional.

| id | question | gold columns | required | alternatives | reason |
|---|---|---|---|---|---|
| t2_01 | Which energy source produced the most overall? | energietraeger, mwh | energietraeger | - | rule 1: "Which energy source produced the most overall?" names no amount; mwh optional |
| t2_06 | Which price zone had the highest average price over the whole period? | preiszone, eur_mwh | preiszone | - | rule 1: "Which price zone had the highest average price"; the price is only the criterion |
| t2_09 | Which month had the highest total solar production? | monat, mwh | monat | - | rule 1: "Which month had the highest total solar production?"; no amount asked |
| t2_12 | Which day of the week has the highest average consumption? | wochentag, mwh | wochentag | - | rule 1: "Which day of the week has the highest average consumption?"; no amount asked |
| t2_20 | Which quarter of 2025 had the most onshore wind? | quartal, mwh | quartal | - | rule 1: "Which quarter of 2025 had the most onshore wind?"; no amount asked |
| t3_01 | Which single day had the highest total solar production? | tag, mwh | tag | - | rule 1: "Which single day had the highest total solar production?"; no amount asked |
| t3_04 | On the day electricity was most expensive, what was the generation mix? | tag, energietraeger, mwh | energietraeger, mwh | - | rule 5: "what was the generation mix?" asks for the mix; the date (tag) only identifies the day and is not asked for |
| t3_05 | Which day had the biggest swing between its highest and lowest grid load? | tag, spanne_mwh | tag | - | rule 1: "Which day had the biggest swing"; no amount asked |
| t3_06 | How did solar in 2025 compare to 2024, in absolute terms and percent? | mwh_2024, mwh_2025, differenz_mwh, veraenderung_prozent | differenz_mwh, veraenderung_prozent | [mwh_2024, mwh_2025, veraenderung_prozent] | rules 2 and 6: "in absolute terms and percent"; "absolute" read as the difference, or as the two yearly totals |
| t3_07 | What share of consumption was covered by renewables in 2025? | erneuerbar_mwh, netzlast_mwh, deckung_prozent | deckung_prozent | - | rules 2 and 5: "What share of consumption was covered by renewables"; the two parts of the ratio are optional |
| t3_09 | On the windiest day for onshore wind, what was the average German price? | tag, eur_mwh | eur_mwh | - | rules 2 and 5: "what was the average German price?"; the day is identified by description and not asked for |
| t3_11 | In 2025, was the price different in quarter-hours with a lot of solar, say above 5000 MWh, compared to the rest? | gruppe, n, eur_mwh | gruppe, eur_mwh | - | rules 2 and 5: "was the price different in quarter-hours with a lot of solar ... compared to the rest?"; the count n is optional |
| t3_12 | Which day had the lowest total generation, and how far below the daily average was it? | tag, tages_mwh, durchschnitt_mwh, abweichung_prozent | tag, abweichung_prozent | [tag, tages_mwh, durchschnitt_mwh] | rules 3 and 6: "Which day had the lowest total generation, and how far below the daily average was it?"; "how far" as percent, or as the absolute gap from the day total and the average |
| t4_01 | For each week, which source was the top producer? | woche, energietraeger, mwh | woche, energietraeger | - | rules 1 and 4: "For each week, which source was the top producer?"; week and source, no amount asked |
| t4_02 | What was the longest unbroken stretch where solar output was zero? | beginn, ende, viertelstunden, stunden | viertelstunden | [stunden]; [beginn, ende] | rules 5 and 6: "What was the longest unbroken stretch"; read as the length (quarter-hours or hours) or as the period (beginn, ende) |
| t4_03 | Which hours had more generation than consumption? | stunde, erzeugt, verbraucht, ueberschuss_mwh | stunde | - | rule 1: "Which hours had more generation than consumption?"; no amount asked |
| t4_04 | What was the longest run of consecutive quarter-hours with a negative German price? | beginn, ende, viertelstunden, stunden | viertelstunden | [stunden] | rules 5 and 6: "What was the longest run of consecutive quarter-hours"; the length, in quarter-hours or hours; start and end optional |

## Items I was unsure about

For each: the two readings, and which one the draft uses. Tell me if you read one differently; the YAML is one line to change.

- **t2_07**: Break down 2025 generation by source and show each one's share in percent.
  - Readings: A: amount (mwh) and share both required (all three columns). B: only the source and the share required, because only the share is named explicitly.
  - Draft: A: "break down generation by source" is itself a request for the amounts.
- **t3_04**: On the day electricity was most expensive, what was the generation mix?
  - Readings: A: tag optional, because the question asks for the mix, not for the date. B: tag required, because the day is only known through the query and the reader cannot know it.
  - Draft: A: rule 5, the day is fixed by the question's description.
- **t3_09**: On the windiest day for onshore wind, what was the average German price?
  - Readings: A: only the price required, the day is identified by description. B: tag also required, same argument as t3_04.
  - Draft: A: the question asks "what was the average price".
- **t3_06**: How did solar in 2025 compare to 2024, in absolute terms and percent?
  - Readings: A: "absolute" = the difference (differenz_mwh) plus the percent. B: "absolute" = the two yearly totals (mwh_2024, mwh_2025) plus the percent.
  - Draft: Both listed (A required, B as an alternative); the percent column is required in both.
- **t3_12**: Which day had the lowest total generation, and how far below the daily average was it?
  - Readings: A: "how far" = percent (abweichung_prozent). B: "how far" = the absolute gap in MWh, which is not a gold column; it follows from tages_mwh and durchschnitt_mwh.
  - Draft: Both listed. The alternative needs the day total and the average, since no gold column holds the difference itself; whether a single computed difference column should also count is a question for the comparator design.
- **t4_02**: What was the longest unbroken stretch where solar output was zero?
  - Readings: A: the length (viertelstunden, or stunden in hours). B: the period itself (beginn and ende).
  - Draft: A required with stunden as an alternative, B as another alternative.
- **t4_04**: What was the longest run of consecutive quarter-hours with a negative German price?
  - Readings: A: the length (viertelstunden / stunden). B: the period (beginn, ende), as in t4_02.
  - Draft: Only A listed: a run counted in quarter-hours is a length. Add the period as an alternative if you read it as in t4_02.
- **t3_08**: Was power more expensive on weekends or on weekdays in 2025?
  - Readings: A: both columns required (the two prices are what is compared; the gold has two rows and the order is the answer). B: only typ required (a "which of two" question, rule 1), price optional.
  - Draft: A: it is a comparison, like t3_03.
- **t4_01**: For each week, which source was the top producer?
  - Readings: A: week and source required, mwh optional (rules 1 and 4: the question asks which source). B: mwh also required, because it is a per-week listing and rule 4 asks for the value it is listed by.
  - Draft: A: the listed item is the source; the amount is only the criterion.
- **t2_14 / t2_05**: Which 5 quarter-hours had the most expensive German power ever? / What were the top 3 sources ...
  - Readings: A: a top-N with N > 1 is a ranking (rule 4), so label and value are required. B: it is a "which" question (rule 1), so only the label is required.
  - Draft: A. A top-1 ("Which source produced the most overall?") is treated as a "which" question, a top-N with N > 1 as a ranking.
- **t3_11**: In 2025, was the price different in quarter-hours with a lot of solar, say above 5000 MWh, compared to the rest?
  - Readings: A: group and price required, the count n optional (rule 5). B: n also required, since the counts show how many quarter-hours each group has.
  - Draft: A: the question asks about the price.

## Also worth knowing

- The rules say nothing about a single computed column that the gold does not have (for example the absolute gap in t3_12). The draft names such a case through the gold columns it follows from; whether a computed column should count is a design question for the comparator (part 2).
- Required columns are only a list of names. How an answer's columns are matched to them (by name, by position, by value) is not decided here.
