# Postgres 16 with the HypoPG extension (hypothetical indexes) for what-if cost analysis.
# HypoPG lets us measure the benefit of an index WITHOUT actually building it — the core of Qurator's Cost Probe.
FROM postgres:16

# The official postgres image ships the PGDG apt repo, so hypopg is one apt install away (no compiling).
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-hypopg \
    && rm -rf /var/lib/apt/lists/*

# Everything in /docker-entrypoint-initdb.d runs once, in alphabetical order, on first cluster init.
COPY init/ /docker-entrypoint-initdb.d/
