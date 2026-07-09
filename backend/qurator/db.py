"""Postgres access layer + EXPLAIN / HypoPG helpers.

Two cost signals matter:
  * estimated cost   — from `EXPLAIN (FORMAT JSON)` top-node "Total Cost" (planner units). Cheap; used with
                       HypoPG hypothetical indexes to score candidates WITHOUT building anything.
  * real latency     — from actually running the query (or `EXPLAIN ANALYZE`). Slow; used only for the
                       before/after demo reveal.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator

import psycopg

from .config import settings


@contextlib.contextmanager
def connect() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(settings.dsn, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def explain_cost(cur: psycopg.Cursor, sql: str) -> float:
    """Planner's estimated total cost for `sql` (reflects any active HypoPG hypothetical indexes)."""
    cur.execute(f"EXPLAIN (FORMAT JSON) {sql}")
    plan = cur.fetchone()[0]
    return float(plan[0]["Plan"]["Total Cost"])


def measure_latency_ms(cur: psycopg.Cursor, sql: str, runs: int = 3) -> float:
    """Median wall-clock execution time of `sql` in milliseconds (runs it for real)."""
    import statistics
    import time

    samples: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        cur.execute(sql)
        cur.fetchall()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


# ---- HypoPG hypothetical-index helpers -------------------------------------------------

def hypo_reset(cur: psycopg.Cursor) -> None:
    cur.execute("SELECT hypopg_reset()")


def hypo_create(cur: psycopg.Cursor, create_sql: str) -> tuple[int, str]:
    """Register a hypothetical index. Returns (indexrelid, indexname)."""
    cur.execute("SELECT indexrelid, indexname FROM hypopg_create_index(%s)", (create_sql,))
    row = cur.fetchone()
    return int(row[0]), row[1]


def hypo_size_bytes(cur: psycopg.Cursor, indexrelid: int) -> int:
    """Estimated on-disk size (bytes) of a hypothetical index."""
    cur.execute("SELECT hypopg_relation_size(%s)", (indexrelid,))
    return int(cur.fetchone()[0])
