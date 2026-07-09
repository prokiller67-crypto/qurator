"""Deterministic data seeder.

Two-pass streaming COPY (transactions, then ledger_entries) using an identical per-pass RNG sequence so a
transaction and its ledger entry stay consistent without holding millions of rows in memory. Reproducible:
same QURATOR_SEED_RNG -> byte-identical dataset -> stable EXPLAIN costs and demo latencies.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import psycopg
from rich.console import Console

from .config import settings
from .db import connect

console = Console()

WINDOW_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 7, 1, tzinfo=timezone.utc)
WINDOW_SECONDS = int((WINDOW_END - WINDOW_START).total_seconds())

COUNTRIES = ["US", "GB", "DE", "FR", "NG", "IN", "BR", "CN", "AE", "SG"]
CURRENCIES = ["USD", "EUR", "GBP"]
CATEGORIES = ["grocery", "restaurant", "travel", "crypto", "gambling", "electronics", "utilities", "healthcare"]
ACCOUNT_STATUS = ["active", "active", "active", "active", "frozen", "closed"]

# Weighted picks via cumulative thresholds (deterministic from the row RNG).
_STATUS = [("settled", 0.80), ("pending", 0.10), ("declined", 0.07), ("reversed", 0.03)]
_CHANNEL = [("pos", 0.45), ("ecom", 0.25), ("card_not_present", 0.15), ("atm", 0.10), ("wire", 0.05)]

# Bias a "hot" account so its per-account queries return realistic row counts in the demo.
HOT_ACCOUNT = 7777
HOT_FRACTION = 0.005


def _weighted(r: float, table: list[tuple[str, float]]) -> str:
    acc = 0.0
    for value, w in table:
        acc += w
        if r <= acc:
            return value
    return table[-1][0]


def _txn_row(rng: random.Random, txn_id: int, n_accounts: int, n_merchants: int) -> tuple:
    """One transaction row. The draw sequence here MUST be identical across both COPY passes."""
    if rng.random() < HOT_FRACTION:
        account_id = HOT_ACCOUNT
    else:
        account_id = rng.randint(1, n_accounts)
    merchant_id = rng.randint(1, n_merchants)
    ts = WINDOW_START + timedelta(seconds=rng.randint(0, WINDOW_SECONDS))
    amount = round(min(rng.lognormvariate(3.4, 1.25), 250_000), 2)
    currency = CURRENCIES[int(rng.random() * len(CURRENCIES))]
    status = _weighted(rng.random(), _STATUS)
    channel = _weighted(rng.random(), _CHANNEL)
    is_flagged = rng.random() < 0.02
    return (txn_id, account_id, merchant_id, amount, currency, ts, status, channel, is_flagged)


def _seed_accounts(cur: psycopg.Cursor, n: int, seed: int) -> None:
    rng = random.Random(seed + 1)
    with cur.copy(
        "COPY accounts (account_id, customer_name, country, kyc_level, status, created_at) FROM STDIN"
    ) as cp:
        for i in range(1, n + 1):
            country = COUNTRIES[int(rng.random() * len(COUNTRIES))]
            created = WINDOW_START - timedelta(days=rng.randint(0, 730))
            cp.write_row((i, f"Account {i}", country, rng.randint(0, 3),
                          ACCOUNT_STATUS[int(rng.random() * len(ACCOUNT_STATUS))], created))


def _seed_merchants(cur: psycopg.Cursor, n: int, seed: int) -> None:
    rng = random.Random(seed + 2)
    with cur.copy("COPY merchants (merchant_id, name, category, country, risk_score) FROM STDIN") as cp:
        for i in range(1, n + 1):
            category = CATEGORIES[int(rng.random() * len(CATEGORIES))]
            # crypto/gambling skew riskier — gives the risk_score filter real signal.
            base = 55 if category in ("crypto", "gambling") else 20
            risk = max(0, min(100, int(rng.gauss(base, 18))))
            country = COUNTRIES[int(rng.random() * len(COUNTRIES))]
            cp.write_row((i, f"Merchant {i}", category, country, risk))


def _seed_transactions(cur: psycopg.Cursor, n: int, n_acc: int, n_mer: int, seed: int) -> None:
    rng = random.Random(seed)
    with cur.copy(
        "COPY transactions (txn_id, account_id, merchant_id, amount, currency, ts, status, channel, is_flagged) "
        "FROM STDIN"
    ) as cp:
        for txn_id in range(1, n + 1):
            cp.write_row(_txn_row(rng, txn_id, n_acc, n_mer))
            if txn_id % 500_000 == 0:
                console.log(f"  transactions: {txn_id:,}/{n:,}")


def _seed_ledger(cur: psycopg.Cursor, n: int, n_acc: int, n_mer: int, seed: int) -> None:
    # Re-run the SAME txn RNG so each ledger entry references its transaction's real account/ts/amount.
    rng = random.Random(seed)
    with cur.copy(
        "COPY ledger_entries (entry_id, txn_id, account_id, direction, amount, balance_after, posted_at) FROM STDIN"
    ) as cp:
        bal = random.Random(seed + 3)
        for txn_id in range(1, n + 1):
            _, account_id, _m, amount, _c, ts, status, _ch, _f = _txn_row(rng, txn_id, n_acc, n_mer)
            direction = "debit" if bal.random() < 0.7 else "credit"
            balance_after = round(bal.uniform(0, 50_000), 2)
            posted_at = ts + timedelta(seconds=bal.randint(0, 90))
            cp.write_row((txn_id, txn_id, account_id, direction, amount, balance_after, posted_at))
            if txn_id % 500_000 == 0:
                console.log(f"  ledger_entries: {txn_id:,}/{n:,}")


def seed(
    n_accounts: int | None = None,
    n_merchants: int | None = None,
    n_transactions: int | None = None,
    seed_rng: int | None = None,
) -> None:
    n_acc = n_accounts or settings.seed_accounts
    n_mer = n_merchants or settings.seed_merchants
    n_txn = n_transactions or settings.seed_transactions
    rng_seed = seed_rng if seed_rng is not None else settings.seed_rng

    console.rule("[bold cyan]Qurator seeder")
    console.log(f"accounts={n_acc:,}  merchants={n_mer:,}  transactions={n_txn:,}  seed={rng_seed}")

    with connect() as conn, conn.cursor() as cur:
        console.log("truncating…")
        cur.execute("TRUNCATE ledger_entries, transactions, accounts, merchants RESTART IDENTITY CASCADE")

        console.log("seeding accounts…")
        _seed_accounts(cur, n_acc, rng_seed)
        console.log("seeding merchants…")
        _seed_merchants(cur, n_mer, rng_seed)
        console.log("seeding transactions…")
        _seed_transactions(cur, n_txn, n_acc, n_mer, rng_seed)
        console.log("seeding ledger_entries…")
        _seed_ledger(cur, n_txn, n_acc, n_mer, rng_seed)

        console.log("ANALYZE (refresh planner statistics)…")
        cur.execute("ANALYZE")

        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        console.log(f"[green]done. database size: {cur.fetchone()[0]}")


if __name__ == "__main__":
    seed()
