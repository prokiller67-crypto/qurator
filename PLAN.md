# Qurator — Project Plan

> **Quantum optimization that picks your database indexes and makes real queries measurably faster.**
> Submission for **QuantumHacks** (deadline **Aug 20, 2026, 5pm PDT**). Themes: Quantum · Databases · Fintech.

---

## The one-sentence pitch

Qurator plugs into a live fintech Postgres, measures real *what-if* index costs with **HypoPG**, builds a genuine
**QUBO**, and runs **QAOA** (Qiskit) to pick the optimal set of indexes under a storage budget — then it **applies**
them to the real database and shows query latency drop from seconds to sub-second, live. The payoff is a real,
measured, non-fakeable system effect, not a chart.

## Why it wins "Innovation"

- **Originality** — Quantum × Databases is the most under-explored theme intersection, backed by real academic
  lineage (Trummer & Koch, VLDB 2016; Schönberger & Mauerer, SIGMOD 2022–23) yet shipped as a product nobody has built.
- **Technical execution** — a complete `HypoPG → QUBO → QAOA → apply → re-benchmark` pipeline; the QUBO is built from
  real cost measurements on a live Postgres, not a synthetic instance.
- **Real-world impact + clarity** — a measured latency drop on a live DB is the most concrete, memorable proof possible.
- **Honesty as sophistication** — we state on-screen that at ~15–22 qubits classical solvers match/beat noisy QAOA, and
  we benchmark QAOA against the exact optimum to *prove* it found the true answer. This converts the field's biggest
  credibility trap into a clarity win.

## The killer differentiator: the closed loop

`QAOA picks indexes → real CREATE INDEX on a live DB → a measured latency drop the audience watches happen.`
Almost no quantum hackathon entry delivers a real system effect instead of a chart.

---

## Architecture — three tiers, all Dockerized

### 1. Data + DB tier
- **PostgreSQL 16 + HypoPG** extension.
- Realistic **fintech schema**: `accounts`, `merchants`, `transactions`, `ledger_entries` at a scale where a set of
  curated dashboard / fraud-scan queries genuinely benefit from indexing.
- A **candidate generator** produces ~15–22 index candidates (single-column + a few predicate-driven multi-column).

### 2. Quantum + backend tier — Python / FastAPI
- **Cost Probe** — issues HypoPG hypothetical-index `EXPLAIN` calls to measure per-query benefit for each candidate and
  pairwise interaction terms.
- **QUBO Builder** — assembles linear benefits + pairwise interference + a budget penalty using the
  **unbalanced-penalty encoding** (no slack qubits).
- **Solver Layer** — maps QUBO → Ising and runs **QAOA on Qiskit Aer** (COBYLA/SPSA outer loop, warm-started from the
  greedy solution), alongside classical baselines (greedy DBA heuristic, exact brute-force for n ≤ 25, simulated
  annealing) for an honest side-by-side. A `qiskit-ibm-runtime` path exists but is **cached/pre-recorded**, never in the
  live critical path.
- **Apply-and-Measure** — runs real `CREATE INDEX` and captures before/after query latency.

### 3. Frontend tier — Next.js / TS
- A **workbench** streaming over WebSocket: candidate table with live HypoPG benefits; the **"optimization theater"**
  (QAOA energy-convergence chart, index-interaction graph, a probability cloud over subsets collapsing to the winning
  bitstring); and a results dashboard (before/after latency bars + quantum-vs-greedy-vs-optimum panel).
- A **cached known-good run** guarantees demo stability, with a live-run button as a bonus.

Deploy: frontend on Vercel; backend + DB on a container host (Fly.io / Render).

---

## 6-week milestones

- **Week 1 — Foundation & ground truth.** Dockerized Postgres+HypoPG seeded with the fintech schema and 6–8 queries
  pre-validated to genuinely benefit from indexing; candidate generator producing ~15–22 candidates; classical baselines
  (greedy + exact brute-force) working so every later result has verified ground truth.
  *Deliverable:* `make demo-db` spins up a DB where greedy vs exact answers differ visibly.
- **Week 2 — QUBO from real costs.** HypoPG Cost Probe measuring linear benefits + pairwise interaction terms; QUBO
  Builder with unbalanced-penalty budget encoding; unit tests confirming the QUBO's classical optimum equals the
  brute-force optimum on small instances.
  *Deliverable:* a correct QUBO whose exact minimizer matches the ground-truth index set.
- **Week 3 — Quantum core.** QAOA on Aer (warm-start + adequate layers, SPSA/COBYLA), verified to converge to the SAME
  optimum the exact solver found on 15–22-candidate instances; simulated-annealing baseline; log per-iteration energy +
  subset-probability snapshots for the animation.
  *Deliverable:* QAOA reproducibly recovers the optimal index set; convergence + probability data streaming.
- **Week 4 — Close the loop + backend API.** Apply-and-Measure doing real `CREATE INDEX` and capturing before/after
  latency; FastAPI + WebSocket streaming of candidates, convergence, probability cloud, and results; record and cache
  one IBM-hardware run of a tiny instance for the flourish.
  *Deliverable:* end-to-end run from workload → QAOA → applied indexes → measured latency drop, over the API.
- **Week 5 — Frontend & the theater.** Next.js workbench — candidate table, the optimization theater, and the
  before/after + quantum-vs-greedy-vs-optimum dashboard; wire the cached known-good run + optional live-run button.
  *Deliverable:* a polished, deployable UI driving the full story with a bulletproof cached path.
- **Week 6 — Harden, deploy, tell the story.** Deploy; pre-seed and lock the demo dataset; rehearse until latency numbers
  are stable; record the 2–5 min video; capture screenshots; write the README with install steps + the honest
  problem/impact/lineage writeup.
  *Deliverable:* live demo link, repo, video, screenshots — all six submission deliverables covered.

---

## The winning demo (2–5 min), beat by beat

- **Beat 1 (0:00–0:30) — the problem, made visceral.** "This is a live Postgres for a fintech app — millions of
  transactions. These six dashboard and fraud-scan queries take 4.2 seconds. A DBA must choose which indexes to build,
  but there are 20 candidates, a 500 MB budget, over a million combinations, and the indexes interfere with each other.
  This is NP-hard."
- **Beat 2 (0:30–1:00) — the workbench & the naive baseline.** Load the workload; candidate indexes populate with their
  real HypoPG-measured benefits; run the greedy DBA heuristic and watch it pick a redundant, sub-optimal set.
- **Beat 3 (1:00–2:00) — quantum solve.** "Qurator puts all million combinations into superposition." Hit RUN — the
  optimization theater lights up: QAOA energy converging, the index-interaction graph, and a probability cloud over
  subsets visibly collapsing onto one winning bitstring. Optional flourish: "and here is the exact same problem on a
  real IBM quantum computer" (cached).
- **Beat 4 (2:00–2:45) — the reveal, real measured payoff.** Apply the quantum-selected indexes to the REAL database and
  re-run the queries live: **4.2s → 0.9s** on screen. Side-by-side bars: the quantum set beats the greedy set within the
  SAME storage budget. Then the honesty panel: quantum vs simulated annealing vs exact optimum — quantum matched the
  true optimum.
- **Beat 5 (2:45–3:15) — impact + candor.** Where it scales (D-Wave / real hardware for 50+ indexes), the real research
  lineage, a frank note that quantum isn't faster than classical at this size yet, and the vision of a quantum tuning
  advisor sitting on production databases. Close on the 4.2s → 0.9s bar.

---

## Scope discipline (solo, demo-safe)

- Cache a known-good run; the live-run button is a bonus, never the critical path.
- Skip live IBM/D-Wave in the hot path — pre-record one hardware run for the flourish.
- Lock **one** pre-validated workload where HypoPG estimates and real latency agree.
- Validate the QUBO encoding early against instances whose exact optimum is known.
