# Text-to-SQL Agent (SMARD): Full Progress Handoff

**Last updated:** 26 October 2026
**Purpose of this file:** a complete record of where the project stands, so a brand-new chat session (or a new laptop, or you after a long break) can pick up without any other context. It is written in plain language on purpose. Read it top to bottom once, then use the section headings to jump around.

**Owner:** Vishnu (M.Sc. Data and Knowledge Engineering, OVGU Magdeburg)
**Project folder on laptop:** `/Users/deepaktalwar/Desktop/text-to-SQL`
**Companion files in that folder:** `README.md` (still an empty template), `PROJECT.md` (long design document; header date 3 Aug, but section 7 now just points to `DECISIONS.md`), `DECISIONS.md` (all decisions, D1 to D22), `gold_set_smard.yaml`

---

## 1. The project in one paragraph

A system where you ask a question in English or German ("How much wind power did Germany produce in June 2024?"), an AI model writes SQL, the SQL runs safely against a real PostgreSQL database of German electricity data, and you get back a chart, a written answer, and the SQL itself. The point of the project is NOT that an AI can write SQL. The point is everything around it: measuring accuracy honestly with a fixed exam, then adding improvements one at a time and showing with numbers which ones actually help. The finished result should let Vishnu say in an interview something like: "Improvement X took accuracy from A to B, improvement Y added C more, and the retry loop added D but made the slowest queries three times slower, so I capped it at three attempts."

**Goal behind the goal:** CV and interview impact. Every decision must be something Vishnu genuinely understands and can explain, not just working code. Documentation should reflect his own understanding.

---

## 2. How Vishnu likes to work (important for any new chat)

- Explanations should be **plain, non-technical, and in small chunks**. Dense all-at-once explanations are overwhelming. When something is complicated, break it into steps and check understanding.
- Vishnu uses **Claude Code (CC)** to write and run the code. The chat assistant's job is to (a) explain what is going on, (b) help make design decisions, and (c) write precise commands to paste into CC. The chat assistant cannot see his laptop. It only sees what he pastes.
- The working style so far: decide the design here, write a command for CC, CC builds and runs it, Vishnu pastes the results back here, we interpret them together.
- Design decisions are made **one at a time and written into `DECISIONS.md`**.

---

## 3. The data

**Source:** SMARD.de (Bundesnetzagentur). Free to use with attribution. Attribution line for the README: `Data source: Bundesnetzagentur | SMARD.de`

**Period:** 2023-06-01 00:00 to 2026-06-01 23:45, one row every 15 minutes.

**Three raw CSV files** (in `data/raw/`, NOT committed to git):
- `Realisierte_Erzeugung_202306010000_202606020000_Viertelstunde.csv` (electricity generated, by source)
- `Actual_consumption_202306010000_202606020000_Quarterhour.csv` (electricity consumed)
- `Gro_handelspreise_202306010000_202606020000_Viertelstunde.csv` (wholesale prices by country/zone)

`data/new/` holds small sample CSVs (`erzeugung_sample.csv`, `verbrauch_sample.csv`, `preise_sample.csv`) that are fine to commit.

### The three tables (long format: one row per timestamp per category)

```sql
erzeugung (id SERIAL PRIMARY KEY, zeitpunkt TIMESTAMP NOT NULL, energietraeger TEXT NOT NULL, mwh NUMERIC(12,2))
verbrauch (same shape, with a metrik column instead of energietraeger)
preise    (same shape, with a preiszone column and preis_eur_mwh instead of mwh)
```

Note: the real tables use a **surrogate `id` primary key**, not a composite key on (zeitpunkt, energietraeger). Older notes showed a composite key; `PROJECT.md` was corrected on 26 Oct. This is what lets the duplicate daylight-saving timestamps be stored (see below).

### Row counts (verified after the reload on 1 Oct 2026)

| Table | Rows | Per category |
|---|---|---|
| erzeugung | 1,263,744 | 105,312 for each of 12 energy sources |
| verbrauch | 421,248 | 105,312 for each of 4 metrics |
| preise | 1,790,304 | 105,312 for each of 17 price zones |

105,312 rows per category but only **105,300 distinct timestamps**. The 12 missing are the daylight-saving duplicates (below). This matches the prediction in `PROJECT.md` exactly.

### Category values

- **energietraeger (12):** Biomasse, Wasserkraft, Wind Offshore, Wind Onshore, Photovoltaik, Sonstige Erneuerbare, Kernenergie, Braunkohle, Steinkohle, Erdgas, Pumpspeicher, Sonstige Konventionelle
- **metrik (4):** 'grid load', 'Grid load incl. hydro pumped storage', 'Hydro pumped storage', 'Residual load' (English, unlike the other two tables; checked against the database on 24 Oct, 0 mismatches)
- **preiszone (17):** Deutschland/Luxemburg, ∅ Anrainer DE/LU, Belgien, Dänemark 1, Dänemark 2, Frankreich, Niederlande, Norwegen 2, Österreich, Polen, Schweden 4, Schweiz, Tschechien, DE/AT/LU, Italien (Nord), Slowenien, Ungarn

### Data quirks (real properties of the data, several exploited by exam questions)

1. **Values are MWh (energy in one quarter-hour), not MW (power).** Multiply by 4 to get MW. This caused the biggest single mistake so far (section 8).
2. **Kernenergie (nuclear) is NULL, not zero, after 2024-01-30.** Before that date it has real readings, all exactly zero. Verified: 81,930 NULL rows, 23,382 zero rows, 0 other values. Any `ORDER BY ... DESC` needs `NULLS LAST` or Kernenergie wrongly sorts to the top.
3. **The `DE/AT/LU` price zone exists but is completely empty** (105,312 NULL rows out of 105,312). The joint zone was split in 2018.
4. **Daylight saving.** Three autumn clock changes (2023-10-29, 2024-10-27, 2025-10-26) each repeat one hour, giving 4 duplicate timestamps each, 12 in total. The three spring days have 23 hours.
5. **`Pumpspeicher` means opposite things in two tables.** In `erzeugung` it is electricity generated by releasing water. In `verbrauch` it is electricity used to pump water uphill.
6. **Exactly-zero solar only appears on 2026-06-01.** Every other night has small values like 0.25. The last day is probably preliminary data. Questions t1_30 and t4_02 depend on this.
7. **The tail is thin.** June 2026 has one day, July 2026 has none, so benchmark questions use 2024 and 2025.
8. **`∅ Anrainer DE/LU` is an average of the neighbouring zones, not a country.** Checked on 26 Oct: it equals the simple mean of the 11 neighbouring zones at each quarter-hour to within 0.005 EUR/MWh. Questions about "neighbouring countries" must leave it out, as the gold SQL of t2_25 does.

### How the CSVs are loaded (the five things that bite)

Semicolon separator; a hidden byte-order mark at the file start (`encoding='utf-8-sig'`); German numbers (`1.542,63` means 1542.63); a dash means NULL not zero; dates are day-first. All already handled in the loader scripts.

---

## 4. Environment and how to rebuild it (learned the hard way on 1 Oct 2026)

Vishnu changed laptops. A Docker container and its data do **not** travel with the code. What happened: the container was recreated from `docker-compose.yml` as a fresh, empty database. Nothing was lost because the raw CSVs and loader scripts were still in the project folder.

**Facts about the current setup (these differ from older docs):**
- Container name is **`text-to-sql-db`** (older notes said `smard-db`; `PROJECT.md` was corrected on 26 Oct).
- Image `postgres:16`, port 5432 exposed.
- Database user is **`app`**, password **`app`**, database **`smard`**. There is no `postgres` user.
- The machine is an Apple-silicon Mac (Postgres reports aarch64). Python 3.12 in a `.venv`.
- The OpenAI key lives in `.env` as `OPENAI_API_KEY`. `.env` must stay in `.gitignore`.

**To rebuild the database on any machine:**
```bash
docker compose up -d                      # starts the empty container
cd scripts
python load_data.py                       # creates and fills erzeugung
python load_verbrauch.py                  # creates and fills verbrauch
python load_preise.py                     # creates and fills preise
docker exec -i text-to-sql-db psql -U app -d smard -v grader_password="<GRADER_DB_PASSWORD from .env>" < ../sql/create_grader_role.sql   # read-only role (safe to re-run)
docker exec -i text-to-sql-db psql -U app -d smard < sanity_checks.sql
```
Important: `docker exec ... -f file` looks for the file *inside the container*. Always feed local files in with `< file` and `-i` as shown above.

**What a healthy sanity-check run looks like** (this was the result after the reload): 1,263,744 rows in erzeugung; all 12 sources at exactly 105,312; range 2023-06-01 00:00 to 2026-06-01 23:45; Kernenergie 23,382 zero / 81,930 NULL / 23,382 non-null; the duplicate-timestamp check shows 2 rows per source; the final anomaly checks return 0 rows.

**Scripts in `scripts/`:** `common.py` (shared helpers, DB connection, German number parser), `load_data.py`, `load_verbrauch.py`, `load_preise.py`, `sanity_checks.sql`.

**Read-only database role: exists (`grader_ro`), grader side is done.** Created by `sql/create_grader_role.sql` (decision D8; D12 covers what is still open). Checked against the database on 24 and 26 Oct:
- SELECT only, on `erzeugung`, `verbrauch` and `preise`. No INSERT, UPDATE, DELETE or TRUNCATE. Not a superuser, cannot create databases or roles, cannot create objects in the `public` schema.
- `statement_timeout` is 30 seconds for this role.
- TEMP (temporary tables) is revoked from `grader_ro` and from PUBLIC. PUBLIC keeps CONNECT. The loader account `app` is unaffected.
- The grader runs all SQL through it (`grader/executor.py` reads `GRADER_DB_USER` and `GRADER_DB_PASSWORD` from `.env`). The loader account is never used for grading.

**Still missing:** a safe runner for the live agent (its own connection, row cap, validation before running). Nothing of that exists yet.

**Rebuilding the role:** the rebuild step above creates it (it disappears whenever the container is recreated from scratch). `sql/create_grader_role.sql` was fixed and tested on 26 Oct: it works on a fresh database when fed in on stdin, and it is safe to re-run. Pass the password as is, without extra quotes around it; the script quotes it itself.

---

## 5. The exam ("gold set")

`gold_set_smard.yaml` has **84 questions**. Each has a question text, the correct SQL (`gold_sql`), and a human-readable expected answer (`gold_antwort`, documentation only, 22 of them are truncated, so the grader never uses it).

| Tier | Count | What it is |
|---|---|---|
| 0 | 8 | Unanswerable questions. The correct behaviour is to decline, not invent an answer |
| 1 | 35 | One aggregate, one or two filters |
| 2 | 25 | Grouping, ranking, shares |
| 3 | 12 | Dates, comparisons, sub-queries, cross-table |
| 4 | 4 | Hard: window functions, gaps-and-islands, joins |

**Why store correct SQL and not correct answers:** stored answers go stale if the data is reloaded; stored queries re-run and stay correct.

**Known weaknesses of the exam (worth mentioning honestly):**
- Tier 1 is 42% of questions and all follow roughly one template (O7). The headline score is therefore not very meaningful on its own, which is why per-tier scores are reported.
- Only 7 of 84 questions are in German, and most use the exact database word (O8).
- There is no "ambiguous, should ask a follow-up" category (O10).
- t1_30 and t4_02 depend on a data artifact (the preliminary last day) (O9).

**Fix made to t2_14** ("top 5 most expensive quarter-hours"): prices tied at 5th place made the order non-deterministic. Added a tiebreaker, so the gold SQL now ends `ORDER BY preis_eur_mwh DESC NULLS LAST, zeitpunkt LIMIT 5` (earliest first on ties), kept `reihenfolge_relevant: true`, and added a `hinweis` explaining the tiebreaker is only for reproducibility. Reasoning: this is explicitly a ranking question, so order matters, and a set comparison would quietly test a weaker question. t2_21 is different (its ties are at a filter cutoff), so it stays order-insensitive.

**Still worth checking:** the other order-sensitive questions (t2_02, t2_05, t2_11, t2_17, t2_22, t2_25, t4_01, t4_02, t4_04) for the same tied-value risk. Not confirmed done.

---

## 6. The grader (done, works)

Lives in the `grader/` folder (`loader.py`, `executor.py`, `comparator.py`, `run_grader.py`; re-checked on 26 Oct, `run_grader.py --self-test` still scores 84/84). **Self-test mode feeds the gold SQL in as if an agent wrote it and scores 84/84.** Any failure there would be a grader bug.

How it marks a question:
1. Run the gold SQL and the agent's SQL.
2. Compare row counts first.
3. Sort both sides unless the question is marked `reihenfolge_relevant: true`.
4. Compare cell by cell **by position, not by column name** (the agent will not reproduce the exact column aliases).
5. Numbers within a tolerance, text must match exactly. Years and similar values are compared as raw numbers (no thousands separators, open item O5).
6. Tier 0: pass only if the agent produced no SQL (declined).

**Comparator is strict about column count.** If the agent returns an extra or missing column, it fails even when the logic is right. Decision so far: **stay strict for now** and revisit later (D19 in `DECISIONS.md`). See t2_01 in section 9 for a case where this arguably penalises a reasonable answer.

**Tolerance decisions:** relative tolerance of 0.5% as the default, with looser overrides for the `ROUND()` questions (t2_07, t3_02, t3_06, t3_07, t3_10, t3_12). Exact override values should be confirmed in the grader's loader file.

**"Grid load" unit decision (O6):** the exam expects raw MWh, so only MWh answers count as correct, not MW (x4). This decision matters a lot, see section 8.

---

## 7. The architecture plan and build order

Mental model: a new analyst on their first day. Smart, but has never seen this database. You show them where things are, give them notes, show worked examples, have someone check their work before it runs, and give them an account that can read but not delete.

| # | Component | Status |
|---|---|---|
| 1 | PostgreSQL in Docker | Done |
| 2 | Schema catalog (table/column notes) | Built, first version (section 8) |
| 3 | Example bank (about 30 question/SQL pairs, retrieved by similarity) | Not started |
| 4 | Query writer (the AI call) | Built as the naive version |
| 5 | Validator (sqlglot AST check plus `EXPLAIN` dry run) | Not started |
| 6 | Retry loop (feed errors back, max 3 attempts, LangGraph) | Not started |
| 7 | Safe runner (read-only role, statement timeout, row cap) | Grader side done (`grader_ro`, SELECT only, 30 s timeout, TEMP revoked; the grader runs through it). Live agent runner not started |
| 8 | Presenter (chart from result shape, written answer, SQL always visible) | Not started |
| 9 | Evaluation harness | Done and working |
| 10 | Tracing (Langfuse) | Not started |

Build order: grader, naive agent, schema catalog, example bank, validator and retry loop, Streamlit UI, tracing and CI, README with the ablation table.

**Tech stack:** PostgreSQL 16 in Docker, Python and pandas for loading, sqlglot for validation, LangGraph for orchestration, Streamlit for UI, Langfuse for tracing, YAML plus a Python grader for the benchmark, GitHub Actions for CI.

**Model lock:** **gpt-4o for every stage**, via the OpenAI API, key in `.env`. Never change the model mid-project. Otherwise a score change could be the model and not the pipeline, and the ablation table would stop being honest.

---

## 8. What has been built and measured so far

### Step A: Naive baseline agent (the "before" row)

Files (new, separate from the grader): `prompt_template.py`, `naive_agent.py`, `run_baseline.py`.

The prompt gave the model ONLY table names, column names and types, the lists of category values, the question, and an instruction to return exactly one SELECT. **No hints about any data quirk.** That was deliberate: the quirk notes are what schema linking is supposed to add, so including them in the baseline would hide their value.

**First run (1 sample, before temperature was fixed): 46/84.**

| Tier | Score |
|---|---|
| 0 | 0/8 |
| 1 | 32/35 |
| 2 | 12/25 |
| 3 | 2/12 |
| 4 | 0/4 |

Valid-SQL rate: 83/84 (almost everything ran; the problem was wrong answers, not broken SQL).

**Why the naive agent failed (five repeatable causes):**
1. NULL sorting: Kernenergie ends up first in descending lists (t2_02, t2_05, t2_22 and others).
2. The empty `DE/AT/LU` price zone gets picked in price aggregates (t2_06, t2_25).
3. Percentages: the agent forgets to multiply by 100 or uses too many decimals (t2_07, t3_02, t3_10).
4. Date format: the agent uses `EXTRACT(MONTH ...)` (returns a number like 6) where gold returns a real date (t2_09, t2_20, t3_03).
5. Column shape: extra or missing columns (t1_02, t1_18, t2_17, t3_04, t3_07, t3_09, t3_11, t3_12, t4_02). Often the logic is right and only the shape differs.

Separately, **tier 0 scored 0/8 because the prompt never told the model that declining was allowed.** That is a prompt-instruction gap, not a schema problem.

### Step B: Schema catalog and "schema linking" (the second row)

Files: `schema_catalog.py` (notes per table: purpose, columns, example values, category lists, quirks), `catalog_retriever.py` (simple **keyword matching** to pick which tables to show; falls back to all three tables when unclear), `prompt_template_schema_linked.py`, `run_schema_linked.py`.

Design decisions made here:
- **Quirks go into the catalog as explicit written notes**, not into the example bank. The example bank is for showing query patterns, not one-off facts about the data.
- **Keyword matching instead of embeddings**, because three tables is too small for vector search to be justified.

**Run 1: 35/84. Worse than the baseline (46).** Cause found: the catalog note I (the chat assistant) wrote said "values are MWh, multiply by 4 to get MW if asked for load." The model multiplied by 4 on almost every question, so answers came out exactly 4x too big, while the exam expects raw MWh. The catalog contradicted the grader. This was a wording mistake in the note, not a retrieval problem (retrieval picked the right tables on all 84 questions).

**The fix:** reword to "Values are MWh per 15-minute interval. Report results in MWh as stored. Only multiply by 4 if the question explicitly asks for MW or power." Changed in both the erzeugung and verbrauch entries only.

**Run 2: 47/84.** Eleven of the twelve regressions were fixed.

| Tier | Naive | Schema run 1 | Schema run 2 |
|---|---|---|---|
| 0 | 0/8 | 0/8 | 0/8 |
| 1 | 32/35 | 27/35 | 33/35 |
| 2 | 12/25 | 7/25 | 11/25 |
| 3 | 2/12 | 1/12 | 3/12 |
| 4 | 0/4 | 0/4 | 0/4 |
| Total | 46 | 35 | 47 |

**Keep the bad run-1 log.** "A well-meaning but ambiguous note cut accuracy by 11 points" is a genuine, interview-worthy finding.

### Step C: Measuring the noise (3 runs each, temperature 0)

Temperature was set to 0 and a fixed seed added in `naive_agent.py` (seeds are best-effort at OpenAI, not guaranteed). Each setup was run 3 times. Logs: `*_t0_run{1,2,3}_2026-10-21.log` in `results/`.

| Setup | Run 1 | Run 2 | Run 3 | Mean |
|---|---|---|---|---|
| Naive baseline | 45 | 47 | 46 | **46.00** |
| Schema-linked | 46 | 48 | 46 | **46.67** |

Per tier (min to max across 3 runs): naive tier 1 = 31 to 32, tier 2 = 11 to 12, tier 3 = 3; schema-linked tier 1 = 32 to 33, tier 2 = 10 to 12, tier 3 = 3. Tiers 0 and 4 are 0 in every run.

**Conclusion: no detectable difference.** The gap (0.67 points) is smaller than the run-to-run wobble (about 2 points within each setup). Questions that flipped between pass and fail across the 3 runs: naive t1_10 and t2_17; schema-linked t1_18, t2_02, t2_17 and t2_21.

**How to read this honestly:** schema linking, as built so far, did not measurably help. `PROJECT.md` (section 6) expected it to be the biggest lever. A plausible but unproven explanation: with only 3 tables, the naive prompt already shows the model nearly everything, and the remaining mistakes are about the *shape* of answers (columns, percentages, date format), which table notes do not address. This is a finding, not a failure, and it is a good thing to be honest about.

### Step D: "Did the notes work?" (a closer look at the schema-linked row)

Full report: `results/analysis_notes_vs_targets_2026-10-24.md`. It is a read-only look at the six temperature-0 logs, with the prompts rebuilt locally. No API calls.

- **The notes reached the prompt every time.** The retriever chose a table set that contained the right table for all five target questions, and the exact note text was in each prompt.
- **DE/AT/LU note: followed in 6 of 6 runs.** It even removed a real naive failure (naive run 2 of t2_06 put DE/AT/LU on top). But t2_06 and t2_25 still failed, for other reasons: t2_06 returned only the zone name (1 column, the gold wants 2), and t2_25 included the `∅ Anrainer DE/LU` zone (15 rows, the gold has 14).
- **Kernenergie note: ignored.** None of the 8 failing schema-linked queries used `NULLS LAST` or filtered the NULLs, and t2_05's SQL is identical in the naive and schema-linked runs. A likely reason, *not tested*: the note says "any ORDER BY ... DESC over this column", but Kernenergie is a value inside the energietraeger column, and the model sorts by its own `SUM(...)`. It may not see the note as applying to what it wrote.
- **What the failures look like.** Of the roughly 29 non-tier-0 failures per schema-linked run, about 14 are the wrong shape (wrong number of columns or rows) and about 15 are wrong values or SQL errors. Roughly half and half. On top of that come the 8 tier 0 questions that fail every time.
- **Labels: 0 mismatches.** The metrik, preiszone and energietraeger values in the database match both prompts and every literal in the 84 gold queries, character for character.

### Step E: The SQL errors

With the catalog, SQL errors rose from 0.7 to 3.3 per run (12 in total across the six runs: 2 naive, 10 schema-linked). That looked like a regression, but all of them are on tier 3 and 4 questions (t3_04, t3_11, t3_12, t4_01, t4_02, t4_04), and every one of those fails in every run anyway. So no passes were lost.

**A prediction for the retry loop**, to be checked when it is built: it should fix *crashes* (t3_12: uses a column name that its own subquery renamed; t3_04: selects a column it did not group by; t4_01: a window function in the wrong place) but not *wrong logic* (t4_02 and t4_04 take `MAX` of a column they never define, instead of counting the rows in each streak). t3_11 is a crash too, but its logic also needs rethinking, so it is unlikely to pass either.

### Step F: Better logging

The runners (`run_baseline.py`, `run_schema_linked.py` and the new decline runner) now also write a `.jsonl` file next to each `.log`, with one line for every one of the 84 questions: the raw model output, the extracted SQL, pass or fail and the reason, latency, and prompt and completion tokens. The code is in `grader/result_logging.py`. It only watches the API call; it passes everything through unchanged, and a field it cannot read is stored as null instead of crashing the run. We checked with a fake client that the old and new runners send byte-identical requests and write byte-identical `.log` files.

**Limit:** logs from before 24 Oct only store the agent's SQL for *failed* questions. For a passed question in an old log there is no SQL to look at.

### Step G: Decline option (the third row, D22)

**What changed:** only the last paragraph of the schema-linked prompt. It now first says: if the question cannot be answered from the tables, reply `NO_QUERY: <one short sentence>`; then "Otherwise, return exactly one PostgreSQL SELECT statement that answers the question. Return only the SQL ..." The original sentence is kept word for word ("Return" just becomes "return" after "Otherwise,"). A reply starting with NO_QUERY, in any letter case and even inside a code fence, counts as a decline. Code: `grader/prompt_template_decline.py` and `grader/run_schema_linked_decline.py`. Same model, temperature 0 and seed. We caught an earlier draft that had dropped the "Return only the SQL" sentence before any money was spent.

**Results (3 runs, temperature 0):**

| Run | Tier 0 | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Total |
|---|---|---|---|---|---|---|
| Decline run 1 | 7/8 | 32/35 | 14/25 | 2/12 | 0/4 | 55 |
| Decline run 2 | 7/8 | 32/35 | 14/25 | 2/12 | 0/4 | 55 |
| Decline run 3 | 7/8 | 33/35 | 14/25 | 2/12 | 0/4 | 56 |
| **Decline mean** | **7.00** | 32.33 | 14.00 | 2.00 | 0.00 | **55.33** |
| Schema-linked mean | 0.00 | 32.67 | 11.00 | 3.00 | 0.00 | 46.67 |

- **Tier 0: clean gain.** 7 of 8 declined in every run. u_08 ("wind in July 2026") was answered with SQL every time. u_01 and u_07 were declined with reasons that quote the catalog notes (Kernenergie is NULL after 2024-01-30; DE/AT/LU is all NULL). The reason for u_08 is probably that no note says where the data ends (interpretation, not tested).
- **Tiers 1 to 4: +1.67, too small to separate from noise.** Per run 48, 48, 49 against 46, 48, 46. The changes are real and repeatable, but they go in both directions and come from the model's answer *style*, not from declining: **5 questions got better** (t1_18, t2_01, t2_02, t2_06, t2_17: now the shape the gold wants, and `NULLS LAST` on t2_02) and **3 got worse** (t1_22, t2_21 returns only the zone, t3_02 returns a fraction instead of a percentage).
- **Wrong declines: only t1_22**, in 2 of 3 runs ("What was the German power price at midday on 3 March 2025?"). The model said the time was missing, so it saw "midday" as ambiguous. The gold reads it as the quarter-hour starting 12:00. No other tier 1 to 4 question was ever declined.
- **The Kernenergie note is still not followed** on t2_05 and t2_22 (`NULLS LAST` appeared only on t2_02, in all 3 runs).
- **Valid-SQL rate is not comparable with earlier runs:** 75, 74 and 75 out of 84 (earlier 80 to 81), because a decline counts as "no valid SQL". Among the questions the model actually answered it was 75/76, 74/76 and 75/77, and SQL errors fell to 1, 2 and 2 per run (earlier 4, 3, 3).
- **Cost:** mean latency 1.08 seconds per question (median 1.01, slowest 3.58), about 521 prompt tokens and 56 completion tokens per question. Only runs from 24 Oct on record this; the earlier runs did not.
- **Format check:** half the replies (125 of 252) came wrapped in a code fence, which the extraction strips. Every extracted statement starts with SELECT or WITH, so no explanation text leaked into the SQL.
- **File names:** the three runs went past midnight, so the runner wrote the files with 2026-10-25 in the name. They were renamed by hand to `*_2026-10-24.*` to match the plan. The runs themselves took place just after midnight on 25 Oct.

---

## 9. Specific cases still open from the schema-linked runs

**t2_01** ("Which energy source produced the most overall?"). Gold returns the name and the total (2 columns). In the schema-linked runs the agent returned just the name, so the strict comparator failed it. With the decline wording (Step G) it now returns name and total and passes in 3 of 3 runs. So the shape rule only bit here because of phrasing, and the rule itself is still unchanged (D19).

**t2_06** ("Which price zone had the highest average price?"). Same story: the DE/AT/LU note was followed, but the zone-only answer failed the column rule. With the decline wording it returns the zone and its average and passes in 3 of 3 runs.

**t2_12** ("Which day of the week has the highest average consumption?"). Gold filters `WHERE metrik = 'grid load'`. The agent forgot the filter and averaged all four metrics (9306 vs 14104). The catalog never explains what the four metrik values mean. The right fix is a **plain description of each metrik value** (helps every consumption question), NOT a note aimed at this one question. Writing a note just to fix one exam question is teaching to the test and would inflate the score dishonestly. Still fails in every run so far (naive, schema-linked and decline).

**t2_25** ("Rank the neighbouring countries by their average price in 2025"). The agent follows the DE/AT/LU note but includes `∅ Anrainer DE/LU`, which is an average of the neighbours and not a country (see section 3, quirk 8). Gold leaves it out, so the agent returns 15 rows instead of 14. No note covers this zone yet. Fails in every run so far. Catalog v2 (section 13) will describe it, for all questions and not just this one.

**t1_22** ("What was the German power price at midday on 3 March 2025?"). Gold reads "midday" as the quarter-hour starting 12:00. In the decline runs the model called "midday" ambiguous and declined in 2 of 3 runs. This is a natural candidate for open item O10 (a "this is ambiguous, ask back" behaviour): there, asking "do you mean 12:00 to 12:15 or the hourly average?" would be the right answer.

---

## 10. Decisions made

**All decisions now live in `DECISIONS.md` (D1 to D22), and `PROJECT.md` section 7 points there.** The earlier list of "still to add" decisions has been written in (D12 to D22). Add new decisions there as they are made, one at a time.

**Principles that came out of the work** (also at the end of `DECISIONS.md`):
- The grader must exist and be validated before any agent code.
- Never change the model between stages.
- One change per ablation row, measured over several runs.
- An ambiguous catalog note can hurt more than no note.
- Do not write notes aimed at individual exam questions.

---

## 11. Open items (status)

| # | Item | Status |
|---|---|---|
| O1 | `reihenfolge_relevant` field | Grader supports it; confirm all listed question IDs are marked |
| O2 | t2_21 tied order | Left order-insensitive on purpose |
| O3 | Float tolerance | Decided (0.5% relative, looser on ROUND items); confirm values in the grader loader |
| O4 | Truncated `gold_antwort` | Handled: grader runs gold_sql, never reads gold_antwort |
| O5 | Years printed as `2 023` | Handled: compare raw values |
| O6 | Grid load unit (MWh vs MW) | **Decided: MWh only** (D21). Matches the reworded catalog note |
| O7 | Tier 1 dominates the exam | Open. Report per-tier, ignore the headline |
| O8 | Few German questions, most use exact schema words | Open. Add questions like "Sonnenstrom", "Kohlestrom", "Windkraft an Land" |
| O9 | t1_30 and t4_02 depend on preliminary data | Open. Annotate in the YAML |
| O10 | No "ambiguous, ask back" category | Open, optional. t1_22 ("midday") is a natural example (section 9) |
| O11 | Read-only DB role | **Grader side done, live agent runner open.** `grader_ro` exists and the grader uses it (section 4). Still to build: the agent's own safe runner |
| O12 | Duplicate DST timestamps and primary key | **Resolved.** Surrogate `id` key; the 12 duplicates are stored. Still be careful in gaps-and-islands queries on changeover days |

**Note on old logs:** logs from before 24 Oct store the agent's SQL only for failed questions (see Step F). Nothing can be recovered about the SQL of questions that passed in those runs.

---

## 12. Things to double-check (known loose ends)

1. **The metrik labels: resolved (24 Oct).** The database has exactly four values, all English ('grid load', 'Grid load incl. hydro pumped storage', 'Hydro pumped storage', 'Residual load'). There are 0 mismatches against `prompt_template.py`, `schema_catalog.py` and every literal in the 84 gold queries. The same holds for preiszone and energietraeger.
2. **Older docs: resolved (26 Oct).** `PROJECT.md` said the container was `smard-db` and showed a composite primary key; both are corrected to match the real setup (`text-to-sql-db`, surrogate `id` key, confirmed in the database). `README.md` is an empty template and says nothing about either.
3. Confirm no other order-sensitive gold question has tied values at the cutoff (section 5).
4. The very first naive result (46/84) and schema-linked results (35, 47) were single samples before temperature 0. Use only the 3-run, temperature-0 numbers in the final ablation table.
5. **`sql/create_grader_role.sql`: resolved (26 Oct).** The `CREATE ROLE` step is now built with `\gexec` instead of inside a `DO $$` block (psql does not substitute variables there), the header shows the working stdin command, and the password is passed without extra quotes (the old instruction would have stored the quote characters as part of the password). Tested on a throwaway database and role, both dropped afterwards: it creates the role on a fresh database, a second run is safe, and the role can log in and SELECT but not INSERT, create tables or create temp tables. The role in the real database was not touched.
6. **New:** there is no git repository in the project folder yet (checked 26 Oct), so none of the code, logs or decisions have version history.

---

## 13. What to do next (in order)

1. **Catalog v2, as one ablation row** (3 runs, temperature 0, on top of the decline row). All of it general, none of it aimed at single questions:
   - Reword the Kernenergie note so it talks about aggregates over the energietraeger *value* (for example "an aggregate over Kernenergie after 2024-01-30 is NULL, and NULL sorts first in DESC order"), not "this column". This tests the Step D hypothesis.
   - Add a plain description of each metrik value and each preiszone value, including that `∅ Anrainer DE/LU` is an average of the neighbours and not a country.
   - State the date range of the data (2023-06-01 to 2026-06-01, with only one day in June 2026), which may help with questions like u_08.
2. **Example bank** (about 30 question/SQL pairs, retrieved by similarity). Aimed at the shape failures: percentage style, date style, column shape. Make sure the examples are NOT copies of exam questions.
3. **Validator and retry loop** (sqlglot AST check plus `EXPLAIN`, max 3 attempts, LangGraph). Check the Step E prediction: it should fix the crashes (t3_12, t3_04, t4_01) but not t4_02 and t4_04. Track retry rate and p95 latency.
4. **Optional: the decline option on the naive setup**, to test whether the catalog notes are what made u_01 and u_07 declinable.
5. **Then:** the agent's safe runner, Streamlit UI with charts and visible SQL, Langfuse tracing, benchmark in CI, final README with the ablation table.

**Also worth deciding later:** whether to relax the column-count rule (t2_01 case), adding German-language questions that avoid the schema words (O8), and an "ask back" behaviour for ambiguous questions (O10, t1_22).

---

## 14. The ablation table so far (to go in the final README)

| Configuration | Execution accuracy (mean of 3 runs, temp 0) |
|---|---|
| Naive prompt, tables and columns only | 46.0 / 84 (54.8%) |
| + schema catalog with quirk notes (keyword retrieval) | 46.7 / 84 (55.6%), not distinguishable from baseline |
| + decline option (D22) | 55.33 / 84 (65.9%): tier 0 +7.0 (clean); tiers 1-4 +1.67, too small to separate from noise |
| + catalog v2 (Kernenergie reword, value descriptions, date range) | to do |
| + retrieved few-shot examples | to do |
| + validation and self-correction | to do |

Supporting metrics: accuracy per tier is in each step of section 8. Valid-SQL rate: 80 to 81 out of 84 for schema-linked, 74 to 75 for the decline runs (not comparable, because declines count as no SQL). Latency and tokens are only recorded from 24 Oct on: the decline runs average 1.08 s, 521 prompt and 56 completion tokens per question. Still to fill in: retry rate, p95 latency, cost per query.

---

## 15. Files and logs map

**Project folder:** `README.md` (empty template), `PROJECT.md`, `DECISIONS.md`, `PROJECT_PROGRESS.md` (this file), `gold_set_smard.yaml`, `docker-compose.yml`, `.env` (not committed), `.gitignore`, `requirements.txt`, `package.json`.
**Folders:** `data/raw/` (not committed), `data/new/` (samples), `scripts/` (loaders and sanity checks), `grader/`, `sql/`, `results/`.
**Grader and agent files, all in `grader/`:** `loader.py`, `executor.py`, `comparator.py`, `run_grader.py`; `naive_agent.py` (the one function that calls the API, shared by all setups), `prompt_template.py`, `run_baseline.py`; `schema_catalog.py`, `catalog_retriever.py`, `prompt_template_schema_linked.py`, `run_schema_linked.py`; **new:** `prompt_template_decline.py`, `run_schema_linked_decline.py`, `result_logging.py`.
**`sql/`:** `create_grader_role.sql` (the read-only role; fixed and tested on 26 Oct, safe to re-run).
**Result logs in `results/`:**
- `baseline_naive_2026-08-05.log` (first naive run, 46/84)
- `schema_linked_2026-10-20.log` (the bad x4 run, 35/84, keep it)
- `schema_linked_mwh_reworded_2026-10-20.log` (47/84)
- six `*_t0_run{1,2,3}_2026-10-21.log` files (the 3-run noise measurement: naive and schema-linked)
- **new:** `analysis_notes_vs_targets_2026-10-24.md` (Step D report)
- **new:** `schema_linked_decline_t0_run{1,2,3}_2026-10-24.log` and `.jsonl` (Step G; the `.jsonl` files have one line per question)
- **new:** `_stdout_decline_t0.txt` (raw console output of those three runs); similar `_stdout_*` files exist for the earlier runs

**What to commit:** loader scripts, grader, benchmark YAML, one small sample CSV, README with attribution. **Never commit:** `data/raw/`, `.env`, credentials. (There is no git repository yet; see section 12, item 6.)

---

## 15A. Findings worth telling in interviews

- **Note wording decided the outcome three times.** The "multiply by 4" note cost 11 points. The Kernenergie note was ignored. The decline sentence changed the answer style on 8 questions, in both directions. Small wording is a real lever, and it needs measuring.
- **The catalog notes did not improve the answers, but they helped the model decline.** For u_01 and u_07 the model's own reason quotes the catalog notes.
- **The extra SQL errors looked like a regression but cost no passes.** They were all on questions that fail in every run anyway. Checking before reacting mattered.
- **The one-change-per-row rule caught a real mistake.** A draft decline prompt had silently dropped the "Return only the SQL" sentence. It was caught in review, before any money was spent.

---

## 16. How to start the next chat

Paste this as your first message in the new chat, and attach this file (and `DECISIONS.md`):

> I'm continuing my text-to-SQL project on German electricity data (SMARD). The attached PROJECT_PROGRESS.md has the full state and DECISIONS.md has all decisions (D1 to D22). Short version: the grader works (self-test 84/84, runs through a read-only role). Over 3 runs at temperature 0 the naive baseline averages 46.0/84, schema-linked 46.7/84 (no measurable gain), and schema-linked plus the decline option 55.3/84 (tier 0 went from 0/8 to 7/8; tiers 1-4 moved only +1.67, within noise). Next I want to build catalog v2 as one ablation row: reword the Kernenergie note to talk about the value, add plain descriptions of the metrik and preiszone values, and state the data's date range. Please explain things in plain language and small chunks, and write commands I can paste into Claude Code.
