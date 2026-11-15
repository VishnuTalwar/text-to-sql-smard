# Prediction for the final held-out run (D47)

**DRAFT, to be approved by Vishnu before the run**

Written 15 Nov 2026, before any API call on the held-out set. r3b_safe is the final setup, v2b is the base; both run 3 times on the same day.

1. On the held-out set, r3b_safe's strict total is between 2 points below and 3 points above v2b's (same day).
2. For both setups the answer score is at least the strict score.
3. Tiers 3 and 4 stay weak: r3b_safe passes at most half of those questions under the strict score.
4. The safe runner blocks 0 queries.
5. The system decline fires only on tier 0, never on tiers 1 to 4.
6. Tier 0: r3b_safe is at least as good as v2b.
7. v2b's same-day result is within plus or minus 2 of its starting point (19.33).
