# Final held-out run, 2026-11-15

Totals and counts only: no question text, no question ids, no SQL (D47).

- Commit: ab80ac6 (tag final-v1)
- Same day: yes
- Held-out items: 30 (tier 0: 3, tier 1: 10, tier 2: 10, tier 3: 5, tier 4: 2)

## Per-run totals (passed of 30)

| setup | run | strict | answer score |
|---|---:|---:|---:|
| r3b_safe | 1 | 20 | 21 |
| r3b_safe | 2 | 22 | 23 |
| r3b_safe | 3 | 20 | 20 |
| v2b | 1 | 20 | 20 |
| v2b | 2 | 18 | 19 |
| v2b | 3 | 20 | 20 |

## Mean over the runs (passed)

| setup | tier 0 (of 3) | tier 1 (of 10) | tier 2 (of 10) | tier 3 (of 5) | tier 4 (of 2) | total (of 30) |
|---|---:|---:|---:|---:|---:|---:|
| r3b_safe, strict | 3.00 | 10.00 | 6.00 | 1.33 | 0.33 | 20.67 |
| r3b_safe, answer score | 3.00 | 10.00 | 6.67 | 1.33 | 0.33 | 21.33 |
| v2b, strict | 2.00 | 10.00 | 5.67 | 1.67 | 0.00 | 19.33 |
| v2b, answer score | 2.00 | 10.00 | 6.00 | 1.67 | 0.00 | 19.67 |

## Failure types (strict failures, summed over the runs)

| setup | wrong shape | wrong values | SQL error | false decline | missed decline | blocked | other | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| r3b_safe | 8 | 17 | 0 | 3 | 0 | 0 | 0 | 28 |
| v2b | 6 | 20 | 3 | 0 | 3 | 0 | 0 | 32 |

## System decline fired (summed over the runs)

| setup | tier 0 | tier 1 | tier 2 | tier 3 | tier 4 |
|---|---:|---:|---:|---:|---:|
| r3b_safe | 3 | 0 | 0 | 0 | 0 |
| v2b | 0 | 0 | 0 | 0 | 0 |

## Blocked queries per wall (every attempt, summed over the runs)

| setup | wall 1 | wall 2 | wall 3 | total |
|---|---:|---:|---:|---:|
| r3b_safe | 0 | 0 | 0 | 0 |
| v2b | 0 | 0 | 0 | 0 |

## Cost, model, fingerprints

| setup | cost (USD, 3 runs) | model | system fingerprints |
|---|---:|---|---|
| r3b_safe | 0.2424 | gpt-4o-2024-08-06 | fp_7c2c459cd0, fp_e665f1271d |
| v2b | 0.2165 | gpt-4o-2024-08-06 | fp_4c910a9acf, fp_7c2c459cd0, fp_e665f1271d |

Total cost: $0.4588

## Prediction check

Predictions as approved in `results/final_heldout_prediction.md` (unchanged). Means are over the 3 runs; "strict" is the strict score, "answer" the answer score.

| # | Prediction | Result | Deciding number |
|---|---|---|---|
| 1 | r3b_safe's strict total is between 2 points below and 3 points above v2b's (same day) | confirmed | r3b_safe 20.67, v2b 19.33: difference +1.33 |
| 2 | For both setups the answer score is at least the strict score | confirmed | r3b_safe 21.33 vs 20.67, v2b 19.67 vs 19.33 (also true in every single run) |
| 3 | Tiers 3 and 4: r3b_safe passes at most half of those questions (strict) | confirmed | 1.67 of 7 on average (tier 3: 1.33 of 5, tier 4: 0.33 of 2) = 23.8% |
| 4 | The safe runner blocks 0 queries | confirmed | 0 blocked queries (walls 1, 2 and 3: 0, 0, 0) |
| 5 | The system decline fires only on tier 0, never on tiers 1 to 4 | confirmed | r3b_safe fired 3 times on tier 0 and 0 times on tiers 1 to 4 |
| 6 | Tier 0: r3b_safe is at least as good as v2b | confirmed | r3b_safe 3.00 of 3, v2b 2.00 of 3 |
| 7 | v2b's same-day result is within plus or minus 2 of its starting point (19.33) | confirmed | v2b strict 19.33: difference 0.00 |

All 7 predictions confirmed.
