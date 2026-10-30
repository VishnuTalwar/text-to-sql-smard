# Held-out starting-point runs

- `v2b_heldout_smard_heldout_run{1,2,3}_2026-10-30.log` and `.jsonl`: first starting-point run on the held-out set. It ran on the **first freeze (commit 36b45cf)**, with the old h2_01 and hu_03. It is **superseded**. The files are kept, not deleted, and should not be used for comparisons.
- `v2b_heldout_smard_heldout_v2_run{1,2,3}_2026-10-30.log` and `.jsonl`: starting-point run on the re-frozen file (commit 627ee4f, SHA-256 `26ffe76d93f419e4d77a230d54fe8df5d60c464854940d03db0ee01345a80713`). This is the current baseline.

See D29 in DECISIONS.md. Only per-tier totals of these runs are looked at, never per-question results.
