# Held-out checks: heldout_smard.yaml (2026-10-29)

## Verdict (safe to share: no question text, no SQL)

| Item | Verdict |
|---|---|
| validate_gold_file.py | OK: 30 items, 0 failures, 0 warnings, every gold_sql executes |
| h4_01 | OK: result is order-independent, longest run is unique (no tie) |
| h3_02 | OK: no tie at 10th place, pooled equals average of daily averages, all ten days have 96 quarter-hours |
| h2_02 | OK: no tie at 5th place; one zone (DE/AT/LU) has only NULL prices in 2025 and is dropped by the gold_sql |
| h3_03 | OK: both methods give 284, difference 0, no NULL prices in the 11 neighbour zones |
| h2_07 | OK: weekday names come back in English, lc_time is en_US.utf8 |

Two notes that are not failures:
- h4_01: the gold_sql in the file already orders by (zeitpunkt, id). So there is no "id only" version in the file to compare against. I compared the file's version with the id-only and zeitpunkt-only variants (details below).
- None of the 30 held-out items has a `gold_zeilen` key, so the validator's row-count cross-check had nothing to compare. This is not an error, because `gold_zeilen` is optional.

## Details

All queries ran as `grader_ro` (confirmed with `SELECT current_user`), PostgreSQL 16.15.

### 1. validate_gold_file.py heldout_smard.yaml
- Top level has `standard` and `fragen`. 30 items were checked.
- No structural failures: no unknown keys, ids unique, tier 1-4 items have gold_sql, reihenfolge_relevant and toleranz, tier 0 items have gold_sql null.
- All gold_sql queries ran without error. The tier-0 `beleg_sql` queries ran and returned results.
- `0 failure(s), 0 warning(s)`, `RESULT: PASS`.

### 2. h4_01
- The preise table has an integer `id` column. For the German zone in 2025 there are 35040 rows, 35036 distinct timestamps (4 duplicated timestamps, the clock-change hour) and 0 NULL prices.
- `id` order never goes backwards in time: 0 rows where an earlier id has a later timestamp.

(a) Gold_sql as written (row numbering ordered by zeitpunkt, id): start 2025-10-04 21:30, 80 quarter-hours.

(b) Result for each ordering of the row numbering:

| Ordering | Result |
|---|---|
| zeitpunkt, id (as in the file) | 2025-10-04 21:30, 80 |
| id only | 2025-10-04 21:30, 80 |
| zeitpunkt only | 2025-10-04 21:30, 80 |

All three are identical.

(c) The longest run is 80 quarter-hours, and exactly 1 run has that length, so there is no tie. The next runs are:

| Length | Start |
|---|---|
| 65 | 2025-10-04 01:15 |
| 56 | 2025-01-01 03:00 |
| 40 | 2025-03-30 08:00 |
| 40 | 2025-06-08 09:00 |

### 3. h3_02
(a) Daily solar ranking, ranks 8 to 13 (MWh):

| Rank | Day | MWh |
|---|---|---|
| 8 | 2025-06-17 | 437433.00 |
| 9 | 2025-07-01 | 434800.38 |
| 10 | 2025-06-19 | 422383.25 |
| 11 | 2025-08-11 | 421734.13 |
| 12 | 2025-06-18 | 421464.50 |
| 13 | 2025-06-14 | 419659.25 |

The 10th and 11th values differ, so there is no tie at the cut-off. The ten days are 2025-05-12, 05-13, 06-12, 06-13, 06-17, 06-19, 06-20, 06-21, 06-30 and 07-01.

(b)

| Method | Value |
|---|---|
| Pooled over all quarter-hours of the ten days | 80.1612916666666667 |
| Average of the ten daily averages | 80.1612916666666667 |
| Difference | 0 |
| Gold_sql as written | 80.1612916666666667 |

They match, because the days have equal numbers of rows (see c).

(c) Each of the ten days has 96 German price rows (0 NULL) and 96 photovoltaic rows. No day deviates from 96.

### 4. h2_02
(a) Price rows per zone in 2025: 17 zones, each with 35040 rows. NULL prices:

| Zone | NULLs |
|---|---|
| DE/AT/LU | 35040 (all of its rows) |
| all other 16 zones | 0 |

DE/AT/LU is the only zone with NULLs. The gold_sql drops it through `HAVING COUNT(preis_eur_mwh) > 0`, and it excludes '∅ Anrainer DE/LU' explicitly.

(b) Ranking by 2025 average price, excluding '∅ Anrainer DE/LU' and DE/AT/LU:

| Rank | Zone | Average |
|---|---|---|
| 1 | Italien (Nord) | 115.8635 |
| 2 | Ungarn | 108.5143 |
| 3 | Slowenien | 104.6428 |
| 4 | Polen | 104.2918 |
| 5 | Schweiz | 101.6882 |
| 6 | Österreich | 98.9442 |
| 7 | Tschechien | 96.8272 |
| 8 | Deutschland/Luxemburg | 89.3217 |

5th and 6th differ by 2.74 EUR/MWh, so there is no tie at the cut-off. `rank()` shows no shared ranks. The gold_sql returns exactly these first five rows.

### 5. h3_03
(a) Gold_sql as written, using the '∅ Anrainer DE/LU' series: **284** days.

(b) Own calculation: the mean of the 11 neighbour zones per quarter-hour, then the daily mean, compared strictly with the German daily mean: **284** days out of 366 compared. The difference is **0**.

Further comparison of the two neighbour series, 2024:
- Days where the two methods give a different verdict: 0.
- Largest absolute daily difference between my neighbour mean and the precomputed series: 0.2296 EUR/MWh. The mean difference is 0.00065.
- The smallest absolute gap between the German daily mean and the precomputed neighbour series is 0.0054. Ten days have a gap below 0.25. None of them flips under the other method.
- Ties (equal daily means): 0 under either method.

NULL prices in 2024 for each of the 11 neighbour zones (Belgien, Dänemark 1, Dänemark 2, Frankreich, Niederlande, Norwegen 2, Österreich, Polen, Schweden 4, Schweiz, Tschechien): 0 NULLs in each, with 35136 rows each (366 days × 96). Deutschland/Luxemburg and '∅ Anrainer DE/LU' also have 35136 rows and 0 NULLs.

### 6. h2_07
- Result: Wednesday, 14097.276241987179.
- All seven names come back in English, with the following averages:

| Weekday | Average |
|---|---|
| Wednesday | 14097.28 |
| Tuesday | 14021.59 |
| Thursday | 13951.32 |
| Friday | 13751.12 |
| Monday | 13629.27 |
| Saturday | 11964.60 |
| Sunday | 11302.85 |

- `SHOW lc_time` returns `en_US.utf8`. `SHOW lc_messages` also returns `en_US.utf8`.
- `to_char(..., 'Day')` pads to nine characters, which the gold_sql removes with `trim`. Without the `TM` prefix, PostgreSQL always emits English names, whatever `lc_time` says. The `TM` form would follow `lc_time`, which is English here, so this setup cannot tell the two apart.
