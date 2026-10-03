"""SQLite storage layer for daily OHLCV data.

Schema is deliberately simple: one row per (ticker, date).
"""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path("data/market.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL,
    high   REAL,
    low    REAL,
    close  REAL,
    volume INTEGER,
    PRIMARY KEY (ticker, date)
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection and ensure the schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def insert_prices(conn: sqlite3.Connection, ticker: str, df: pd.DataFrame) -> int:
    """Insert OHLCV rows for one ticker. Skips duplicates.

    Returns the number of rows actually inserted.
    """
    if df.empty:
        return 0

    # Normalise the DataFrame into the shape our table expects.
    rows = df.reset_index()
    rows["ticker"] = ticker.upper()
    rows["date"] = pd.to_datetime(rows["Date"]).dt.strftime("%Y-%m-%d")

    payload = [
        (
            r["ticker"],
            r["date"],
            float(r["Open"]),
            float(r["High"]),
            float(r["Low"]),
            float(r["Close"]),
            int(r["Volume"]),
        )
        for _, r in rows.iterrows()
    ]

    # INSERT OR IGNORE uses the PRIMARY KEY (ticker, date) to skip duplicates.
    cursor = conn.executemany(
        "INSERT OR IGNORE INTO prices "
        "(ticker, date, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    conn.commit()
    return cursor.rowcount


def count_rows(conn: sqlite3.Connection, ticker: str | None = None) -> int:
    """Count rows in the prices table, optionally for one ticker."""
    if ticker:
        cur = conn.execute("SELECT COUNT(*) FROM prices WHERE ticker = ?", (ticker.upper(),))
    else:
        cur = conn.execute("SELECT COUNT(*) FROM prices")
    return cur.fetchone()[0]
