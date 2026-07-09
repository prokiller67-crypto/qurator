"""End-to-end orchestrator — runs the whole Qurator pipeline and produces one serializable RunArtifact.

    workload + candidates
        → HypoPG Cost Probe            (benefits, sizes)
        → classical baselines           (greedy, exact, simulated annealing)
        → QUBO → QAOA                    (quantum-selected set + convergence trace + probability cloud)
        → apply indexes & measure        (real before/after latency)
        → RunArtifact (JSON)             (everything the frontend needs to render the theater)

The artifact is cached to disk so the demo runs off a known-good record and never depends on a live QAOA or
DB timing on stage. `run_pipeline(..., with_latency=False, reps=...)` gives a fast path for iteration.
"""

from __future__ import annotations

import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .candidates import by_id
from .costprobe import probe
from .qubo import build_qubo
from .solvers import classical
from .solvers.qaoa import run_qaoa
from .workload import WORKLOAD

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
DEMO_RUN_PATH = CACHE_DIR / "demo_run.json"


def _solution_dict(problem, sol, optimum_benefit: float) -> dict:
    cmap = by_id()
    return {
        "method": sol.method,
        "selected": sol.labels,
        "selected_detail": [{"id": cid, "label": cmap[cid].label} for cid in sol.labels],
        "size_mb": round(sol.size / 1e6, 1),
        "benefit": round(sol.benefit, 1),
        "pct_of_optimum": round(100.0 * sol.benefit / optimum_benefit, 1) if optimum_benefit else 0.0,
        "residual_cost": round(problem.baseline_workload_cost() - sol.benefit, 1),
    }


def _interaction_edges(problem, reduced_ids: list[str], top: int = 24) -> list[dict]:
    """Pairs of candidates that BOTH help some query (weighted shared benefit) — the interaction graph."""
    w, b = problem.weights, problem.benefit
    edges = []
    for i, j in itertools.combinations(range(problem.n_candidates), 2):
        overlap = float((w * np.minimum(b[:, i], b[:, j])).sum())
        if overlap > 0:
            edges.append({"source": reduced_ids[i], "target": reduced_ids[j], "weight": round(overlap, 1)})
    edges.sort(key=lambda e: e["weight"], reverse=True)
    return edges[:top]


def run_pipeline(
    budget_mb: float | None = None,
    with_latency: bool = True,
    reps: int = 4,
    latency_runs: int = 3,
) -> dict:
    probe_result = probe(budget_mb=budget_mb)
    full = probe_result.problem
    reduced, keep = full.prune()
    report = probe_result.report()

    # --- classical baselines (on the pruned instance the quantum solver also sees) ---
    greedy = classical.greedy(reduced)
    exact = classical.exact(reduced)
    anneal = classical.simulated_annealing(reduced)

    # --- quantum core ---
    qubo = build_qubo(reduced)
    qaoa = run_qaoa(reduced, qubo, reps=reps)

    opt = exact.benefit
    artifact: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "budget_mb": round(reduced.budget / 1e6, 1),
            "total_candidate_mb": round(full.sizes.sum() / 1e6, 1),
            "n_candidates_total": full.n_candidates,
            "n_candidates_active": reduced.n_candidates,
            "n_qubits": reduced.n_candidates,
            "baseline_workload_cost": round(reduced.baseline_workload_cost(), 1),
        },
        "workload": [
            {"id": q.id, "weight": q.weight, "note": q.note,
             "baseline_cost": report["queries"][j]["baseline_cost"]}
            for j, q in enumerate(WORKLOAD)
        ],
        "candidates": report["candidates"],
        "active_candidates": reduced.candidate_ids,
        "interaction_edges": _interaction_edges(reduced, reduced.candidate_ids),
        "solvers": {
            "greedy": _solution_dict(reduced, greedy, opt),
            "anneal": _solution_dict(reduced, anneal, opt),
            "exact": _solution_dict(reduced, exact, opt),
            "qaoa": _solution_dict(reduced, qaoa.solution, opt),
        },
        "qaoa": {
            "n_qubits": qaoa.n_qubits,
            "reps": qaoa.reps,
            "n_evals": qaoa.n_evals,
            "optimal_value": round(qaoa.optimal_value, 4),
            "matches_exact": set(qaoa.solution.labels) == set(exact.labels),
            "energies": [round(e, 4) for e in qaoa.trace.energies],
            "prob_snapshots": qaoa.trace.prob_snapshots,
            "final_distribution": qaoa.final_distribution,
        },
    }

    if with_latency:
        from .apply import benchmark_config

        base = benchmark_config([], "baseline", runs=latency_runs)
        gb = benchmark_config(greedy.labels, "greedy", runs=latency_runs)
        xb = benchmark_config(exact.labels, "exact/quantum", runs=latency_runs)
        artifact["latency"] = {
            cfg.label: {
                "per_query_ms": {k: round(v, 2) for k, v in cfg.per_query_ms.items()},
                "total_ms": round(cfg.total_ms, 1),
                "weighted_ms": round(cfg.weighted_ms, 1),
                "build_ms": round(cfg.build_ms, 1),
                "applied": cfg.applied,
            }
            for cfg in (base, gb, xb)
        }
        artifact["headline"] = {
            "baseline_weighted_ms": round(base.weighted_ms, 1),
            "optimum_weighted_ms": round(xb.weighted_ms, 1),
            "greedy_weighted_ms": round(gb.weighted_ms, 1),
            "speedup": round(base.weighted_ms / xb.weighted_ms, 1) if xb.weighted_ms else 0.0,
            "greedy_slowdown": round(gb.weighted_ms / xb.weighted_ms, 2) if xb.weighted_ms else 0.0,
        }

    return artifact


def cache_run(budget_mb: float | None = None, reps: int = 4) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    artifact = run_pipeline(budget_mb=budget_mb, with_latency=True, reps=reps)
    DEMO_RUN_PATH.write_text(json.dumps(artifact, indent=2))
    return DEMO_RUN_PATH


def load_cached_run() -> dict | None:
    if DEMO_RUN_PATH.exists():
        return json.loads(DEMO_RUN_PATH.read_text())
    return None
