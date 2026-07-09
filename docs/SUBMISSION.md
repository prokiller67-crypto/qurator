# Qurator — Devpost submission copy

Ready-to-paste text for the QuantumHacks submission form. Trim to taste.

---

## Elevator pitch (≤ 200 chars)
Quantum optimization that picks your database indexes and makes real queries measurably faster — QAOA chooses the optimal Postgres indexes under a storage budget, applies them live, and the latency drops on screen.

## Inspiration
Every database team faces the same expensive, unglamorous problem: **which indexes should I build?** With a
fixed storage budget and dozens of candidates, the choice is NP-hard — a budgeted weighted maximum-coverage
problem where indexes interact. Real tuning advisors fall back on greedy heuristics that leave performance on
the table. It turns out this problem maps *perfectly* onto a QUBO — the native language of quantum optimizers.
Quantum × Databases is the most under-explored intersection in this hackathon, and it has real academic lineage
(Trummer & Koch, VLDB 2016; Schönberger & Mauerer, SIGMOD 2022–23). We wanted to ship it as a product nobody
has actually built.

## What it does
Qurator plugs into a live fintech Postgres, measures each candidate index's real *what-if* benefit with HypoPG,
builds a genuine QUBO, and runs **QAOA** (Qiskit) to choose the optimal index set under a storage budget. Then
it does the thing almost no quantum hackathon project does — it **applies the quantum-chosen indexes to the real
database** and re-runs the workload, so you watch the query latency drop from ~1.9 s to ~0.35 s, live. A greedy
DBA heuristic, simulated annealing, and the exact brute-force optimum run side by side for an honest comparison.

## How we built it
- **Postgres 16 + HypoPG** (Docker) — hypothetical indexes let us score candidates without building anything.
- **Cost Probe** — a few hundred cheap `EXPLAIN`s produce the benefit matrix + estimated index sizes.
- **QUBO builder** — linearizes the max-coverage benefit and encodes the storage budget with the
  *unbalanced-penalty* method (no slack qubits, so the qubit count stays in the demoable 15 range).
- **QAOA on Qiskit** — QUBO → Ising Hamiltonian → `QAOAAnsatz`, optimized with layerwise **INTERP** growth
  (p:1→4) so the circuit reliably concentrates probability; decoded by post-selecting the best feasible bitstring
  against the true objective. It recovers the exact optimum on the 15-qubit demo, verified against brute force.
- **Apply-and-measure** — real `CREATE INDEX`, warm cache, median-latency measurement.
- **FastAPI + Next.js** — the "optimization theater": energy convergence, the probability cloud collapsing onto
  the winning index set, the index-interaction graph, and the real before/after latency reveal.

## Challenges we ran into
- The `max_{i∈S}` structure of the true benefit isn't quadratic — we had to linearize it into a faithful QUBO.
- The unbalanced-penalty QUBO can return a slightly over-budget bitstring; we decode by repairing to feasibility
  and scoring with the *true* objective (the standard, honest way to read out a QAOA result).
- Plain QAOA at 15 qubits gave a flat distribution; **INTERP** layerwise growth fixed the concentration.
- A self-inflicted bug: our benchmark left real indexes on the table and polluted the next probe's baseline —
  now every benchmark cleans up after itself.

## Accomplishments we're proud of
- A **real, measured, non-fakeable system effect** — a live latency drop, not a chart.
- **Radical honesty**: at ~15 qubits classical still matches QAOA, and we say so on screen while benchmarking
  QAOA against the exact optimum to prove it found the true answer.
- 69 passing tests, including "the exact solver equals brute force" and "QAOA recovers the optimum."

## What we learned
Quantum advantage isn't the only reason to build a quantum pipeline. A *correct, principled formulation* on real
data — that plugs straight into scaling hardware — is a genuine contribution, and honesty about today's limits
reads as sophistication, not weakness.

## What's next
Run on real IBM Quantum hardware for the finale; scale to D-Wave for 50+ candidate indexes where the advantage
materializes; a background advisor that sits on production databases and proposes tuning changes.

## Built with
postgresql, hypopg, python, qiskit, qiskit-aer, numpy, scipy, fastapi, next.js, react, typescript, tailwindcss, docker

## The honest note (please read, judges)
Qurator is a **correct, principled pipeline and an honest demonstration**, not a quantum-speedup claim. At ~15
qubits a classical solver matches QAOA — which is exactly why we keep the exact solver in the loop and show the
benchmark. The value is a genuine QUBO formulation on real, measured data that plugs directly into scaling
quantum hardware. Everything you see in the demo is real: real Postgres, real HypoPG cost measurements, real
QAOA circuits, real `CREATE INDEX`, real measured latency.
