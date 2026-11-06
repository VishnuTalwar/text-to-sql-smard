"""
Runs SQL against the read-only grader_ro role (see sql/create_grader_role.sql,
open item O11, DECISIONS.md D8). Never the loader account — that account has
write/DDL rights and using it here would defeat the whole point of the
read-only sandbox.
"""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class QueryError(RuntimeError):
    """Raised whenever SQL fails to execute. Never swallowed into an empty result set —
    a broken query and a query that legitimately returns zero rows must stay distinguishable."""


def run_query(sql: str) -> list[tuple]:
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "smard"),
        user=os.environ["GRADER_DB_USER"],
        password=os.environ["GRADER_DB_PASSWORD"],
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    except Exception as exc:
        raise QueryError(str(exc)) from exc
    finally:
        conn.close()


def run_query_with_columns(sql: str) -> tuple[list[str], list[tuple]]:
    """Same execution path as run_query (role grader_ro, fresh connection, QueryError on any
    failure), but also returns the result column names. Used by the answer comparator (D42);
    run_query itself is unchanged."""
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "smard"),
        user=os.environ["GRADER_DB_USER"],
        password=os.environ["GRADER_DB_PASSWORD"],
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return cols, cur.fetchall()
    except Exception as exc:
        raise QueryError(str(exc)) from exc
    finally:
        conn.close()
