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

## Principles
- The grader must exist and be validated before any agent code.
- Never change the model between stages.
- One change per ablation row, measured over several runs.
- An ambiguous catalog note can hurt more than no note.
- Do not write notes aimed at individual exam questions.
