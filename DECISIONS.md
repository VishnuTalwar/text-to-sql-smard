Design decisions, in the order they were made. Each entry: the decision, why, and evidence if any.

## D1. Long format, not wide
**Decision:** Long format, not wide.
**Why:** Cross-source comparison becomes one clean query instead of an unwritable one

## D2. PostgreSQL in Docker, not SQLite/DuckDB
**Decision:** PostgreSQL in Docker, not SQLite/DuckDB.
**Why:** Keeps the read-only account, which is the strongest safety argument in the design

## D3. German column names, English descriptions in the catalog
**Decision:** German column names, English descriptions in the catalog.
**Why:** Realistic; makes the catalog do real work; supports the bilingual story

## D4. Benchmark written before the agent
**Decision:** Benchmark written before the agent.
**Why:** Otherwise every later change is a guess and the first score has nothing to compare to

## D5. Store gold SQL, not gold answers
**Decision:** Store gold SQL, not gold answers.
**Why:** Stored answers go stale on reload; stored queries re-run and stay correct

## D6. Compare result sets, not query text
**Decision:** Compare result sets, not query text.
**Why:** Many different queries give the same correct answer; string matching measures style, not correctness

## D7. AST inspection, not regex, for query validation
**Decision:** AST inspection, not regex, for query validation.
**Why:** Regex on SQL is bypassed by comments and nesting — and knowing why is an interview answer

## D8. Read-only DB role as the last line of defence
**Decision:** Read-only DB role as the last line of defence.
**Why:** Defence in depth; the database itself refuses to do damage

## D9. Retries capped at three
**Decision:** Retries capped at three.
**Why:** Prevents infinite loops on bad questions; makes retry rate a usable signal

## D10. Always show the generated SQL
**Decision:** Always show the generated SQL.
**Why:** Trust. Anyone who reads SQL will not trust an answer they cannot verify

## D11. Drop the `Datum bis` column
**Decision:** Drop the `Datum bis` column.
**Why:** Always exactly +15 minutes; one less thing for the model to misread

## D12. Read-only database role deferred as tech debt
**Decision:** Read-only database role deferred as tech debt.
**Why:** The grader already uses the read-only role `grader_ro`. The live agent has no safe runner yet, and must have one before it runs queries.
**Status:** Open (O11).

## D13. t2_14 tiebreaker
**Decision:** The gold SQL for t2_14 sorts by `preis_eur_mwh DESC NULLS LAST, zeitpunkt` (earliest first) with `LIMIT 5`. It keeps `reihenfolge_relevant: true` and has a `hinweis` saying the tiebreaker is only for reproducibility.
**Why:** Prices tied at 5th place made the order random. It is a ranking question, so order matters; switching to a set comparison would quietly test a weaker question. t2_21 is different (ties at a filter cutoff) and stays order-insensitive.
**Evidence:** The `hinweis` on t2_14 in `gold_set_smard.yaml`.

## D14. Model locked to gpt-4o for every stage
**Decision:** gpt-4o is used for every stage, via the OpenAI API.
**Why:** If the model changed between stages, a score change could come from the model instead of the pipeline, and the ablation table would stop being honest.

## D15. Naive baseline contains zero data-quirk hints
**Decision:** The naive baseline prompt has no hints about data quirks.
**Why:** The quirk notes are what schema linking adds. Putting them in the baseline would hide their effect and make the ablation dishonest.

## D16. Data quirks go into the schema catalog, not the example bank
**Decision:** Quirks are written as notes in the schema catalog.
**Why:** The example bank is for showing query patterns. One-off facts about the data belong with the table descriptions.

## D17. Table retrieval uses keyword matching, not embeddings
**Decision:** Keyword matching picks which tables to show. When it is unclear, all tables are shown.
**Why:** With only 3 tables, vector search adds complexity without a real benefit.
**Evidence:** Retrieval picked the right tables on all 84 questions.

## D18. The MWh/MW catalog note was reworded after it caused an 11-point drop
**Decision:** The old note told the model to multiply by 4 for load, and it did so on almost every question (35/84 vs 46/84 baseline). The new wording says: report MWh as stored, and only multiply by 4 if the question explicitly asks for MW or power.
**Result:** 47/84, with 11 of the 12 regressions fixed.
**Evidence:** `results/schema_linked_2026-10-20.log` (keep it) and `results/schema_linked_mwh_reworded_2026-10-20.log`.
**Lesson:** An ambiguous note can hurt more than no note.

## D19. The comparator stays strict on column count, for now
**Decision:** An answer with a different number of columns than the gold fails.
**Why:** It keeps grading simple and predictable.
**Known cost:** Answers with correct logic but a different shape fail. Example: t2_01 returns only the name, while the gold returns name and total. To be revisited later.

## D20. Every ablation row is measured at temperature 0, over 3 runs, reporting the mean
**Decision:** Each configuration is run 3 times at temperature 0 and the mean is reported.
**Why:** Single runs wobble by about 2 points, which is bigger than some effects we want to measure. The early single-sample numbers (46, 35, 47) are not comparable and will not appear in the final ablation table.
**Evidence:** `results/*_t0_run{1,2,3}_2026-10-21.log`. Naive mean 46.00, schema-linked mean 46.67, a gap smaller than the noise.

## D21. The grid-load answer unit is MWh only (resolves open item O6)
**Decision:** Grid-load questions are answered in raw MWh, not MW.
**Why:** The gold SQL returns raw MWh, and the catalog note now says to report MWh as stored.

## D22. Decline option added on top of schema-linked
**Decision:** If the question cannot be answered from the tables, the model replies "NO_QUERY: <reason>". The original "return only the SQL" sentence is kept word for word (only "Return" becomes "return" after "Otherwise,"); only the decline sentence and "Otherwise," were added, so this row is one change.
**Why:** Tier 0 scored 0/8 in every earlier run because the prompt never told the model that declining was allowed. That is an instruction gap no schema note can fix, and declining instead of guessing is what a trustworthy assistant should do.
**Evidence:** `results/schema_linked_decline_t0_run{1,2,3}_2026-10-24.log`. Mean 55.33 vs 46.67 for schema-linked. Tier 0 went from 0/8 to 7/8 in every run (clean). Tiers 1-4 moved +1.67 (per run 48, 48, 49 vs 46, 48, 46), too small to separate from run-to-run noise; it comes from consistent style changes in both directions (5 questions better, 3 worse). Wrong declines: t1_22 in 2 of 3 runs ("midday" seen as ambiguous). u_08 (July 2026) was never declined, likely because nothing tells the model where the data ends (interpretation, not tested).

## D23. Kernenergie note reworded to talk about aggregates (row v2a)
**Decision:** The note now says that any SUM, AVG or MAX of Kernenergie after 2024-01-30 is NULL and that rankings by a total need ORDER BY <total> DESC NULLS LAST. Only this one note changed.
**Why:** The old note said "this column", but the model sorts by its own SUM, so it likely did not see the note as applying (Step D in `PROJECT_PROGRESS.md`). Catalog v2 is split into three rows (v2a, v2b, v2c) so each change can be measured on its own.
**Evidence:** `results/v2a_t0_run{1,2,3}_2026-10-27.log`. Mean 59.67 vs 55.33. t2_05 and t2_22 went from 0/3 to 3/3 with NULLS LAST added (+2.00, clean). NULLS LAST now appears on 8 ranking questions instead of 1. The other +2.33 (t1_02, t2_09, t3_06) are likely side effects of the rewording. The 28 questions with unchanged prompts netted exactly 0. t1_22 is now wrongly declined in 3/3 runs ("no data for 2025") with an unchanged prompt, so not caused by this row.

## D24. t2_25 gold: "neighbours" = the 11 zones in ∅ Anrainer DE/LU
**Decision:** The gold SQL for t2_25 now ranks exactly these 11 zones: Belgien, Dänemark 1, Dänemark 2, Frankreich, Niederlande, Norwegen 2, Österreich, Polen, Schweden 4, Schweiz, Tschechien. Year 2025, ORDER BY the average DESC and `reihenfolge_relevant: true` are unchanged. `gold_zeilen` is 11 (was 14), `gold_antwort` is updated, and a `hinweis` explains that "neighbours" follows the 11 zones used in '∅ Anrainer DE/LU'.
**Why:** The question asks for "the neighbouring countries", but the old gold ranked 14 zones, including Italien (Nord), Slowenien and Ungarn, which do not border Germany. The data's own neighbour set, the 11 zones averaged in '∅ Anrainer DE/LU' (checked on 26 Oct: it matches in all 105,312 timestamps, against 0.1% when the three extra zones are added), excludes them.
**Evidence:** The self-test still scores 84/84, and only t2_25 differs between the old and new gold file. t2_25 was re-graded against the new gold for all 15 earlier runs that stored its SQL (naive 4, schema-linked 5, decline 3, v2a 3). It failed in every one before and after (row count 14 or 15 against 11), so no earlier score changed.

## D25. Plain descriptions of the metrik and preiszone values (row v2b)
**Decision:** On top of v2a, the catalog now says what each metrik value and each preiszone value means, in a new "Value meanings" section under the values line (shown by a new prompt template, `prompt_template_v2b.py`). "grid load" is for general questions about consumption, demand or load. "Deutschland/Luxemburg" is the German price zone. "∅ Anrainer DE/LU" is not a market zone but the average of Germany's 11 neighbouring zones, to be left out when ranking or comparing zones. "DE/AT/LU" is the old, empty joint zone. In verbrauch the Pumpspeicher quirk was rewritten to name 'Hydro pumped storage'; the erzeugung version is unchanged.
**Why:** The catalog listed the values but never said what they mean, so the model averaged all four metrik values together (t2_12) and had no rule for "the German price" or for the ∅ Anrainer zone. The descriptions are general, not aimed at single questions. This is the second of the three catalog v2 rows (see D23).
**Evidence:** `results/v2b_t0_run{1,2,3}_2026-10-27.log`. Mean 60.67 vs 59.67 for v2a (runs 60, 61, 61 vs 60, 59, 60). Three questions went from 0/3 to 3/3 with the intended SQL: t2_12 and t1_32 now filter `metrik = 'grid load'`, and t1_22 uses Deutschland/Luxemburg (+3.00 together). Three questions got worse: t1_18 (3/3 to 0/3, now returns an extra column), t2_21 (1/3 to 0/3: it now excludes ∅ Anrainer DE/LU, but the gold lists all 16 zones including it) and t2_06 (3/3 to 2/3). Together they cost 1.67, so the net gain of +1.00 is too small to separate from noise. The 42 questions with unchanged prompts (the control group) moved by -0.33. t2_25 now ranks exactly the 11 right zones but sorts ascending, so it still fails 3/3. No wrong declines (t1_22 is no longer declined). Tier 0 unchanged at 7/8.

## D26. Data date range stated at the top of the prompt (row v2c)
**Decision:** On top of v2b, one line at the very top of the prompt says the data covers 2023-06-01 00:00 to 2026-06-01 23:45 in 15-minute steps, that there is no data before or after, and that June 2026 has only one day. Nothing else changed (new prompt template `prompt_template_v2c.py`). **Status:** Not carried forward. The date line fixed u_08 but caused false declines on t1_12 and t1_26 (dates inside the range), net -3.67. Later rows build on v2b.
**Why:** In the decline row (D22) u_08 (July 2026) was never declined, likely because nothing told the model where the data ends (interpretation, not tested). This is the third and last of the three catalog v2 rows (see D23).
**Evidence:** `results/v2c_t0_run{1,2,3}_2026-10-27.log`. Mean 57.00 vs 60.67 for v2b (runs 57, 57, 57 vs 60, 61, 61), so the drop is outside the run-to-run range. The intended effect worked: u_08 was declined in 3/3 runs (was 0/3; "Data for July 2026 is not available"), +1.00. But two German questions about dates inside the covered range were wrongly declined in 3/3 runs: t1_12 ("Data for February 2026 is not available") and t1_26 ("The data does not cover May 2025"), -2.00. Why the added line triggers this is not clear. t2_19 fell from 3/3 to 0/3 (it now also groups by year: 37 rows instead of 12), -1.00. The rest is small drops (t2_12 -2 passes, t2_01, t2_05, t2_22 and u_01 -1 each, t2_06 +1), -1.67 together. No unchanged-prompt control group exists this time, since every prompt changed. The model did not start adding date filters it did not need (28 questions without one in the gold: 3 runs with a filter in both v2b and v2c; no coverage-boundary date appears in any SQL). The 2026 questions t1_32, t1_34 and t1_30 still pass 3/3, and t4_02 still fails.

## D27. ∅ Anrainer wording: "zones" changed to "countries" (row v2b2)
**Decision:** On top of v2b (not v2c), the last sentence of the ∅ Anrainer DE/LU description now reads "Leave it out when ranking or comparing countries." instead of "... zones." Only this one word changed (the v2b prompt template is used, with a catalog built in `schema_catalog_v2b2.py`). **Status:** Not carried forward. The wording was not why t2_21 drops ∅ Anrainer; no gain (run 3 alone lost 4 points, control group -0.67). Later rows build on v2b.
**Why:** In v2b, t2_21 ("list all the price zones") dropped ∅ Anrainer DE/LU although the gold includes it (D25). The likely reason, not tested before this row, is that "zones" made the model apply the rule to any question about price zones. "Countries" should limit the rule to country questions like t2_25.
**Evidence:** `results/v2b2_t0_run{1,2,3}_2026-10-29.log`. Mean 58.67 vs 60.67 for v2b (runs 60, 60, 56 vs 60, 61, 61). The intended effect did not appear: t2_21 still excludes ∅ Anrainer DE/LU in 3/3 runs and fails 3/3 (15 rows against 16), exactly as in v2b, so the word "zones" was not the cause. t2_25 is unchanged: the 11 right zones, sorted ascending, 0/3. Changes: two wrong declines in run 3 only, t1_27 ("no data specifically for the year 2024") and t1_35 ("no data for December 2025"), -2 passes; t2_06 went from 2/3 to 0/3 (returns only the zone name), -2 passes. The 53 questions with unchanged prompts (the control group) moved by -0.67 (t2_01, t2_09, t3_06) and the 31 questions that show the price table by -1.33. Because unchanged prompts also swing by about 0.7, the -2.00 is only partly separable from noise, but the row brought no gain. Tier 0 unchanged at 7/8.
**Note:** The catalog series ends at v2b. Further wording tweaks were stopped because their effects are smaller than run-to-run noise and they risk tuning the prompt to the exam (O13).

## D28. House-style output conventions written down
The 8 conventions (percent 0–100 with 2 decimals, label + value, label first, calendar buckets as dates and cyclic ones as integers, undirected “rank/top” means highest first, time-ordered lists ascending, raw units, half-open ranges) come from the gold SQL (results/house_style_inventory_2026-10-29.md). They are given to both the held-out writer and the example writer, so examples teach a written convention, not the exam. Known inconsistencies in the exam (extra columns in t3_09, t3_12, t4_03; mixed NULLS LAST) were noted and left for later review.

## D29. Held-out set of 30 questions (O13)
Drafted by Claude in an incognito chat outside the Project that saw only the schema, data facts and D28 conventions; reviewed, edited and verified by me (validator pass, tie and method checks, leak check). It is not used for tuning: only per-tier totals are looked at, never per-question results.
**History:** First frozen at commit 36b45cf (SHA-256 of heldout_smard.yaml: 1b364c69e6315f92249bfe906ae6913e3eb66c93b27cd024d1c397ede41a92ef). The leak check flagged h2_01 and hu_03 (text scores 0.64 and 0.74 against t2_01 and u_08); after they were reworded the text scores were below 0.6 (0.08 and 0.31). A side-by-side "same question" check against the exam then showed that both were still the same question as t2_01 and u_08 with different filters. Both were replaced (new h2_01: different table and question; new hu_03: different table and period, same skill), re-checked against every exam item, and re-frozen at commit 627ee4f (SHA-256 26ffe76d93f419e4d77a230d54fe8df5d60c464854940d03db0ee01345a80713; commit 58dfc73 holds the same file). The replacements were made because of the exam comparison, not because of held-out results: only per-tier totals of the first starting-point run (3 runs, mean 18.67 of 30) had been seen, no per-question results. The starting-point run was repeated on the re-frozen file; the first run is superseded (its files are kept, see results/README_heldout_runs.md).
**Lesson:** a low text-similarity score does not mean a different question; the side-by-side check is what caught it.
**Note:** the contents of h2_01 and hu_03 (old and new) and the detailed check results for h4_01, h3_02, h2_02, h3_03 and h2_07 were shown once in the tuning chat.

## D30. Example bank: 30 question/SQL examples with written rules
*Drafted by Claude from the check reports and the instructions given at the time; review the wording.*
**Decision:** `example_bank.yaml` holds 30 examples (tier 0: 2, tier 1: 3, tier 2: 19, tier 3: 4, tier 4: 2; 28 have gold_sql). Rules: (1) every example must be "same type only" against EVERY item of `gold_set_smard.yaml` and `heldout_smard.yaml`, checked with `grader/structure_check.py` (a pair is "same question" when no structural feature differs: tables, measure, metrik, aggregate, grain, order direction, limit, CTE/join/window/FILTER/HAVING/ratio, change-vs-share, source and zone selection kind); (2) no exam-specific labels, classification lists or answer values; (3) the D28 house style; (4) no data quirk as the point of an example (for instance `∅ Anrainer DE/LU`); (5) tier-0 examples decline a concept that appears in no exam or held-out tier-0 item; (6) each item carries a `muster` (pattern) key. `validate_gold_file.py --examples` checks the file (skips reihenfolge_relevant and toleranz, allows `muster`).
**Why:** The first bank (written outside the checks) had 13 of 30 examples that were the same question as an exam item with other dates, sources or zones, although their text scores were low. Examples that repeat exam questions would measure copying, not the method. The held-out items had to be protected the same way.
**Evidence:** `results/example_bank_checks_2026-10-30.md` (first bank: validator 86 failures, 13/30 same question as an exam item) and `results/example_bank_checks_v2_2026-10-30.md` (final bank, commit 56b2225): validator `--examples` PASS, structure check 0 same-question pairs against the exam (16 pairs differ in one feature) and against the held-out set (9 such pairs), text-score pairs above 0.6: 2 against the exam, 1 against the held-out set. 15 examples were replaced and ex_22 was reworded; no replaced example shares an answer value with an exam or held-out item (one coincidence, 4.38).
**Note:** "Each pattern at least twice" is not met (28 distinct `muster` values; only "percent change" and "decline" occur twice). The structure tool cannot see time-of-day conditions, label strings, source lists or tier-0 items, so those checks rest on side-by-side reading and concept keywords.

## D31. Static 8-example block (row ex-a): tested, not carried forward
*Drafted by Claude from the analysis file; review the wording.*
**Decision:** On top of v2b, one block of 8 fixed examples from the bank (ex_06, ex_07, ex_11, ex_13, ex_16, ex_20, ex_24, ex_26, in this order) is inserted after the schema section and before the question line, under the header "Examples (they show the expected answer style; the notes above still apply):". The block is read from `example_bank.yaml` at run time. Nothing else changed (`grader/prompt_template_exa.py`, `grader/run_exa.py`). **Status:** Not carried forward.
**Why:** The remaining failures on the exam are mostly shape and style (column count, row count, SQL errors) that the catalog notes do not reach.
**Evidence:** `results/analysis_exa_vs_v2b_2026-10-31.md`. Mean 59.33 vs 60.67 for v2b (runs 59, 59, 60 vs 60, 61, 61); mean prompt 1624 tokens (v2b 629). Shape failures (wrong column count + wrong row count + SQL errors, 3 runs summed) fell from 40 to 16 and u_08 was declined correctly in 3/3 runs (tier 0 8.00 vs 7.00), but wrong declines on tier 1-4 went from 0 to 35 (11, 12, 12 per run), for instance t2_12 and t3_05 (both 3/3 in v2b) were declined in all 3 runs, and the stated reasons are invented ("no information about the day of the week"). t2_16 copied ex_20 (month as an integer, ratio 0.979) in all 3 runs and fails. Four questions went from 0/3 to 3/3 and five from 3/3 to 0/3.
**Note:** This is the origin of open item O14 (invented declines).

## D32. Retrieved examples (row ex-b): tested, not carried forward
*Drafted by Claude from the analysis file; review the wording.*
**Decision:** Same position and header as ex-a, but the 3 bank examples most similar to the question (cosine similarity of text-embedding-3-small embeddings of the question text; pool = the 28 bank items with gold_sql; the most similar example last) instead of the fixed 8. Embeddings are cached in `grader/cache/embeddings_text-embedding-3-small.json` so runs are reproducible (`grader/example_retriever.py`, `grader/prompt_template_exb.py`, `grader/run_exb.py`). The prediction was written before the run (`results/exb_prediction_2026-10-31.md`). **Status:** Not carried forward.
**Why:** Test whether ex-a's declines came from examples that did not resemble the question.
**Evidence:** `results/analysis_exb_2026-10-31.md`. Mean 56.33 vs 60.67 for v2b and 59.33 for ex-a (runs 55, 57, 57); mean prompt 978 tokens. Shape failures fell further (13 summed over 3 runs), but wrong declines rose to 51 (18, 16, 17 per run). Declined and non-declined tier 1-4 questions have the same similarity to their examples (top-1 0.578 vs 0.585, p = 0.95; ex-a: 0.482 vs 0.511, p = 0.41), so resemblance does not explain the declines. Two new failures: t2_22 (no `NULLS LAST` on a DESC ranking of sources, none of the three retrieved examples shows it) and t2_23 (year returned as a date after retrieving date_trunc examples). t2_16 copied ex_20 again.
**Note:** The prediction check is at the end of the analysis file: shape failures drop (confirmed), declines drop sharply if resemblance was the cause (not confirmed), copying of ex_20 (confirmed), tier 0 unchanged (confirmed), tier 1 unchanged (not confirmed, -2.33). Next step: fix the declines on their own (O14), then re-run ex-a and ex-b unchanged on top of that.

## D33. Narrower decline rule (row df): tested, not carried forward
**Decision:** On top of v2b, only the decline paragraph was replaced: decline only if the information "is not in the tables above at all, or a note above says those values are missing"; anything that can be worked out from the tables counts as available, "including parts of zeitpunkt (year, month, day, weekday, hour)"; an open detail such as the time period gets the most natural reading. The last two sentences were kept word for word (`grader/prompt_template_df.py`, `grader/run_df.py`). The prediction was written before the run (`results/df_prediction_2026-10-31.md`). **Status:** Not carried forward.
**Why:** 65 of the 86 false declines in ex-a and ex-b claimed that something calculable "does not exist" (`results/false_declines_inventory_2026-10-31.md`), and the old wording said "tables and columns above".
**Evidence:** `results/analysis_df_vs_v2b_2026-10-31.md`. Mean 52.00 vs 60.67 for v2b (52, 52, 52), far outside the noise. False declines on tiers 1-4 went from 0 to 10 per run; 21 of the 30 claim that a year or month is missing although the data exists (t1_12, t1_22, t1_27, t1_31, t1_34, t1_35, t2_16, t2_25). One reason cites the Kernenergie note on a Photovoltaik question, so the "note says values are missing" clause seems to have spread to dates in general (interpretation). t2_09 and t2_24 lost 3/3 each by switching from DATE_TRUNC to EXTRACT, likely nudged by the listed parts of zeitpunkt (not tested). u_08 went to 3/3, but through the same false date claim, so it is not a real gain. Tier 0 8.00 (v2b 7.00). Shape failures 43 vs 40. Prediction check: 1 partly, 2-4 not confirmed. Run 3 was repeated on its own after the API credits ran out mid-run; same code and settings.
**Lesson:** This is the third change aimed at declining that moved the decline behaviour in an uncontrolled way (v2c, ex-a/ex-b, df). Next approach: leave the main prompt unchanged and check a decline's reason against the database only after the model declines, so answered questions cannot be affected.

## Principles
- The grader must exist and be validated before any agent code.
- Never change the model between stages.
- One change per ablation row, measured over several runs.
- An ambiguous catalog note can hurt more than no note.
- Do not write notes aimed at individual exam questions.
