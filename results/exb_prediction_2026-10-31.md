Prediction for row ex-b, written before running.
- Shape failures (wrong column count, wrong row count, SQL errors) drop
  compared with v2b, as in ex-a.
- Wrong declines: if ex-a's declines came from examples that did not resemble
  the question, ex-b cuts them sharply. If they stay high, the cause is the
  presence of an example block itself.
- Copying: month questions may still copy ex_20 (month of year as an integer).
- Tier 1 and tier 0 roughly unchanged.
- Differences under about 2-3 points are noise.
