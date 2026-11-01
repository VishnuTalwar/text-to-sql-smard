# Prediction for row R1 (error retry on top of v2b), written before the run
- Attempt 1 is identical to v2b, so only questions whose SQL crashes can change.
- v2b had 5 crashes over 3 runs, so the highest possible gain is about 1.7 points per run (5/3). The total score is expected within noise of 60.67 (roughly 59 to 63). The earlier estimate of +2 to +4 (section 13) was too high.
- The clean measure is "crashed on attempt 1, fixed by retry": expected at least half of the crashes to be fixed, especially wrong column names and GROUP BY errors.
- Questions whose SQL runs but has the wrong logic (t4_02, t4_04) do not change.
- declined_after_error: expected 0 or close to 0.
- Tier 0 unchanged at 7/8 (NO_QUERY on attempt 1 stops the loop).
- Retry rate expected low (under 10% of questions); mean attempts close to 1.0.

## Note added when N was filled in (facts from v2b, not predictions)
- The 5 crashes are t4_02 (runs 1 and 3) and t4_04 (runs 1, 2 and 3), per run 2, 1 and 2. All five are `column "..." does not exist` (invented column names such as zero_stretch, consecutive_count, consecutive_intervals). There are no GROUP BY errors and no timeouts.
- Tier 4 scored 0/4 in all three v2b runs.
- So bullets 3 and 4 refer to the same questions: if "fixed" means the SQL runs on a later attempt, bullet 3 can hold while bullet 4 (no change in the score) also holds; if "fixed" means pass after retry (the definition printed by `run_r1.py`), the two cannot both hold. The run report prints both numbers ("SQL runs without error at the end" and "pass after retry"), and the analysis will say which one each bullet was judged on.
