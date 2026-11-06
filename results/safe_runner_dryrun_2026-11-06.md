# Safe runner: dry run on history (2026-11-06)

Every agent SQL in every `results/*.jsonl` (all rows, all runs, all attempts) went through wall 1 (static check) and wall 2 (EXPLAIN, no ANALYZE) of `grader/safe_runner.py`. No query was run, no API call was made, no result file was changed. Script: `grader/safe_runner_dryrun.py`.

Limits used: max_plan_cost 15533613.4, max_rows 20000, timeout_ms 30000 (grader/limits.yaml). Walls 3 (row cap, timeout) are not part of a dry run.

## Scope

- Result files read: 39 `.jsonl` files. Files with "heldout" in the name were skipped by name and never opened: 6 (v2b_heldout_smard_heldout_run1_2026-10-30.jsonl, v2b_heldout_smard_heldout_run2_2026-10-30.jsonl, v2b_heldout_smard_heldout_run3_2026-10-30.jsonl, v2b_heldout_smard_heldout_v2_run1_2026-10-30.jsonl, v2b_heldout_smard_heldout_v2_run2_2026-10-30.jsonl, v2b_heldout_smard_heldout_v2_run3_2026-10-30.jsonl).
- Rows without a `.jsonl` file (the earliest `.log`-only runs) have no stored SQL and are not covered.
- Agent queries checked: **2910** (570 distinct SQL texts). A query is every non-empty `extracted_sql` of every attempt (loop rows) or of the answer (single-call rows). Declines contain no SQL and are not counted.

## Summary

- Would be blocked: **5** of 2910 (0.17%).
- Passed walls 1 and 2: 2845. Of these, largest estimated plan cost 347455.9 (limit 15533613.4).
- PostgreSQL error already at EXPLAIN (the query was broken before the walls could judge it, e.g. unknown column): 60. These are not blocks; the loop handles them as before.
- Blocked queries that were the final answer of their question-run: 3; of these, the answer had **passed** in history: **0**.

### Blocked, by wall

| Wall | Count |
|---|---|
| 1 | 5 |
| 2 | 0 |

### Blocked, by wall and reason

| Wall | Reason | Count |
|---|---|---|
| 1 | could not be parsed as one SELECT | 2 |
| 1 | the query reads none of the tables erzeugung, verbrauch, preise | 3 |

## Blocked queries

`final` = this query was the answer the row was graded on; `passed` = that answer passed in history (for an earlier attempt it is the outcome of the question-run).

| Row | Run | Id | Attempt | Wall | Reason | final | passed |
|---|---|---|---|---|---|---|---|
| r2 | 2 | t4_04 | 2 | 1 | the text could not be parsed as one SELECT statement (Invalid expression / Unexpected token near "AS", line 12) | no | no |
| r3 | 1 | u_08 | 2 | 1 | the query reads none of the tables erzeugung, verbrauch, preise | yes | no |
| r3 | 2 | u_08 | 2 | 1 | the query reads none of the tables erzeugung, verbrauch, preise | yes | no |
| r3 | 3 | u_08 | 2 | 1 | the query reads none of the tables erzeugung, verbrauch, preise | yes | no |
| r3b | 1 | t4_04 | 2 | 1 | the text could not be parsed as one SELECT statement (Invalid expression / Unexpected token near "SELECT", line 12) | no | no |

### SQL of the blocked queries (distinct)

**r2 run 2 t4_04** (wall 1: the text could not be parsed as one SELECT statement (Invalid expression / Unexpected token near "AS", line 12))

```sql
SELECT MAX(consecutive_quarters) AS longest_negative_run
FROM (
  SELECT zeitpunkt, 
         preis_eur_mwh, 
         ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
         ROW_NUMBER() OVER (PARTITION BY preis_eur_mwh < 0 ORDER BY zeitpunkt) AS grp
  FROM preise
  WHERE preiszone = 'Deutschland/Luxemburg'
) subquery
WHERE preis_eur_mwh < 0
GROUP BY grp
HAVING COUNT(*) AS consecutive_quarters
ORDER BY longest_negative_run DESC
LIMIT 1;
```

**r3 run 1 u_08** (wall 1: the query reads none of the tables erzeugung, verbrauch, preise)

```sql
SELECT 0 AS total_wind_generation
```

**r3 run 2 u_08** (wall 1: the query reads none of the tables erzeugung, verbrauch, preise)

```sql
SELECT 0 AS total_mwh
```

**r3 run 3 u_08** (wall 1: the query reads none of the tables erzeugung, verbrauch, preise)

```sql
SELECT 0 AS total_wind_generation;
```

**r3b run 1 t4_04** (wall 1: the text could not be parsed as one SELECT statement (Invalid expression / Unexpected token near "SELECT", line 12))

```sql
SELECT MAX(consecutive_quarters) AS longest_negative_run
FROM (
  SELECT zeitpunkt, 
         preis_eur_mwh, 
         ROW_NUMBER() OVER (ORDER BY zeitpunkt) - 
         ROW_NUMBER() OVER (PARTITION BY preis_eur_mwh < 0 ORDER BY zeitpunkt) AS grp
  FROM preise
  WHERE preiszone = 'Deutschland/Luxemburg'
) subquery
WHERE preis_eur_mwh < 0
GROUP BY grp
SELECT COUNT(*) AS consecutive_quarters
FROM subquery
WHERE preis_eur_mwh < 0
GROUP BY grp;
```

## Queries that fail in EXPLAIN (not blocks)

- 17 x column "zero_stretch" does not exist
- 11 x column "consecutive_intervals" does not exist
- 10 x column "consecutive_quarters" does not exist
- 7 x window functions are not allowed in window definitions
- 7 x column "consecutive_count" does not exist
- 2 x column "is_zero" does not exist
- 2 x column "mwh" does not exist
- 1 x column "streak_length" does not exist
- 1 x column "zero_output" does not exist
- 1 x column "zero_streak" does not exist
- 1 x column "preise.zeitpunkt" must appear in the GROUP BY clause or be used in an aggregate function

## Per row

| Row | Queries | Blocked |
|---|---|---|
| df | 198 | 0 |
| exa | 193 | 0 |
| exb | 180 | 0 |
| r1 | 233 | 0 |
| r2 | 248 | 1 |
| r3 | 244 | 3 |
| r3b | 243 | 1 |
| schema_linked_decline_t0 | 229 | 0 |
| v2a_t0 | 228 | 0 |
| v2b2_t0 | 229 | 0 |
| v2b_fresh | 231 | 0 |
| v2b_t0 | 231 | 0 |
| v2c_t0 | 223 | 0 |

