-- Extensions Qurator relies on.
-- hypopg: hypothetical indexes — measure an index's benefit via EXPLAIN without building it.
-- pg_stat_statements: capture the real query workload (optional, used for workload discovery).
CREATE EXTENSION IF NOT EXISTS hypopg;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
