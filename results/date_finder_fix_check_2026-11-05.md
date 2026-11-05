# Date finder fix check, 2026-11-05

Source: every attempt in `results/r2_run{1,2,3}_2026-11-02.jsonl`, `results/r3_run{1,2,3}_2026-11-02.jsonl` and `results/r3b_run{1,2,3}_2026-11-05.jsonl` whose SQL ran and returned 0 rows or only NULLs (`empty_rows` / `empty_null`). No API call; read-only database. Old finder = `grader/date_facts.py` at commit 869b4d7 (before D40); new finder = conservative version (UNKNOWN unless every condition on zeitpunkt is understood). "Fires" = a period was found and every table has 0 rows for it.

| Row | Run | Id | Tier | Attempt | Result | Old finder: period | Old fires | New finder: period | New fires | Changed |
|---|---:|---|---:|---:|---|---|---|---|---|---|
| R2 | 1 | t4_03 | 4 | 1 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 1 | t4_03 | 4 | 2 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 1 | t4_03 | 4 | 3 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 1 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 1 | u_08 | 0 | 2 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 1 | u_08 | 0 | 3 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 2 | t4_03 | 4 | 1 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 2 | t4_03 | 4 | 2 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 2 | t4_03 | 4 | 3 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 2 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 2 | u_08 | 0 | 2 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 2 | u_08 | 0 | 3 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 3 | t4_03 | 4 | 1 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 3 | t4_03 | 4 | 2 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 3 | t4_03 | 4 | 3 | 0 rows | - | no | UNKNOWN | no | no |
| R2 | 3 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 3 | u_08 | 0 | 2 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R2 | 3 | u_08 | 0 | 3 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R3 | 1 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R3 | 2 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R3 | 3 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R3b | 1 | t4_03 | 4 | 1 | 0 rows | - | no | UNKNOWN | no | no |
| R3b | 1 | t4_03 | 4 | 2 | 0 rows | - | no | UNKNOWN | no | no |
| R3b | 1 | t4_03 | 4 | 3 | 0 rows | - | no | UNKNOWN | no | no |
| R3b | 1 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R3b | 2 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |
| R3b | 3 | t4_03 | 4 | 1 | 0 rows | - | no | UNKNOWN | no | no |
| R3b | 3 | t4_03 | 4 | 2 | 0 rows | - | no | UNKNOWN | no | no |
| R3b | 3 | t4_03 | 4 | 3 | 0 rows | - | no | UNKNOWN | no | no |
| R3b | 3 | u_08 | 0 | 1 | only NULL | 2026-07-01..2026-08-01 | yes | 2026-07-01..2026-08-01 | yes | no |

**Summary** (empty attempts; old fires; new fires): R2 t4_03: 9, 0, 0; R2 u_08: 9, 9, 9; R3 u_08: 3, 3, 3; R3b t4_03: 6, 0, 0; R3b u_08: 3, 3, 3.

Decisions that changed between the old and the new finder: **0** of 30.
The new finder fires on `u_08` in every run where the old one did and does not fire on `t4_03`: the old finder found no period in it; the new one reports UNKNOWN (it joins `erzeugung` and `verbrauch` on zeitpunkt, which counts as a condition on zeitpunkt in a JOIN ON clause). Both do not fire. Expected: no change; confirmed.
