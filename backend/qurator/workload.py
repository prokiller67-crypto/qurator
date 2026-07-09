"""The demo query workload — dashboard + fraud-scan queries a fintech runs constantly.

Literals are fixed (not parameters) so EXPLAIN costs are deterministic and reproducible. Values fall inside
the seeded ranges (accounts 1..N, merchants 1..M, ts in 2026-01-01 .. 2026-07-01). Weights approximate how
often each query runs, so total workload cost is Σ weightᵩ · costᵩ.
"""

from __future__ import annotations

from dataclasses import dataclass

# A demo "hot" account and time anchors inside the seeded window.
HOT_ACCOUNT = 7777


@dataclass(frozen=True)
class Query:
    id: str
    weight: float
    sql: str
    note: str = ""


WORKLOAD: list[Query] = [
    Query(
        "account_statement", 5.0,
        f"""SELECT txn_id, amount, ts, status
            FROM transactions
            WHERE account_id = {HOT_ACCOUNT} AND ts >= '2026-03-01' AND ts < '2026-04-01'
            ORDER BY ts""",
        "monthly statement for one account — wants transactions(account_id, ts)",
    ),
    Query(
        "settlement_by_merchant", 3.0,
        """SELECT merchant_id, sum(amount) AS settled
           FROM transactions
           WHERE status = 'settled' AND ts >= '2026-03-01' AND ts < '2026-03-08'
           GROUP BY merchant_id""",
        "weekly settlement dashboard — wants transactions(status, ts)",
    ),
    Query(
        "fraud_cnp_highvalue", 4.0,
        """SELECT txn_id, account_id, amount
           FROM transactions
           WHERE channel = 'card_not_present' AND amount > 2000
           ORDER BY amount DESC
           LIMIT 100""",
        "card-not-present high-value scan — wants transactions(channel, amount)",
    ),
    Query(
        "flagged_highvalue", 3.0,
        """SELECT txn_id, account_id, amount
           FROM transactions
           WHERE is_flagged = true AND amount > 500""",
        "review queue of flagged high-value txns — wants transactions(is_flagged, amount)",
    ),
    Query(
        "account_ledger", 4.0,
        f"""SELECT entry_id, amount, balance_after, posted_at
            FROM ledger_entries
            WHERE account_id = {HOT_ACCOUNT}
            ORDER BY posted_at DESC
            LIMIT 50""",
        "recent balance history — wants ledger_entries(account_id, posted_at)",
    ),
    Query(
        "velocity_check", 5.0,
        f"""SELECT count(*)
            FROM transactions
            WHERE account_id = {HOT_ACCOUNT} AND ts >= '2026-06-01'""",
        "recent transaction velocity — wants transactions(account_id, ts)",
    ),
    Query(
        "merchant_category_dash", 3.0,
        """SELECT m.name, sum(t.amount) AS volume
           FROM transactions t
           JOIN merchants m ON t.merchant_id = m.merchant_id
           WHERE m.category = 'crypto' AND t.ts >= '2026-03-01' AND t.ts < '2026-04-01'
           GROUP BY m.name""",
        "category volume dashboard — wants merchants(category) + transactions(merchant_id, ts)",
    ),
    Query(
        "cross_border_scan", 2.0,
        """SELECT count(*)
           FROM transactions t
           JOIN accounts a ON t.account_id = a.account_id
           JOIN merchants m ON t.merchant_id = m.merchant_id
           WHERE a.country <> m.country AND t.amount > 1000""",
        "cross-border high-value count — wants amount + country indexes",
    ),
]


def total_weight() -> float:
    return sum(q.weight for q in WORKLOAD)
