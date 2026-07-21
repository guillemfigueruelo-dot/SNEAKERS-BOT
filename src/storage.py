import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts_sent (
    model TEXT NOT NULL,
    sent_at TEXT NOT NULL
);
"""


def _connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def was_recently_alerted(model, within_hours):
    conn = _connect()
    cutoff = (datetime.utcnow() - timedelta(hours=within_hours)).isoformat()
    row = conn.execute(
        "SELECT 1 FROM alerts_sent WHERE model = ? AND sent_at >= ? LIMIT 1",
        (model, cutoff),
    ).fetchone()
    conn.close()
    return row is not None


def mark_alerted(model):
    conn = _connect()
    conn.execute(
        "INSERT INTO alerts_sent (model, sent_at) VALUES (?, ?)",
        (model, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
