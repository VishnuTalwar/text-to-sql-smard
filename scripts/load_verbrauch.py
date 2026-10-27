"""
Loads the SMARD "Actual Consumption" CSV into Postgres, in long/tidy format:
one row per (zeitpunkt, metrik) pair.

Source quirks handled here:
  - This file was exported in ENGLISH locale, unlike erzeugung/preise:
      - Comma-delimited numbers use US convention already (comma thousands,
        dot decimal) — no digit-swapping needed, unlike the German files.
      - Dates look like 'Jun 1, 2023 12:00 AM' (month name, 12-hour clock).
  - UTF-8 BOM at the start of the file (encoding='utf-8-sig' strips it).
  - metrik labels are kept in English, exactly as the source column headers
    read, since this file itself has no German labels to preserve.
  - "End date" is dropped: every interval is a fixed 15 minutes, so it's
    always derivable from zeitpunkt (= "Start date") + 15 minutes.
"""

from common import RAW_DIR, load_to_postgres, parse_us_number
import pandas as pd

CSV_PATH = RAW_DIR / "Actual_consumption_202306010000_202606020000_Quarterhour.csv"

TABLE_NAME = "verbrauch"

DATE_COLUMN = "Start date"

# Source column -> metrik label (kept in English, matching this file's own headers)
METRIK_MAP = {
    "grid load [MWh] Original resolutions": "grid load",
    "Grid load incl. hydro pumped storage [MWh] Original resolutions": "Grid load incl. hydro pumped storage",
    "Hydro pumped storage [MWh] Original resolutions": "Hydro pumped storage",
    "Residual load [MWh] Original resolutions": "Residual load",
}

# zeitpunkt is NOT unique on its own: German local time repeats one wall-clock
# hour every October when clocks fall back, and each zeitpunkt has one row per
# metrik anyway — so a surrogate key is used instead of a natural one.
DDL = f"""
DROP TABLE IF EXISTS {TABLE_NAME};
CREATE TABLE {TABLE_NAME} (
    id        SERIAL PRIMARY KEY,
    zeitpunkt TIMESTAMP NOT NULL,
    metrik    TEXT NOT NULL,
    mwh       NUMERIC(12, 2)
);
CREATE INDEX idx_{TABLE_NAME}_zeitpunkt ON {TABLE_NAME} (zeitpunkt);
CREATE INDEX idx_{TABLE_NAME}_metrik ON {TABLE_NAME} (metrik);
"""


def load_dataframe() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8-sig")

    zeitpunkt = pd.to_datetime(df[DATE_COLUMN], format="%b %d, %Y %I:%M %p")

    source_columns = list(METRIK_MAP.keys())
    wide = df[source_columns].apply(parse_us_number)
    wide.insert(0, "zeitpunkt", zeitpunkt)

    long_df = wide.melt(id_vars="zeitpunkt", var_name="source_column", value_name="mwh")
    long_df["metrik"] = long_df["source_column"].map(METRIK_MAP)

    return long_df[["zeitpunkt", "metrik", "mwh"]].sort_values(["zeitpunkt", "metrik"])


def main() -> None:
    df = load_dataframe()
    print(f"Parsed {len(df):,} rows ({df['zeitpunkt'].nunique():,} timestamps x {df['metrik'].nunique()} metrik)")

    load_to_postgres(df, TABLE_NAME, DDL)
    print(f"Loaded into table '{TABLE_NAME}'.")


if __name__ == "__main__":
    main()
