"""Runtime configuration — DB connection and demo defaults, all overridable via env."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    pg_host: str = os.getenv("QURATOR_PG_HOST", "localhost")
    pg_port: int = int(os.getenv("QURATOR_PG_PORT", "5433"))
    pg_user: str = os.getenv("QURATOR_PG_USER", "qurator")
    pg_password: str = os.getenv("QURATOR_PG_PASSWORD", "qurator")
    pg_db: str = os.getenv("QURATOR_PG_DB", "qurator")

    # Default demo scale — enough that unindexed aggregate/scan queries take real wall-clock time.
    seed_accounts: int = int(os.getenv("QURATOR_SEED_ACCOUNTS", "20000"))
    seed_merchants: int = int(os.getenv("QURATOR_SEED_MERCHANTS", "2000"))
    seed_transactions: int = int(os.getenv("QURATOR_SEED_TRANSACTIONS", "2000000"))
    seed_rng: int = int(os.getenv("QURATOR_SEED_RNG", "42"))

    # Canonical demo storage budget (MB). 250MB (~25% of total candidate size) is the tuned instance where
    # greedy is visibly sub-optimal vs the exact/quantum optimum.
    demo_budget_mb: float = float(os.getenv("QURATOR_BUDGET_MB", "250"))

    @property
    def dsn(self) -> str:
        return (
            f"host={self.pg_host} port={self.pg_port} "
            f"user={self.pg_user} password={self.pg_password} dbname={self.pg_db}"
        )


settings = Settings()
