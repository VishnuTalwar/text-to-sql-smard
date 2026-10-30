# Structure of gold_set_smard.yaml and how the grader reads it (2026-10-29)

Read-only inspection. No question text, SQL or reference answers are reproduced here, only structure. Sources: `gold_set_smard.yaml`, `grader/loader.py`, `grader/comparator.py`, `grader/run_grader.py` and the `grader/run_*.py` runners.

## 1. gold_set_smard.yaml

### Top level
A dict with exactly two keys. It is not a plain list.

| Key | Type | Content |
|---|---|---|
| `standard` | dict | Defaults block, two keys: `reihenfolge_relevant` (bool) and `toleranz` (float) |
| `fragen` | list | The 84 items |

There is no version or other metadata key. The header comment block above `standard:` (lines 1-92) is YAML comments only.

### Keys used by items (84 items)

"Required by loader" means the loader indexes it with `item[...]` and raises `KeyError` if it is missing. "Optional" means `item.get(...)`. See section 2.

| Key | Items with it | Value type | Required by loader? |
|---|---|---|---|
| `id` | 84 | string | required |
| `tier` | 84 | int | required |
| `frage` | 84 | string | required |
| `gold_sql` | 84 | string (76 items) or null (8 items) | optional (`.get`); null means tier 0 |
| `reihenfolge_relevant` | 76 | bool | optional, falls back to `standard.reihenfolge_relevant` |
| `toleranz` | 76 | float | optional, falls back to `standard.toleranz` |
| `gold_zeilen` | 76 | int | optional |
| `gold_antwort` | 76 | string | optional |
| `hinweis` | 39 | string | optional |
| `fragil` | 2 | bool | optional, default False |
| `fragil_grund` | 2 | string | optional |
| `beantwortbar` | 8 | bool | optional, default True |
| `erwartetes_verhalten` | 8 | string | optional |
| `beleg_sql` | 5 | string | optional |
| `beleg_ergebnis` | 5 | string | optional |

No key holds a list or dict value inside an item.

Which items carry the optional keys:
- `hinweis`: 39 items, all tiers 1-4 (14 T1, 13 T2, 8 T3, 4 T4). No tier-0 item has it.
- `fragil` and `fragil_grund`: t1_30 and t4_02.
- `beleg_sql` and `beleg_ergebnis`: u_01, u_02, u_03, u_07 and u_08.

Two observations:
- Only `id`, `tier` and `frage` are required by the loader.
- The other 11 item keys are optional, not just the extra tier-0 ones.

### Id format
- Tiers 1-4: `t<tier>_<NN>`, zero-padded to two digits, numbered 1..n within each tier.

  | Tier | Count | Range |
  |---|---|---|
  | 1 | 35 | t1_01 .. t1_35 |
  | 2 | 25 | t2_01 .. t2_25 |
  | 3 | 12 | t3_01 .. t3_12 |
  | 4 | 4 | t4_01 .. t4_04 |

- Tier 0: `u_<NN>`, `u_01` .. `u_08`. The prefix is `u`, not `t0`.
- Both patterns are plain strings. The loader does not parse or validate the prefix.

### Tier storage
- Key `tier`, YAML int (0, 1, 2, 3, 4), in all 84 items.
- The `tier` value is not derived from the id prefix. The loader reads it directly into `Question.tier: int`.

### Tier 0 items (u_01 .. u_08)

| Aspect | Observed |
|---|---|
| `gold_sql` | present as an explicit null (`gold_sql:` with no value). Not absent, not an empty string. |
| Keys present in all 8 | `id`, `tier`, `frage`, `gold_sql`, `beantwortbar` (False), `erwartetes_verhalten` |
| Extra keys in 5 of 8 | `beleg_sql`, `beleg_ergebnis` (u_01, u_02, u_03, u_07, u_08) |
| Keys lacking | `reihenfolge_relevant`, `toleranz`, `gold_zeilen`, `gold_antwort`, `hinweis` |

How the grader identifies tier 0:
- `Question.is_tier0` is `gold_sql is None` (`loader.py:44-47`, the `is_tier0` property). The tier number is not used.
- Consequence: a tier 1-4 item that lost its `gold_sql` would be graded as an "unanswerable" item, and a tier-0 item given a `gold_sql` would be graded as a normal item.
- `beantwortbar` is stored but not read anywhere outside the loader.

### toleranz
- Exact key name: `toleranz`. A float, in the per-item block and in `standard`.
- Values in use:
  - `1.0e-06` on 70 of the 76 tier 1-4 items, as written explicitly on each item.
  - `0.001` on six items: t2_07, t3_02, t3_06, t3_07, t3_10 and t3_12.
  - Absent on the 8 tier-0 items.
- It is relative, with a floor of 1 on the divisor. The check is in `comparator.py:120`:
  `abs(agent - gold) <= toleranz * max(abs(gold), 1)`.
  - Effectively relative when |gold| is 1 or larger, and absolute (`toleranz` itself) when |gold| < 1.
  - It applies only to numeric cells, meaning cells where the gold value is int, float or Decimal.
  - Dates and timestamps are compared exactly. Text is compared exactly with no case-folding or trimming.
  - A NULL matches only a NULL.
- Defaults when missing, in order:
  1. `standard.toleranz` in the YAML (1.0e-06).
  2. `DEFAULT_TOLERANZ = 0.005` in `loader.py:23`, used only if `standard` also lacks the key.
- The 0.005 fallback does not fire on the current file, because every item carries its own value and `standard` defines one.
- The loader docstring (lines 1-11) and the code comment at line 23 both say the per-item value always wins.

## 2. grader/loader.py and grader/run_grader.py

### loader.py
- Entry point: `load_questions(path: Path = GOLD_SET_PATH)` (`loader.py:50`). The default is `PROJECT_ROOT / "gold_set_smard.yaml"` (`loader.py:19-20`).
- Top-level keys read:
  - `data["fragen"]` is a hard index. A missing key raises `KeyError`.
  - `data.get("standard", {})` is optional. Within it, `reihenfolge_relevant` falls back to `False` and `toleranz` to `0.005`.
- Item keys read (`loader.py:62-76`):
  - **Hard index, `KeyError` if missing:** `id`, `tier`, `frage`.
  - **`.get` with a default:**
    - `gold_sql`: default None.
    - `gold_zeilen`: default None.
    - `reihenfolge_relevant`: default `standard`.
    - `toleranz`: default `standard`.
    - `gold_antwort`: default None.
    - `hinweis`: default None.
    - `fragil`: default False.
    - `fragil_grund`: default None.
    - `beantwortbar`: default True.
    - `erwartetes_verhalten`: default None.
    - `beleg_sql`: default None.
    - `beleg_ergebnis`: default None.
- Unknown extra keys on an item are silently ignored. The loader builds the dataclass by explicit field, so a typo in a key name is also silently ignored (that field just takes its default).
- There is no type validation. The loader does not check that `tier` is an int, that ids are unique, or that `gold_sql` is a string.

### Is `gold_zeilen` or `gold_antwort` required?
No. Both use `.get` in the loader. Nothing in `grader/` other than `loader.py` reads either field, as the grep over all `grader/*.py` files shows.
- `gold_zeilen` is documentation and a "quick shape check" per the YAML header, but the comparator compares actual row counts from running `gold_sql`.
- `gold_antwort` is described in the YAML header as documentation. The grader always executes `gold_sql`.
- The same holds for `hinweis`, `fragil`, `fragil_grund`, `beantwortbar`, `erwartetes_verhalten`, `beleg_sql` and `beleg_ergebnis`. They are loaded into `Question` but not used by the comparator, `run_grader.py` or the runners.

### What the comparator and runners use from Question
- `comparator.compare` (`comparator.py:29-85`): `is_tier0` (hence `gold_sql`), `gold_sql`, `reihenfolge_relevant`, `toleranz`, `id`, `tier`.
- Runners: `frage` (as input to the agent and the retriever), `id`, `tier`, `gold_sql` (retrieval check in `_retrieval_missing`), and `frage` again in `result_logging.py:75`.
- Required in practice for a new or changed YAML:
  - `id`, `tier` and `frage` on every item.
  - `gold_sql` on tier 1-4 items. A missing `gold_sql` on a non-tier-0 item makes it tier 0.
  - `reihenfolge_relevant` and `toleranz`, only if `standard` is also dropped, otherwise they inherit.

### Can the YAML path be changed from the command line?
No, the path is not exposed as a flag or environment variable.
- The only place it is set is `loader.py:20`: `GOLD_SET_PATH = PROJECT_ROOT / "gold_set_smard.yaml"`.
- `load_questions` accepts a `path` argument (`loader.py:50`), but no caller passes one. Every call is the bare `load_questions()`:
  - `run_grader.py:31`
  - `run_baseline.py:55`
  - `run_schema_linked.py:102`
  - `run_schema_linked_decline.py:101`
  - `run_v2a.py:103`
  - `run_v2b.py:97`
  - `run_v2b2.py:102`
  - `run_v2c.py:96`
- CLI flags that exist:
  - `run_grader.py`: `--self-test` only.
  - All other runners (`run_baseline`, `run_schema_linked`, `run_schema_linked_decline`, `run_v2a`, `run_v2b`, `run_v2b2`, `run_v2c`): `--runs` (int, default 1) and `--tag` (string).
- Environment variables read in `grader/` are for the database (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `GRADER_DB_USER`, `GRADER_DB_PASSWORD`), `OPENAI_API_KEY`, and `RUN_TAG` in four runners. None of them selects a YAML file.
- Pointing a runner at a different YAML therefore needs a code change, either editing `GOLD_SET_PATH` at `loader.py:20` or passing `path=` at the runner's `load_questions()` call.

## 3. Skeleton of one item (every key present)

No single item has all 15 keys. This is the union across all 84 items, in the order the keys are written in the file.

```yaml
- id: <string>
  tier: <int>
  frage: <string>
  reihenfolge_relevant: <bool>
  toleranz: <float>
  gold_zeilen: <int>
  gold_sql: <string | null>
  gold_antwort: <string>
  hinweis: <string>
  fragil: <bool>
  fragil_grund: <string>
  beantwortbar: <bool>
  erwartetes_verhalten: <string>
  beleg_sql: <string>
  beleg_ergebnis: <string>
```

Typical shapes in the file:
- **Tier 1-4:** `id, tier, frage, reihenfolge_relevant, toleranz, gold_zeilen, gold_sql, gold_antwort`, optionally `hinweis`, and for t1_30 and t4_02 also `fragil` and `fragil_grund`.
- **Tier 0:** `id, tier, frage, beantwortbar, erwartetes_verhalten, gold_sql` (null), and for five items `beleg_sql, beleg_ergebnis`.
