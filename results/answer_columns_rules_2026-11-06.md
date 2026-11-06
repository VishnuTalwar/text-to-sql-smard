# Rules for the required answer columns (D40 step 4, draft, 2026-11-06)

Purpose: the answer-correctness score checks the columns an answer must contain, instead of demanding every column of the gold query. The marking in `grader/answer_columns.yaml` was drafted from the question text and the gold SQL / gold result columns only, blind to every agent answer (no results file was opened).

## The rules

1. A "which" question (which zone, day, source, hour, ...): the label column is required; the value it was chosen by is optional unless the question also asks "how much / how high / what was".
2. A "how much / what was / how high" question: the value column is required.
3. "Which ... and how much/how far/what": both are required.
4. Rankings, ordered lists and "for each / per / month by month" questions: the label (or time bucket) and the value it is ranked or listed by are required; order counts where reihenfolge_relevant is true.
5. Context the question does not ask for (counts such as n, the parts of a ratio, start/end of a run when the question asks for its length, the date of a day the question already fixes) is optional.
6. If the question is honestly ambiguous between two measures (for example absolute vs percent), list both as alternatives; either one counts.
7. Required columns are named by their gold column names.

## Worked examples (from the gold items)

1. **t2_09**, "Which month had the highest total solar production?" Gold columns: `monat`, `mwh`. Required: `monat`. The `mwh` the month was chosen by is optional, because the question asks which month and not how much.
2. **t1_05**, "What was the average grid load in 2024?" Gold column: `mwh`. Required: `mwh`. **t2_18**, "How many negative-price quarter-hours were there each year?": the value asked is the count, so `n` is required (together with `jahr`, by rule 4).
3. **t3_12**, "Which day had the lowest total generation, and how far below the daily average was it?" Required: `tag` (which day) and `abweichung_prozent` (how far). Both are required. The day total and the average (`tages_mwh`, `durchschnitt_mwh`) are optional context.
4. **t2_04**, "Give me total generation per month for 2025." Required: `monat` and `mwh`. **t2_02**, "Rank all sources by total output in July 2025": required `energietraeger` and `mwh`, and because `reihenfolge_relevant` is true for t2_02 the order of the rows counts too.
5. **t3_07**, "What share of consumption was covered by renewables in 2025?" Gold columns: `erneuerbar_mwh`, `netzlast_mwh`, `deckung_prozent`. Required: `deckung_prozent`. The two parts of the ratio are optional. **t4_04**, "What was the longest run of consecutive quarter-hours with a negative German price?": the question asks for the length, so `beginn` and `ende` are optional.
6. **t3_06**, "How did solar in 2025 compare to 2024, in absolute terms and percent?" The percent is clear, but "absolute" can mean the difference or the two yearly totals. Required: `differenz_mwh` and `veraenderung_prozent`; alternative: `mwh_2024`, `mwh_2025` and `veraenderung_prozent`. An answer counts if it has the required columns or all columns of one alternative.
7. **t2_09** again: the required column is called `monat`, as in the gold, not "month" and not "the month column". The agent's own column names do not have to match; how an answer is matched to the names is a question for the comparator, not for these rules.

## How I applied the rules to borderline shapes

These are my reading of the rules, not additions to them; the items where it matters are in the review file.

- A top-1 question ("Which source produced the most overall?", t2_01) is a "which" question (rule 1). A top-N with N > 1 ("Which 5 quarter-hours had the most expensive ...", t2_14; "the top 3 sources", t2_05) is a ranking (rule 4), so label and value are required.
- Comparison questions ("Compare June against July", t3_03; "weekends or weekdays", t3_08; "price different with a lot of solar compared to the rest", t3_11) need the label and the value that is compared.
- A day that the question only describes ("the day electricity was most expensive", "the windiest day") and asks something else about: its date is optional (rule 5, "the date of a day the question already fixes"). t3_04 and t3_09. This is the least certain application.
- "For each week, which source was the top producer?" (t4_01): the bucket (`woche`) and the label (`energietraeger`) are required; the amount is the criterion and optional (rules 1 and 4).
- `alternatives` in the YAML: an answer counts if it contains all of `required`, or all columns of any one list in `alternatives`. All other gold columns are optional.
