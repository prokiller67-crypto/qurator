"""Candidate index set for the demo workload.

Curated to be interesting for optimization: single-column candidates PLUS composite candidates that
*dominate* pairs of singles for specific queries. That domination is exactly the pairwise interaction
that makes budgeted index selection NP-hard — and gives QAOA something a greedy heuristic gets wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Candidate:
    id: str
    table: str
    columns: tuple[str, ...]
    note: str = ""

    @property
    def label(self) -> str:
        return f"{self.table}({', '.join(self.columns)})"

    @property
    def index_name(self) -> str:
        return f"qur_{self.id}"

    def create_sql(self, *, hypothetical: bool) -> str:
        cols = ", ".join(self.columns)
        if hypothetical:
            # HypoPG names the index itself; omit the name.
            return f"CREATE INDEX ON {self.table} ({cols})"
        return f"CREATE INDEX {self.index_name} ON {self.table} ({cols})"

    def drop_sql(self) -> str:
        return f"DROP INDEX IF EXISTS {self.index_name}"


CANDIDATES: list[Candidate] = [
    # --- transactions: single-column ---
    Candidate("txn_account", "transactions", ("account_id",), "FK; account lookups"),
    Candidate("txn_merchant", "transactions", ("merchant_id",), "FK; merchant joins"),
    Candidate("txn_ts", "transactions", ("ts",), "time-range scans"),
    Candidate("txn_status", "transactions", ("status",), "settlement filters"),
    Candidate("txn_channel", "transactions", ("channel",), "fraud channel filter"),
    Candidate("txn_flagged", "transactions", ("is_flagged",), "flagged filter"),
    Candidate("txn_amount", "transactions", ("amount",), "high-value filter/sort"),
    # --- transactions: composite (these DOMINATE pairs of the singles above) ---
    Candidate("txn_account_ts", "transactions", ("account_id", "ts"), "dominates txn_account + txn_ts"),
    Candidate("txn_merchant_ts", "transactions", ("merchant_id", "ts"), "dominates txn_merchant + txn_ts"),
    Candidate("txn_status_ts", "transactions", ("status", "ts"), "dominates txn_status + txn_ts"),
    Candidate("txn_channel_amount", "transactions", ("channel", "amount"), "dominates txn_channel + txn_amount"),
    Candidate("txn_flagged_amount", "transactions", ("is_flagged", "amount"), "dominates txn_flagged + txn_amount"),
    # --- ledger_entries ---
    Candidate("led_account", "ledger_entries", ("account_id",), "balance lookups"),
    Candidate("led_posted", "ledger_entries", ("posted_at",), "time scans"),
    Candidate("led_account_posted", "ledger_entries", ("account_id", "posted_at"), "dominates led_account + led_posted"),
    Candidate("led_txn", "ledger_entries", ("txn_id",), "FK join to transactions"),
    # --- accounts ---
    Candidate("acc_country", "accounts", ("country",), "cross-border filter"),
    Candidate("acc_status", "accounts", ("status",), "account status filter"),
    # --- merchants ---
    Candidate("mer_category", "merchants", ("category",), "category filter"),
    Candidate("mer_country", "merchants", ("country",), "cross-border filter"),
    Candidate("mer_risk", "merchants", ("risk_score",), "risk filter"),
]


def by_id() -> dict[str, Candidate]:
    return {c.id: c for c in CANDIDATES}
