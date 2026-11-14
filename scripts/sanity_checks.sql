-- Sanity checks for the erzeugung load (long format: zeitpunkt, energietraeger, mwh).
-- Run with (from the scripts folder): docker exec -i text-to-sql-db psql -U app -d smard < sanity_checks.sql
-- (or paste sections into psql interactively)

-- 1. Row count — should be 1,263,744 (105,312 source rows x 12 energietraeger).
SELECT count(*) AS total_rows FROM erzeugung;

-- 2. Column names clean (no BOM ghost character on the first column).
SELECT column_name FROM information_schema.columns
WHERE table_name = 'erzeugung' ORDER BY ordinal_position;

-- 3. All 12 energietraeger present, one row per timestamp each.
SELECT energietraeger, count(*) AS n
FROM erzeugung
GROUP BY energietraeger
ORDER BY energietraeger;

-- 4. Date range and day-first parsing sanity.
--    Earliest should be 2023-06-01, not misparsed as Jan 6.
SELECT min(zeitpunkt) AS earliest, max(zeitpunkt) AS latest FROM erzeugung;

-- 5. German number parsing — spot check a known value.
--    Raw CSV's first Biomasse value is "1.026,00" -> should read as 1026.00, not 1.026 or 102600.
SELECT zeitpunkt, energietraeger, mwh
FROM erzeugung
WHERE energietraeger = 'Biomasse'
ORDER BY zeitpunkt LIMIT 1;

-- 6. NULL vs zero for Kernenergie — both should exist, and NOT be conflated.
--    Zero = measured and empty; NULL = no data reported (after the shutdown-adjacent cutoff).
SELECT
    count(*) FILTER (WHERE mwh = 0)         AS zero_rows,
    count(*) FILTER (WHERE mwh IS NULL)     AS null_rows,
    count(*) FILTER (WHERE mwh IS NOT NULL) AS non_null_rows
FROM erzeugung
WHERE energietraeger = 'Kernenergie';

-- 7. DST fall-back duplicate (Oct 29, 2023 02:00–02:15 occurs twice in local time,
--    so each energietraeger should appear twice at that zeitpunkt).
--    Expect count = 2 per energietraeger, 24 rows total (12 energietraeger x 2).
SELECT energietraeger, count(*)
FROM erzeugung
WHERE zeitpunkt = '2023-10-29 02:00:00'
GROUP BY energietraeger
ORDER BY energietraeger;

-- 8. DST spring-forward gap (last Sunday in March, e.g. 2024-03-31 02:00–03:00 doesn't exist).
--    Expect 0 rows for the skipped hour.
SELECT zeitpunkt
FROM erzeugung
WHERE zeitpunkt BETWEEN '2024-03-31 02:00:00' AND '2024-03-31 02:45:00';

-- 9. No (zeitpunkt, energietraeger) pair appears more than twice
--    (twice only being valid for the known DST fall-back hours).
SELECT zeitpunkt, energietraeger, count(*) AS n
FROM erzeugung
GROUP BY zeitpunkt, energietraeger
HAVING count(*) > 2;
