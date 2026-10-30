# House-style inventory of gold_sql (tiers 1-4), 2026-10-29

Source: `gold_set_smard.yaml`, field `gold_sql` of the 76 tier 1-4 items (35 T1, 25 T2, 12 T3, 4 T4). Tier 0 is excluded. Nothing was executed. The question text (`frage`) was used only to decide which items count as "Which X" questions in section 3.

## 1. Percentages

**Pattern: 0-100 scale, `ROUND(100 * ..., 2)`, two decimals.** The percent columns are aliased `*_prozent`. Consistent across the gold set. There is no 0-1 share and no other rounding precision.

| Item | Percent column |
|---|---|
| t2_07 | `anteil_prozent` |
| t3_02 | `wind_anteil_prozent` |
| t3_06 | `veraenderung_prozent` |
| t3_07 | `deckung_prozent` |
| t3_10 | `solaranteil_prozent` |
| t3_12 | `abweichung_prozent` |

- **Sign:** `veraenderung_prozent` (t3_06) and `abweichung_prozent` (t3_12) are signed change figures. The other four are plain shares.
- **Other ROUND uses:** `ROUND(..., 2)` also appears on non-percent columns. These are `durchschnitt_mwh` (t3_12) and `stunden` (t4_02, t4_04, as `ROUND(COUNT(*) / 4.0, 2)`).
- **Unrounded values:** every other SUM, AVG, MAX and MIN is returned unrounded, including the AVG prices.
- **Tolerance:** `toleranz` is 1e-3 for exactly the six percent items. t4_02 and t4_04 contain a ROUND but keep the default 1e-6.

## 2. Time buckets

| Bucket | Returned as | Items |
|---|---|---|
| Month | `date_trunc('month', zeitpunkt)::date`, first of month, DATE, alias `monat` | t2_04, t2_09, t2_16, t2_24, t3_03, t3_10 |
| Quarter | `date_trunc('quarter', zeitpunkt)::date`, DATE, alias `quartal` | t2_20 |
| Week | `date_trunc('week', zeitpunkt)::date`, DATE, alias `woche` | t4_01 |
| Day | `zeitpunkt::date`, DATE, alias `tag` | t3_01, t3_04, t3_05, t3_09, t3_12 |
| Year | `EXTRACT(YEAR FROM zeitpunkt)::int`, integer, alias `jahr` | t2_13, t2_18, t2_23 |
| Month of year (1-12) | `EXTRACT(MONTH FROM zeitpunkt)::int`, integer, alias `monat` | t2_19 |
| Hour of day (0-23) | `EXTRACT(HOUR FROM zeitpunkt)::int`, integer, alias `stunde` | t2_03, t2_08, t2_10 |
| Weekday name | `trim(to_char(zeitpunkt, 'Day'))`, text, alias `wochentag` | t2_12 |
| Absolute hour | `date_trunc('hour', zeitpunkt)`, no `::date` cast, so TIMESTAMP, alias `stunde` | t4_03 |

**Verdict: consistent by bucket type, with one exception and some mixing.**
- **Rule:** calendar buckets (month, quarter, week, day) are `date_trunc(...)::date` or `::date`. Cyclic or numeric buckets (year, month-of-year, hour-of-day) are `EXTRACT(...)::int`.
- **Alias `monat` is overloaded.** It is a DATE (first of month) in six items and an integer 1-12 in t2_19.
- **Alias `stunde` is overloaded.** It is an integer 0-23 in t2_03, t2_08 and t2_10. In t4_03 it is a full TIMESTAMP truncated to the hour.
- **t4_03 is the only `date_trunc` without `::date`.** That is expected, because a date cast would drop the hour.
- **`TO_CHAR` appears once.** t2_12 is the only item that returns a time bucket as text. No year or month label is ever formatted with `TO_CHAR`.
- **Not bucket outputs:** t3_06 uses `EXTRACT(YEAR)` only inside a CTE, and its output is pivoted into `mwh_2024` and `mwh_2025`. t3_08 uses `EXTRACT(ISODOW)` only inside a CASE.
- **Raw timestamps** are returned by t2_14 (`zeitpunkt`) and by t4_02 and t4_04 (`MIN`/`MAX(zeitpunkt)` as `beginn`/`ende`). These are row-level or boundary values, not buckets.
- **Row order:** time-bucket outputs are always `GROUP BY 1 ORDER BY 1`, so ascending chronological. The exception is "top bucket" items (t2_09, t2_20, t3_01, t3_05, t3_12), which sort by the measure with `LIMIT 1`.

## 3. "Which X" questions: label only, or label + value?

**Pattern A: label + one value column.** Consistent across the gold set. No gold_sql returns the label alone, and the value is always the measure being ranked.

| Item | Columns returned |
|---|---|
| t2_01 | `energietraeger, mwh` |
| t2_06 | `preiszone, eur_mwh` |
| t2_09 | `monat, mwh` |
| t2_11 | `energietraeger, mwh` |
| t2_12 | `wochentag, mwh` |
| t2_14 | `zeitpunkt, eur_mwh` |
| t2_20 | `quartal, mwh` |
| t3_01 | `tag, mwh` |
| t3_05 | `tag, spanne_mwh` |

**Pattern B: label + several value columns.**
- t3_12 returns `tag, tages_mwh, durchschnitt_mwh, abweichung_prozent`. Its question asks for the day and the gap to the average.
- t4_03 returns `stunde, erzeugt, verbraucht, ueberschuss_mwh`. Its question asks only which hours.

**Pattern C: two labels + value.** t4_01 returns `woche, energietraeger, mwh`.

**Pattern D: label only.** No items.

**Related items (not worded "which X")** that also carry the identified entity next to the answer:
- t3_04 returns `tag, energietraeger, mwh`. The expensive day is repeated on every row. The price on that day is not returned.
- t3_09 returns `tag, eur_mwh`. The question asks only for the price, but the windiest day is also returned. Its wind total is not returned.
- Ranking items (t2_02, t2_05, t2_17, t2_21, t2_22, t2_25) also return label + value.

**Verdict:** consistent on "label is never returned alone". The number of extra value columns varies: one in most items, three in t3_12 and t4_03.

## 4. Column order

**Label(s) first, then value(s). Consistent, no exceptions.**
- Single label + value: every T2 item, plus t3_01, t3_05, t3_09 and t3_11.
- Two labels, time dimension first: t3_04 returns `tag, energietraeger, mwh` and t4_01 returns `woche, energietraeger, mwh`.
- Value ordering within multi-value rows:
  - Base quantities come before derived ones: t3_06, t3_07, t3_12, t4_03, t4_02.
  - Counts come before averages: t3_11 returns `gruppe, n, eur_mwh`.
  - The measure comes before its share: t2_07 returns `energietraeger, mwh, anteil_prozent`.
- Items with no label column: all T1 (single scalar), t3_02 (single percent), and t3_06 and t3_07 (values only, one row).

## 5. Other conventions

**Row shape**
- All 35 T1 items return exactly one row and one column.
- One-row "top" answers are `ORDER BY <measure> DESC LIMIT 1`: t2_01, t2_06, t2_09, t2_12, t2_20, t3_01, t3_05, t3_12, t4_02, t4_04.
- Top-N uses `LIMIT 3` (t2_05) or `LIMIT 5` (t2_14).
- Per-group top-1 uses `ROW_NUMBER() ... WHERE rn = 1` (t4_01).

**Sorting**
- Every multi-row gold_sql has an `ORDER BY`. 38 of the 76 items contain an `ORDER BY` anywhere (t3_09 only inside its CTE), and 24 of those contain no `LIMIT`. Items with `reihenfolge_relevant: true` (8): t2_02, t2_05, t2_11, t2_14, t2_17, t2_22, t2_25 and t3_08.
- Rankings and "top" queries sort DESC by the measure. The only ASC sorts are t2_21 (lowest minimum price first), t3_12 (lowest day), and the chronological `ORDER BY 1` on bucketed outputs.
- Tie-breaks are almost absent. Only t2_14 adds a secondary key (`..., zeitpunkt`). The other `LIMIT` items have none.
- `NULLS LAST` is mixed.
  - Present on DESC sorts in: t2_01, t2_02, t2_05, t2_07, t2_11, t2_14, t2_17, t2_22, t3_04, t4_01 (inside the window).
  - Absent on DESC sorts in: t2_06, t2_09, t2_12, t2_15, t2_20, t2_25, t3_01, t3_05, t3_08, t4_02, t4_04.
  - Of those eleven, t2_06 and t2_25 are guarded by a `HAVING` clause (see NULL handling) and t4_02 and t4_04 sort on a COUNT, which cannot be NULL.
  - t2_09, t2_12, t2_15, t2_20, t3_01, t3_05 and t3_08 are neither guarded nor use `NULLS LAST`.

**NULL handling**
- `COALESCE` and `NULLIF` appear nowhere, so NULL is never converted to 0.
- `HAVING COUNT(preis_eur_mwh) > 0` drops all-NULL price zones in t2_06, t2_21 and t2_25. The other price-zone group-bys (t3_08, t3_09, t3_11) filter on a single zone and have no HAVING.

**Units**
- Energy columns are raw MWh and price columns are EUR/MWh. There is no GWh, TWh or MW conversion anywhere, and no ×4 for load. Load stays in MWh per quarter-hour.
- Column aliases carry the unit: `mwh`, `eur_mwh`, `*_mwh`, `*_prozent`, `n`, `stunden`, `viertelstunden`.
- Averages over time buckets are averages of the quarter-hour values. The hour-of-day items (t2_03, t2_08, t2_10) are not scaled to hourly MWh. t3_12's daily average is an average of daily sums.
- Durations in t4_02 and t4_04 are returned twice, as `viertelstunden` (COUNT) and `stunden` (COUNT / 4.0, rounded to 2).

**Formatting**
- No gold_sql applies `TO_CHAR`, thousands separators or currency formatting to numbers. Values are raw numeric, with `::int` casts on EXTRACT outputs and COUNT as bigint.

**Labels**
- Aliases for labels and buckets are German: `energietraeger`, `preiszone`, `monat`, `quartal`, `woche`, `tag`, `stunde`, `jahr`, `wochentag`, `kategorie`, `typ`, `gruppe`, `beginn`, `ende`.
- Value aliases are mixed. `mwh`, `eur_mwh` and `n` are the base names. Derived ones are `spitze_mwh` (t2_17), `min_eur_mwh` (t2_21), `spanne_mwh` (t3_05), and `mwh_2024`, `mwh_2025`, `differenz_mwh`, `erneuerbar_mwh`, `netzlast_mwh`, `tages_mwh`, `durchschnitt_mwh`, `ueberschuss_mwh`, `erzeugt`, `verbraucht`.
- CASE-generated label values are German: `Erneuerbar` / `Konventionell` (t2_15), `Wochenende` / `Werktag` (t3_08), `viel Solar` / `wenig Solar` (t3_11).
- Energy-source and price-zone values are returned as the raw DB literals.

**Filters**
- Every time range is half-open: `zeitpunkt >= 'start' AND zeitpunkt < 'next'`. `BETWEEN` appears nowhere. The only exact timestamp match is t1_22.
- "German price" always filters `preiszone = 'Deutschland/Luxemburg'`. The only unfiltered price-zone queries are t2_06 and t2_21 (all zones) and t2_25 (an explicit list of 11 neighbours).
- Grid-load questions use `metrik = 'grid load'` (t1_05, t1_18, t1_32, t2_08, t2_12, t3_05, t3_07, t4_03). Residual-load and pumped-storage items use their own `metrik` literals.

**Grouping syntax**
- 26 items use positional `GROUP BY 1` (some inside a CTE), mostly for expression groupings. Plain-column groupings use the column name (`GROUP BY energietraeger` or `preiszone`). The outer queries of t3_04 and t3_09 group by qualified names.
