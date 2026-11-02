# Prediction for row R3 (R2 + date fact check: decline review and empty fact) on top of v2b, written before the run
- Base: v2b_fresh 60.00; R2 59.67. Model gpt-4o-2024-08-06 (D36).
- Decline review: fires on 0 to 1 questions per run (v2b_fresh and R2 had no false declines). Dry run: it would have fired on 0 of 111 correct tier-0 declines.
- u_01 to u_07 stay declined in 3 of 3 runs. Known gap: a correct decline that names a source and a period without "after/before" would be reviewed (none of 111 earlier replies is worded that way); watched via u_01.
- Empty fact: fires on u_08 in 3 of 3 runs. u_08 is declined after it in at least 1 of 3 runs (it was 0 of 3 in R2 without the fact).
- t4_03 unchanged (no date in its SQL, no fact; 0 of 3).
- Total within noise of 60.00 (roughly 58 to 63); expected gain 0 to +1, all of it from u_08. Tier 0 between 7 and 8.
- No new false declines on tiers 1-4 caused by the loop.
- The real test of the decline review is the next row (ex-a on top of R3); the dry run predicts it catches only 2 of ex-a's 35 false declines, because most name no period.
