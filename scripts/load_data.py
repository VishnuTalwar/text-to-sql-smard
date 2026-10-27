"""
Loads the SMARD "Realisierte Erzeugung" (actual generation) CSV into Postgres,
in long/tidy format: one row per (zeitpunkt, energietraeger) pair.

Source quirks handled here:
  - Semicolon-delimited, German locale.
  - UTF-8 BOM at the start of the file (encoding='utf-8-sig' strips it).
  - German number format: '.' = thousands separator, ',' = decimal point.
  - '-' means "no data" (NULL), not zero.
  - Dates are day-first (01.06.2023 = June 1st).
  - "Datum bis" is dropped: every interval is a fixed 15 minutes, so it's
    always derivable from zeitpunkt (= "Datum von") + 15 minutes.
"""

from common import RAW_DIR, load_to_postgres, parse_german_number
import pandas as pd

CSV_PATH = RAW_DIR / "Realisierte_Erzeugung_202306010000_202606020000_Viertelstunde.csv"

TABLE_NAME = "erzeugung"

DATE_COLUMN = "Datum von"

# Source column -> energietraeger label
ENERGIETRAEGER_MAP = {
    "Biomasse [MWh] Originalauflösungen": "Biomasse",
    "Wasserkraft [MWh] Originalauflösungen": "Wasserkraft",
    "Wind Offshore [MWh] Originalauflösungen": "Wind Offshore",
    "Wind Onshore [MWh] Originalauflösungen": "Wind Onshore",
    "Photovoltaik [MWh] Originalauflösungen": "Photovoltaik",
    "Sonstige Erneuerbare [MWh] Originalauflösungen": "Sonstige Erneuerbare",
    "Kernenergie [MWh] Originalauflösungen": "Kernenergie",
    "Braunkohle [MWh] Originalauflösungen": "Braunkohle",
    "Steinkohle [MWh] Originalauflösungen": "Steinkohle",
    "Erdgas [MWh] Originalauflösungen": "Erdgas",
    "Pumpspeicher [MWh] Originalauflösungen": "Pumpspeicher",
    "Sonstige Konventionelle [MWh] Originalauflösungen": "Sonstige Konventionelle",
}

# zeitpunkt is NOT unique on its own: German local time repeats one wall-clock
# hour every October when clocks fall back (e.g. 2023-10-29 02:00 occurs twice,
# once in CEST and once in CET), and each zeitpunkt has one row per
# energietraeger anyway — so a surrogate key is used instead of a natural one.
DDL = f"""
DROP TABLE IF EXISTS {TABLE_NAME};
CREATE TABLE {TABLE_NAME} (
    id             SERIAL PRIMARY KEY,
    zeitpunkt      TIMESTAMP NOT NULL,
    energietraeger TEXT NOT NULL,
    mwh            NUMERIC(12, 2)
);
CREATE INDEX idx_{TABLE_NAME}_zeitpunkt ON {TABLE_NAME} (zeitpunkt);
CREATE INDEX idx_{TABLE_NAME}_energietraeger ON {TABLE_NAME} (energietraeger);
"""


def load_dataframe() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8-sig")

    zeitpunkt = pd.to_datetime(df[DATE_COLUMN], format="%d.%m.%Y %H:%M")

    source_columns = list(ENERGIETRAEGER_MAP.keys())
    wide = df[source_columns].apply(parse_german_number)
    wide.insert(0, "zeitpunkt", zeitpunkt)

    long_df = wide.melt(id_vars="zeitpunkt", var_name="source_column", value_name="mwh")
    long_df["energietraeger"] = long_df["source_column"].map(ENERGIETRAEGER_MAP)

    return long_df[["zeitpunkt", "energietraeger", "mwh"]].sort_values(["zeitpunkt", "energietraeger"])


def main() -> None:
    df = load_dataframe()
    print(f"Parsed {len(df):,} rows ({df['zeitpunkt'].nunique():,} timestamps x {df['energietraeger'].nunique()} energietraeger)")
    kernenergie_null = df.loc[df["energietraeger"] == "Kernenergie", "mwh"].isna().sum()
    print(f"NULL Kernenergie rows: {kernenergie_null:,}")

    load_to_postgres(df, TABLE_NAME, DDL)
    print(f"Loaded into table '{TABLE_NAME}'.")


if __name__ == "__main__":
    main()
