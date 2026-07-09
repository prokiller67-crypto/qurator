-- Qurator demo schema: a small but realistic fintech payments ledger.
--
-- Design intent: ONLY primary keys are indexed. Every foreign-key column, filter column, and sort column
-- is deliberately left unindexed so that Qurator's candidate indexes have real, measurable benefit — and so
-- the indexes INTERACT (a composite index can dominate two single-column ones), which is what makes the
-- index-selection problem NP-hard and interesting for QAOA.

CREATE TABLE accounts (
    account_id    BIGINT PRIMARY KEY,
    customer_name TEXT        NOT NULL,
    country       CHAR(2)     NOT NULL,           -- ISO-3166 alpha-2
    kyc_level     SMALLINT    NOT NULL,           -- 0..3
    status        TEXT        NOT NULL,           -- 'active' | 'frozen' | 'closed'
    created_at    TIMESTAMPTZ NOT NULL
);

CREATE TABLE merchants (
    merchant_id BIGINT PRIMARY KEY,
    name        TEXT     NOT NULL,
    category    TEXT     NOT NULL,                -- MCC-like category, e.g. 'crypto', 'gambling', 'grocery'
    country     CHAR(2)  NOT NULL,
    risk_score  SMALLINT NOT NULL                 -- 0..100
);

CREATE TABLE transactions (
    txn_id      BIGINT PRIMARY KEY,
    account_id  BIGINT        NOT NULL REFERENCES accounts(account_id),
    merchant_id BIGINT        NOT NULL REFERENCES merchants(merchant_id),
    amount      NUMERIC(12,2) NOT NULL,
    currency    CHAR(3)       NOT NULL,           -- ISO-4217
    ts          TIMESTAMPTZ   NOT NULL,
    status      TEXT          NOT NULL,           -- 'settled' | 'pending' | 'declined' | 'reversed'
    channel     TEXT          NOT NULL,           -- 'pos' | 'ecom' | 'card_not_present' | 'atm' | 'wire'
    is_flagged  BOOLEAN       NOT NULL DEFAULT false
);

CREATE TABLE ledger_entries (
    entry_id      BIGINT PRIMARY KEY,
    txn_id        BIGINT        NOT NULL REFERENCES transactions(txn_id),
    account_id    BIGINT        NOT NULL,
    direction     TEXT          NOT NULL,         -- 'debit' | 'credit'
    amount        NUMERIC(12,2) NOT NULL,
    balance_after NUMERIC(14,2) NOT NULL,
    posted_at     TIMESTAMPTZ   NOT NULL
);
