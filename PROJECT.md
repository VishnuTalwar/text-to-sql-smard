# Natural-Language Analytics Agent — SMARD / German Electricity Market

A system that takes a question in plain English or German, turns it into SQL, runs it
safely against a real PostgreSQL database, and returns a chart plus a written answer
with the query on display.

**Status:** data loaded, benchmark written, grading script is the next piece.
**Last updated:** 3 August 2026

---

## 1. What this project is, and why it exists

### The goal

Build something that demonstrates real LLM engineering rather than a demo notebook.
The point of difference is not that a model can write SQL — it can — but everything
built around it: grounding it in a real schema, checking its output before execution,
recovering from its mistakes, and **measuring** whether any of it works.

### Why text-to-SQL specifically

- Almost every company wants this internally, so it reads as useful rather than academic
- It forces real tool use, not just retrieval
- The failure modes are concrete and measurable, which makes the evaluation story honest
- German energy data connects to a large employment sector and supports a bilingual angle

### The thing to be able to say afterwards

Not *"I built a text-to-SQL agent."* That invites polite nodding.

Instead: *"Schema linking took accuracy from X to Y, few-shot retrieval added Z, and the
repair loop added more but tripled p95 latency, so I capped it at three attempts."*

That sentence is only available if the benchmark exists first. Which is why it does.

---

## 2. The data

### Source

[SMARD.de](https://www.smard.de) — the Bundesnetzagentur's open electricity market
platform. Free to use with attribution. Downloads are capped at two years per file,
so the range was assembled from several exports.

**Attribution line for the README:** Data source: Bundesnetzagentur | SMARD.de

### Coverage

| | |
|---|---|
| Period | 2023-06-01 00:00 – 2026-06-01 23:45 |
| Resolution | 15 minutes |
| Timestamps per series | 105,312 |
| Categories loaded | Realisierte Erzeugung, Realisierter Stromverbrauch, Großhandelspreise |

### Deliberately not loaded

- **System stability** (balancing energy, control reserve) — specialist vocabulary that
  would need to be learned properly just to write correct benchmark questions
- **Prognostizierte Erzeugung Intraday** — too similar to Day-Ahead; gives the model two
  near-identical tables to confuse
- **Installierte Erzeugungsleistung** — good candidate for a later extension, because it
  sits at a different time granularity (yearly vs. quarter-hourly) and mixing granularities
  is the classic real-world trap

---

## 3. Database design

### Schema

```sql
CREATE TABLE erzeugung (
    id             serial PRIMARY KEY,
    zeitpunkt      timestamp NOT NULL,
    energietraeger text      NOT NULL,
    mwh            numeric
);

CREATE TABLE verbrauch (
    id        serial PRIMARY KEY,
    zeitpunkt timestamp NOT NULL,
    metrik    text      NOT NULL,
    mwh       numeric
);

CREATE TABLE preise (
    id             serial PRIMARY KEY,
    zeitpunkt      timestamp NOT NULL,
    preiszone      text      NOT NULL,
    preis_eur_mwh  numeric
);
```

### Column values

**`erzeugung.energietraeger`** (12)
Biomasse, Wasserkraft, Wind Offshore, Wind Onshore, Photovoltaik, Sonstige Erneuerbare,
Kernenergie, Braunkohle, Steinkohle, Erdgas, Pumpspeicher, Sonstige Konventionelle

**`verbrauch.metrik`** (4) — English, matching this table's source CSV (unlike erzeugung/preise, which are German)
grid load, Grid load incl. hydro pumped storage, Hydro pumped storage, Residual load

**`preise.preiszone`** (17)
Deutschland/Luxemburg, ∅ Anrainer DE/LU, Belgien, Dänemark 1, Dänemark 2, Frankreich,
Niederlande, Norwegen 2, Österreich, Polen, Schweden 4, Schweiz, Tschechien, DE/AT/LU,
Italien (Nord), Slowenien, Ungarn

### Why long format instead of wide

The source CSV arrives **wide**: one row per timestamp, one column per energy source.
It was reshaped to **long**: one row per timestamp *per source*.

The motivating example is *"which energy source produced the most in June?"*

- **Wide:** the model must compare twelve separate columns against each other. There is no
  clean way to write that. It gets it wrong repeatedly, and the table is to blame.
- **Long:** group by source, sum, sort descending, take the top row. One straightforward query.

Secondary benefits: adding a source later means new rows rather than a schema change, and
the schema catalog shrinks from describing fourteen columns to describing three.

---

## 4. Data quirks that matter

These are all real properties of the loaded data. Several are deliberately exploited by
benchmark questions.

**Values are work (MWh), not power (MW).** Each figure is the energy in one quarter-hour.
Multiply by 4 to get MW. This creates genuine ambiguity on "grid load" questions — see
open item O6.

**Kernenergie is NULL, not zero.** Measurements exist only up to 2024-01-30 and are all
zero; everything after is NULL. `SUM()` returns NULL there, not 0. Any `ORDER BY ... DESC`
needs `NULLS LAST` or Kernenergie sorts to the top.

**`DE/AT/LU` price zone exists but is entirely empty** across the whole period. The joint
bidding zone was split in 2018.

**Daylight saving.** Three autumn changeovers (2023-10-29, 2024-10-27, 2025-10-26) produce
four duplicate local timestamps each — twelve in total. The three spring days have 23 hours.
Affects t3_12 and any gap analysis.

**Row counts confirm duplicates were kept.** 1,097 days × 96 = 105,312, which matches the
observed count exactly. That only works if the autumn duplicates were inserted and the
spring gaps left as gaps. Confirmed: the tables use a surrogate `id` primary key rather than
a composite key on (timestamp, category), which is what lets the duplicates be stored. Still
worth being careful with gaps-and-islands queries at DST boundaries.

**`Pumpspeicher` means opposite things in two tables.** In `erzeugung` it is electricity
generated by releasing water. In `verbrauch` it is electricity consumed to pump water up.

**Exactly-zero solar occurs only on 2026-06-01** (24 quarter-hours). Every other night
SMARD reports small values like 0.25 or 0.5. That last day is likely still preliminary.

**The tail is thin.** June 2026 contains a single day; July 2026 contains nothing. Benchmark
questions therefore use 2024 and 2025.

---

## 5. Loading — the five things that bite

1. **Separator is a semicolon**, not a comma
2. **Byte-order mark at the start of the file.** Without `encoding='utf-8-sig'` the first
   column name carries an invisible character and every lookup on it fails mysteriously
3. **German number format.** `1.542,63` means 1542.63 — dot is thousands, comma is decimal,
   the exact opposite of the default assumption. Strip dots, swap comma for dot
4. **A dash means missing, not zero.** Store as NULL. Zero means "measured, was nothing";
   NULL means "no number exists". Confusing them produces confidently wrong answers
5. **Dates are day-first.** `01.06.2026` is 1 June. Tell the parser explicitly or it guesses
   wrong on every day below the 13th

### Post-load verification

Run after any reload:

```sql
-- 1. Row count
SELECT COUNT(*) FROM erzeugung;

-- 2. All sources present, and NULL handling correct
SELECT energietraeger, COUNT(*) AS rows, COUNT(mwh) AS with_value
FROM erzeugung GROUP BY energietraeger ORDER BY energietraeger;

-- 3. Time range and gaps
SELECT MIN(zeitpunkt), MAX(zeitpunkt), COUNT(DISTINCT zeitpunkt) FROM erzeugung;

-- 4. Spot-check against the CSV (catches the German number bug)
SELECT energietraeger, mwh FROM erzeugung
WHERE zeitpunkt = '2026-06-01 00:00' ORDER BY energietraeger;

-- 5. Does the sun behave like the sun?
SELECT EXTRACT(HOUR FROM zeitpunkt) AS stunde, ROUND(AVG(mwh), 1) AS schnitt
FROM erzeugung WHERE energietraeger = 'Photovoltaik'
GROUP BY 1 ORDER BY 1;
```

Check 5 is the strongest single test. If the curve looks like a sunrise, timestamps *and*
numbers are both correct — that shape cannot happen by accident.

---

## 6. Architecture

The useful mental model: **a new analyst on their first day.** Smart, but has never seen
this database. To make them useful you show them where the data lives, give them notes on
what each table means, show worked examples, have someone check their work before it runs,
and give them an account that can read but not delete.

Every component below is one of those things.

| # | Component | Role | Status |
|---|---|---|---|
| 1 | PostgreSQL in Docker | Where the data lives | **Done** |
| 2 | Schema catalog | Table and column descriptions the model can retrieve | Not started |
| 3 | Example bank | ~30 question/SQL pairs, retrieved by similarity | Not started |
| 4 | Query writer | The LLM call that produces SQL | Not started |
| 5 | Validator | AST check + `EXPLAIN` dry run | Not started |
| 6 | Retry loop | Feed errors back, max 3 attempts (LangGraph) | Not started |
| 7 | Safe runner | Read-only role, statement timeout, row cap | Partly — role to confirm |
| 8 | Presenter | Chart type from result shape + written answer + SQL shown | Not started |
| 9 | Evaluation harness | The 84-question exam and its grader | **Benchmark done**, grader next |
| 10 | Observability | Langfuse traces of every question and retry | Not started |

### Component notes

**2 — Schema catalog.** For each table and column: what it holds, its type, two or three
example values. The model cannot see the database; it only sees what is put in front of it.
Show nothing and it invents column names. Show everything and the signal drowns. So retrieve
only the relevant slice per question. This is expected to be the single largest accuracy lever.

**3 — Example bank.** Showing beats telling. An instruction about German date handling gets
half-followed; three worked examples get copied.

**4 — Query writer.** The smallest part of the project, perhaps fifty lines. Worth saying
plainly in interviews: the model writing SQL is the easy bit.

**5 — Validator.** Three checks in order: parse with `sqlglot` and walk the AST; confirm the
statement only reads; confirm every table and column exists in the catalog. Then `EXPLAIN` as
a dry run — the planner catches type and join errors without touching a row.

**6 — Retry loop.** Three attempts, then fail honestly. Retry *rate* is itself a metric: if
most questions need two attempts, the query writer is weak and the loop is papering over it.

**7 — Safe runner.** Separate read-only database account, session-level `statement_timeout`,
row cap. The loader uses a different account with write rights. Assume every other layer will
eventually be fooled; make that survivable.

**8 — Presenter.** Chart chosen from result shape: single value → big number; date + value →
line; category + value → bars. The SQL is always displayed and editable. Hiding it looks
slicker and destroys trust with exactly the people who will evaluate this.

---

## 7. Design decisions and their reasoning

All design decisions are recorded in DECISIONS.md.

---

## 8. Evaluation

### The exam

`gold_set_smard.yaml` — 84 items, every `gold_sql` executed against the real loaded data.

| Tier | Count | Shape |
|---|---|---|
| 0 — unanswerable | 8 | Correct behaviour is to decline, not to invent |
| 1 — single aggregate | 35 | One aggregate, one or two filters |
| 2 — grouping and ranking | 25 | `GROUP BY`, ordering, shares |
| 3 — dates and comparisons | 12 | Sub-queries, CTEs, cross-table |
| 4 — hard | 4 | Window functions, gaps-and-islands, two-table joins |

### Metrics

**Execution accuracy** is the headline: does the agent's result set match the gold result set?

Supporting metrics, each of which changes what to do next:

| Metric | What a bad value tells you |
|---|---|
| Accuracy **per tier** | Where it breaks — add examples for that tier |
| Valid-SQL rate, first attempt | Broken SQL → schema linking is weak. Valid but wrong → intent understanding is weak. **Opposite fixes** |
| Retry rate | The repair loop is carrying the query writer |
| Latency p50 / p95 | Averages hide tails, and tails are what stop people using a tool |
| Cost per query | Whether this could exist in production |
| Abstention accuracy (tier 0) | Whether it invents answers when it shouldn't |

Run each configuration three times. If accuracy moves 4 points and run-to-run variance is 6,
nothing was learned.

### Planned ablation table for the README

| Configuration | Execution accuracy |
|---|---|
| Naive prompt, full schema dumped | *baseline* |
| + schema linking | |
| + retrieved few-shot examples | |
| + validation and self-correction | |

### The grading script

Per question: send `frage` to the agent → run the agent's SQL → run `gold_sql` → compare →
record pass/fail. For tier 0 there is no `gold_sql`; pass means the agent declined.

Comparison rules: row count first; then sort both sides unless order matters; then compare
cell by cell **by position, not column name** (the agent will not reproduce the aliases
`mwh`, `eur_mwh`, `n`, `stunde`, `monat`); numbers within tolerance, text exact.

**Build it with a self-test mode.** Feed the gold SQL in as if the agent had written it —
it must score 84/84. Any failure is a grader bug found in ten minutes rather than a week of
chasing phantom agent failures.

---

## 9. Current status

### Done

- [x] SMARD data downloaded across three categories, 2023-06-01 – 2026-06-01
- [x] Loaded into PostgreSQL in Docker (`text-to-sql-db` container), three tables, long format
- [x] Post-load verification queries run
- [x] Benchmark written: 84 items, all gold SQL executed against real data, pitfalls documented

### Benchmark quality — verified

Internal consistency was cross-checked and holds:

- June 2025 solar total ÷ 2,880 quarter-hours = 3,658.37, exactly the June average in t3_03
- `Erneuerbar` in t2_15 matches `erneuerbar_mwh` in t3_07 to the last decimal
- Wind Onshore's 24.38% share in t2_07 equals its total ÷ the combined figure in t2_15
- Solar 2024 in t3_06 matches Photovoltaik 2024 in t2_11
- The 936.28 €/MWh peak on 2024-12-12 is the real Dunkelflaute price spike

These could not line up if any figure were estimated.

### Next

**The grading script**, with a self-test mode. Nothing else can be measured until it exists.

---

## 10. Open items

Findings from the benchmark review, roughly in priority order.

| # | Item | Action |
|---|---|---|
| O1 | No field records whether row order is part of the answer | Add `reihenfolge_relevant`. Default false; set true on t2_02, t2_05, t2_11, t2_17, t2_22, t2_25, t4_01, t4_02, t4_04 |
| O2 | t2_21 reads as order-sensitive but several zones sit exactly at the −500 cap | Leave `reihenfolge_relevant: false` — the tied order is undetermined |
| O3 | No float tolerance defined | Add `toleranz`, with a looser override on the `ROUND()` items: t2_07, t3_02, t3_06, t3_07, t3_10, t3_12 |
| O4 | 22 `gold_antwort` fields are truncated with "…" | Grader must execute `gold_sql`. Treat `gold_antwort` as human documentation only |
| O5 | Years print as `2 023` in t2_13 and t2_18 — thousands separator applied to a year | Compare raw values; format only for display |
| O6 | "Grid load" questions (t1_05, t1_13, t1_18) are answered in MWh per quarter-hour, but a person asking about *load* expects MW | Decide and write down whether 52,994 MW counts as correct alongside 13,248.60 MWh |
| O7 | Tier 1 is 42% of the set, uses zero `GROUP BY` and zero joins — one query template | Report per-tier scores. Treat the headline number as nearly meaningless |
| O8 | Only 7 of 84 questions are German, and most hand over the exact schema literal (`Photovoltaik`, `braunkohle`, `Energieträger`) | Add German questions that avoid the literal: *Sonnenstrom*, *Kohlestrom*, *Windkraft an Land* |
| O9 | t1_30 and t4_02 both depend on exactly-zero solar, which occurs only on the preliminary last day | Keep them; annotate as tied to a data artifact so future debugging doesn't chase a working grader |
| O10 | No "ambiguous, should ask back" category | Optional third behaviour: e.g. *"wie viel Kohle?"* could mean Braunkohle or Steinkohle |
| O11 | Read-only database role | Confirm it exists and that the agent will use it, not the loader account |
| O12 | Duplicate DST timestamps appear to have been inserted | **Resolved.** The tables use a surrogate `id` primary key (confirmed in the database), which is what lets the 12 duplicate daylight-saving timestamps be stored |
| O13 | No held-out set. Every ablation row is tuned and measured on the same 84 questions, so repeated rewording risks fitting the prompt to the exam | Build a small held-out set (questions not used for tuning) before the final README numbers |

---

## 11. Build order from here

1. **Grading script** with self-test — must score 84/84 on gold SQL
2. Naive agent: dump the whole catalog, take the SQL, run it — **first real score**
3. Schema catalog + retrieval — score again
4. Example bank + similarity retrieval — score again
5. Validator + retry loop — score again
6. Streamlit UI, charts, SQL visible and editable
7. Langfuse tracing; benchmark in CI on every push
8. README with the ablation table

Steps 3, 4 and 5 each get their own row in the ablation table. That table is the most
valuable artifact in the project.

---

## 12. Tech stack

| Layer | Choice |
|---|---|
| Database | PostgreSQL 16 in Docker |
| Loading | Python + pandas |
| Query validation | sqlglot (AST) + `EXPLAIN` |
| Orchestration | LangGraph |
| Model | Hosted to start; local model comparison later for the on-prem angle |
| UI | Streamlit |
| Tracing | Langfuse |
| Benchmark | YAML + a Python grader |
| CI | GitHub Actions |

### Repository hygiene

- **Commit:** loader, grader, benchmark YAML, one small sample CSV, README with attribution
- **Do not commit:** raw data folder, `.env`, credentials
- Two database accounts: one for loading (write), one for the agent (read-only)

---

## 13. For the CV and the interview

**Draft bullet** — fill the numbers once the ablation table exists:

> Built a natural-language analytics agent over 3 years of German electricity market data
> (LangGraph, PostgreSQL, sqlglot). Raised execution accuracy from X% to Y% on a self-built
> 84-question benchmark via schema linking and self-correction. Read-only execution sandbox
> with AST-level query validation.

**Questions to be ready for**

- *Why not just prompt the model harder?* — Schema linking moved accuracy more than any
  prompt change; the model cannot see the database, only what you put in front of it.
- *How do you know it works?* — 84-question benchmark, execution accuracy, per-tier scores,
  three runs per configuration to separate signal from noise.
- *What if someone injects a malicious query?* — AST validation rejects anything that isn't a
  read; and independently, the database account has no permission to write. Defence in depth.
- *Why regex isn't enough* — comments and nested statements bypass it; the AST is the actual
  structure.
- *What was hardest?* — answer from the failure log once it exists, not from memory.
