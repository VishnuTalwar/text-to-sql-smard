# Dry run: would the system decline fire? (R2 and R3 files, read only)

Source: every attempt in `results/r2_run{1,2,3}_2026-11-02.jsonl` and `results/r3_run{1,2,3}_2026-11-02.jsonl` whose SQL ran and returned 0 rows or only NULLs (the loop recorded these as `empty_rows` / `empty_null`). "Fires" = `empty_fact_decision(sql)`: a period is found in the SQL and every table has 0 rows for it. e/v/p = rows in erzeugung / verbrauch / preise.

| Row | Run | Id | Tier | Attempt | Result | Period found in the SQL, rows (e/v/p) | System decline fires |
|---|---:|---|---:|---:|---|---|---|
| R2 | 1 | t4_03 | 4 | 1 | 0 rows | - | no |
| R2 | 1 | t4_03 | 4 | 2 | 0 rows | - | no |
| R2 | 1 | t4_03 | 4 | 3 | 0 rows | - | no |
| R2 | 1 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 1 | u_08 | 0 | 2 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 1 | u_08 | 0 | 3 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 2 | t4_03 | 4 | 1 | 0 rows | - | no |
| R2 | 2 | t4_03 | 4 | 2 | 0 rows | - | no |
| R2 | 2 | t4_03 | 4 | 3 | 0 rows | - | no |
| R2 | 2 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 2 | u_08 | 0 | 2 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 2 | u_08 | 0 | 3 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 3 | t4_03 | 4 | 1 | 0 rows | - | no |
| R2 | 3 | t4_03 | 4 | 2 | 0 rows | - | no |
| R2 | 3 | t4_03 | 4 | 3 | 0 rows | - | no |
| R2 | 3 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 3 | u_08 | 0 | 2 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R2 | 3 | u_08 | 0 | 3 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R3 | 1 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R3 | 2 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |
| R3 | 3 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01: e0/v0/p0 | **yes** |

**Summary:** empty results by question: R2 t4_03: 9 (fires on 0); R2 u_08: 9 (fires on 9); R3 u_08: 3 (fires on 3).
The system decline would fire on: u_08. It would not fire on t4_03 (0 rows, but the SQL has no condition on zeitpunkt). Expected: only u_08.

# Prediction for row R3b (R3 with the empty fact replaced by a system decline), written before the run
- Base: v2b_fresh 60.00; R3 59.67. Model gpt-4o-2024-08-06.
- System decline fires on u_08 in every run where its SQL returns an empty result for July 2026 (expected 3 of 3), so u_08 passes in those runs.
- It fires on no tier 1-4 question (no gold query is empty, and the dry run shows only u_08).
- Tier 0 between 7 and 8, depending on u_05's attempt-1 variation.
- Total within noise of 60.00; expected gain about +1 (u_08).
- No made-up constants for u_08 (no SELECT 0).
- Decline review: still expected to fire on 0 questions on this base.
