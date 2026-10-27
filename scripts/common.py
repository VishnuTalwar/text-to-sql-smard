"""Shared helpers for the SMARD loader scripts."""

import io
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def parse_german_number(series: pd.Series) -> pd.Series:
    """'1.542,63' -> 1542.63; '-84,15' -> -84.15; '-' -> NaN (missing, not zero)."""
    s = series.astype(str).str.strip()
    missing = s.eq("-")
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    numeric = pd.to_numeric(s, errors="coerce")
    numeric[missing] = pd.NA
    return numeric


def parse_us_number(series: pd.Series) -> pd.Series:
    """'11,053.00' -> 11053.00 (comma thousands separator, dot decimal point)."""
    s = series.astype(str).str.strip().str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def get_connection():
    load_dotenv(PROJECT_ROOT / ".env")
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "smard"),
        user=os.environ.get("POSTGRES_USER", "app"),
        password=os.environ.get("POSTGRES_PASSWORD", "app"),
    )


def load_to_postgres(df: pd.DataFrame, table_name: str, ddl: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)

            buffer = io.StringIO()
            df.to_csv(buffer, index=False, header=False, na_rep="")
            buffer.seek(0)
            columns = ", ".join(df.columns)
            cur.copy_expert(
                f"COPY {table_name} ({columns}) FROM STDIN WITH (FORMAT csv, NULL '')",
                buffer,
            )
        conn.commit()
    finally:
        conn.close()
