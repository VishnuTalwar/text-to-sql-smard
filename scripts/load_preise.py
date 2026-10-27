"""
Loads the SMARD "Großhandelspreise" (wholesale prices) CSV into Postgres, in
long/tidy format: one row per (zeitpunkt, preiszone) pair.

Source quirks handled here:
  - Semicolon-delimited, German locale.
  - UTF-8 BOM at the start of the file (encoding='utf-8-sig' strips it).
  - German number format: '.' = thousands separator, ',' = decimal point.
  - '-' means "no data" (NULL), not zero — e.g. DE/AT/LU (a combined bidding
    zone dissolved in Oct 2018, before this dataset starts) is NULL throughout.
  - Prices can be negative (oversupply), which parse_german_number handles
    fine since only the literal '-' string (not a leading minus sign) is
    treated as missing.
  - Dates are day-first (01.06.2023 = June 1st).
  - Columns are price *zones*, not strictly countries (e.g. '∅ Anrainer
    DE/LU' is an average of neighbors, 'DE/AT/LU' is a historical combined
    bidding zone) — the category column is named preiszone, not land.
  - "Datum bis" is dropped: every interval is a fixed 15 minutes, so it's
    always derivable from zeitpunkt (= "Datum von") + 15 minutes.
"""

from common import RAW_DIR, load_to_postgres, parse_german_number
import pandas as pd

CSV_PATH = RAW_DIR / "Gro_handelspreise_202306010000_202606020000_Viertelstunde.csv"

TABLE_NAME = "preise"

DATE_COLUMN = "Datum von"

# Source column -> preiszone label
PREISZONE_MAP = {
    "Deutschland/Luxemburg [€/MWh] Originalauflösungen": "Deutschland/Luxemburg",
    "∅ Anrainer DE/LU [€/MWh] Originalauflösungen": "∅ Anrainer DE/LU",
    "Belgien [€/MWh] Originalauflösungen": "Belgien",
    "Dänemark 1 [€/MWh] Originalauflösungen": "Dänemark 1",
    "Dänemark 2 [€/MWh] Originalauflösungen": "Dänemark 2",
    "Frankreich [€/MWh] Originalauflösungen": "Frankreich",
    "Niederlande [€/MWh] Originalauflösungen": "Niederlande",
    "Norwegen 2 [€/MWh] Originalauflösungen": "Norwegen 2",
    "Österreich [€/MWh] Originalauflösungen": "Österreich",
    "Polen [€/MWh] Originalauflösungen": "Polen",
    "Schweden 4 [€/MWh] Originalauflösungen": "Schweden 4",
    "Schweiz [€/MWh] Originalauflösungen": "Schweiz",
    "Tschechien [€/MWh] Originalauflösungen": "Tschechien",
    "DE/AT/LU [€/MWh] Originalauflösungen": "DE/AT/LU",
    "Italien (Nord) [€/MWh] Originalauflösungen": "Italien (Nord)",
    "Slowenien [€/MWh] Originalauflösungen": "Slowenien",
    "Ungarn [€/MWh] Originalauflösungen": "Ungarn",
}

# zeitpunkt is NOT unique on its own: German local time repeats one wall-clock
# hour every October when clocks fall back, and each zeitpunkt has one row per
# preiszone anyway — so a surrogate key is used instead of a natural one.
DDL = f"""
DROP TABLE IF EXISTS {TABLE_NAME};
CREATE TABLE {TABLE_NAME} (
    id            SERIAL PRIMARY KEY,
    zeitpunkt     TIMESTAMP NOT NULL,
    preiszone     TEXT NOT NULL,
    preis_eur_mwh NUMERIC(12, 2)
);
CREATE INDEX idx_{TABLE_NAME}_zeitpunkt ON {TABLE_NAME} (zeitpunkt);
CREATE INDEX idx_{TABLE_NAME}_preiszone ON {TABLE_NAME} (preiszone);
"""


def load_dataframe() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8-sig")

    zeitpunkt = pd.to_datetime(df[DATE_COLUMN], format="%d.%m.%Y %H:%M")

    source_columns = list(PREISZONE_MAP.keys())
    wide = df[source_columns].apply(parse_german_number)
    wide.insert(0, "zeitpunkt", zeitpunkt)

    long_df = wide.melt(id_vars="zeitpunkt", var_name="source_column", value_name="preis_eur_mwh")
    long_df["preiszone"] = long_df["source_column"].map(PREISZONE_MAP)

    return long_df[["zeitpunkt", "preiszone", "preis_eur_mwh"]].sort_values(["zeitpunkt", "preiszone"])


def main() -> None:
    df = load_dataframe()
    print(f"Parsed {len(df):,} rows ({df['zeitpunkt'].nunique():,} timestamps x {df['preiszone'].nunique()} preiszone)")
    de_at_lu_null = df.loc[df["preiszone"] == "DE/AT/LU", "preis_eur_mwh"].isna().sum()
    print(f"NULL DE/AT/LU rows: {de_at_lu_null:,}")

    load_to_postgres(df, TABLE_NAME, DDL)
    print(f"Loaded into table '{TABLE_NAME}'.")


if __name__ == "__main__":
    main()
