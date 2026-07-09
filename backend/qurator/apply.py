"""Apply-and-Measure — the closed loop.

Given a chosen index set, actually `CREATE INDEX` on the live database, run the workload, and measure real
wall-clock latency. This is what turns Qurator from "a chart" into "a measured system effect" on stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg
from rich.console import Console

from .candidates import by_id
from .db import connect, measure_latency_ms
from .workload import WORKLOAD

console = Console()


@dataclass
class LatencyResult:
    label: str
    per_query_ms: dict[str, float]
    total_ms: float               # unweighted sum — the headline "these queries take X"
    weighted_ms: float            # Σ weightᵩ · latencyᵩ — matches the optimization objective
    applied: list[str] = field(default_factory=list)
    build_ms: float = 0.0


def drop_qurator_indexes(cur: psycopg.Cursor) -> None:
    cur.execute(
        "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'qur_%'"
    )
    for (name,) in cur.fetchall():
        cur.execute(f"DROP INDEX IF EXISTS {name}")


def apply_indexes(cur: psycopg.Cursor, selected_ids: list[str]) -> float:
    """Build the selected indexes for real. Returns total build time in ms."""
    import time

    cmap = by_id()
    t0 = time.perf_counter()
    for cid in selected_ids:
        cur.execute(cmap[cid].create_sql(hypothetical=False))
    cur.execute("ANALYZE transactions, ledger_entries, accounts, merchants")
    return (time.perf_counter() - t0) * 1000.0


def measure_workload(cur: psycopg.Cursor, label: str, runs: int = 3) -> LatencyResult:
    per_query: dict[str, float] = {}
    total = 0.0
    weighted = 0.0
    for q in WORKLOAD:
        ms = measure_latency_ms(cur, q.sql, runs=runs)
        per_query[q.id] = ms
        total += ms
        weighted += q.weight * ms
    return LatencyResult(label=label, per_query_ms=per_query, total_ms=total, weighted_ms=weighted)


def benchmark_config(
    selected_ids: list[str], label: str, runs: int = 3, cleanup: bool = True
) -> LatencyResult:
    """Drop all Qurator indexes, apply `selected_ids`, warm caches, and measure.

    `cleanup=True` (default) drops the built indexes again afterwards so a benchmark never pollutes a later
    Cost Probe's baseline. For the live demo — where we WANT the chosen indexes to stay on the DB — pass
    `cleanup=False`.
    """
    with connect() as conn, conn.cursor() as cur:
        drop_qurator_indexes(cur)
        build_ms = apply_indexes(cur, selected_ids) if selected_ids else 0.0
        measure_workload(cur, label, runs=1)          # warm the cache first
        result = measure_workload(cur, label, runs=runs)
        result.applied = list(selected_ids)
        result.build_ms = build_ms
        if cleanup:
            drop_qurator_indexes(cur)
        return result
