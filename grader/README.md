# grader/

## How to run

Every ablation row is run with the shared runner `run.py` and one config file from `configs/`:

```
cd grader
python run.py --config configs/<row>.yaml [--runs N] [--gold-file PATH]
```

- `--config`: one of `configs/*.yaml` (`naive`, `schema_linked`, `decline`, `v2a`, `v2b`, `v2b2`, `v2c`, `ex-a`, `ex-b`, `df`, `r1`, `r2`, `r3`, `r3b`). A config holds only what differs between rows: prompt (by name), example block (`none` / `ex-a` / `ex-b`), loop switches (`error_retry`, `empty_retry`, `decline_review`, `empty_fact_decline`), `max_attempts`, model, temperature, seed, number of runs and the output tag. All keys are required.
- `--runs N`: number of full runs (default: `runs` in the config). Each run calls the API 84 times or more.
- `--gold-file PATH`: use another gold YAML instead of `gold_set_smard.yaml`; its name goes into the file names.

Outputs, for each run `n`, in `results/` (existing naming, `<date>` is the day of the run):

| File | Content |
|---|---|
| `<tag>_run{n}_<date>.log` | the summary: scores per tier, loop numbers, latency, tokens, cost, per-question outcome, failures |
| `<tag>_run{n}_<date>.jsonl` | one record per question (the fields of `run_r3b.py`, including every attempt) |
| `<tag>_run{n}_<date>.manifest.json` | the run receipt: config file name and full content, SHA-256 of the exact prompt of each question and one combined hash, SHA-256 of the gold file, git commit and whether tracked files were unmodified (untracked files are listed), model, temperature, seed, max_attempts, switches, start and end time, versions of openai, psycopg2 and sqlglot |

Rows that run the same prompt as an older row differ only in their config, so the manifest shows exactly what changed between two result files. Only the model call needs the API key (`.env`); the tests in `tests/` use a fake model.

The older `run_*.py` files (`run_baseline.py`, `run_v2b.py`, `run_r3b.py`, ...) and the prompt templates they use are kept only to reproduce earlier results; do not add new rows as new runner files, add a config. `tests/test_run_equivalence.py` shows that `run.py` sends the same prompts and writes the same records as the old runners.

Note on old rows: their original results (before 2 Nov 2026) were produced with the model alias `gpt-4o`; all configs pin `gpt-4o-2024-08-06` (D36), so a new run of an old row is comparable with R1 to R3b but not byte for byte with the old logs.

Run the offline tests (no API) from this folder: `python -m unittest discover -s tests -v`.
