"""QUBO correctness — the QUBO landscape must place the true optimum among its lowest-energy states, so that
decoding + true-objective post-selection recovers it (exactly when the pairwise surrogate is exact)."""

from __future__ import annotations

import numpy as np
import pytest

from qurator.model import IndexProblem
from qurator.qubo import build_qubo
from qurator.solvers import classical
from qurator.solvers.qubo_solver import solve_qubo_bruteforce


def test_energy_is_quadratic_form() -> None:
    prob = IndexProblem.random_instance(n_candidates=8, seed=1)
    Q = build_qubo(prob)
    x = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=float)
    assert Q.energy(x) == pytest.approx(float(x @ Q.Q @ x + Q.offset))


@pytest.mark.parametrize("seed", range(15))
def test_qubo_recovers_exact_when_surrogate_exact(seed: int) -> None:
    """≤2 candidates help any query → pairwise surrogate is exact → decoded QUBO solution == true optimum."""
    prob = IndexProblem.random_instance(n_candidates=12, n_queries=7, seed=seed, max_helpers=2)
    Q = build_qubo(prob)
    sol = solve_qubo_bruteforce(prob, Q, k=64)
    exact = classical.exact(prob)
    assert prob.is_feasible(sol.selected)
    assert sol.benefit == pytest.approx(exact.benefit, rel=1e-9)


@pytest.mark.parametrize("seed", range(15))
def test_qubo_near_optimal_general(seed: int) -> None:
    """General instances (up to 3 helpers/query): decoded QUBO solution is feasible and near-optimal.

    The pairwise surrogate under-counts queries served by 3+ selected indexes, so it can trail the true
    optimum by a few percent here — the honest limitation the demo discloses (and why the classical exact
    solver stays in the loop). On the tuned real instance the optimum uses ≤2 indexes/query, so it's exact.
    """
    prob = IndexProblem.random_instance(n_candidates=12, n_queries=7, seed=seed, max_helpers=3)
    Q = build_qubo(prob)
    sol = solve_qubo_bruteforce(prob, Q, k=64)
    exact = classical.exact(prob)
    assert prob.is_feasible(sol.selected)
    assert sol.benefit >= 0.93 * exact.benefit


def test_qubo_penalizes_budget_violation() -> None:
    """The all-ones selection (clearly over budget) must have higher energy than the QUBO minimum."""
    prob = IndexProblem.random_instance(n_candidates=10, budget_frac=0.3, seed=3)
    Q = build_qubo(prob)
    x, _ = Q.brute_force_min()
    assert Q.energy(np.ones(prob.n_candidates)) > Q.energy(x)
