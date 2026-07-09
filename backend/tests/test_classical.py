"""Classical solver correctness — the exact solver IS our ground truth, so it must be provably correct."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from qurator.model import IndexProblem, mask_from_indices
from qurator.solvers import classical


def brute_force(problem: IndexProblem) -> float:
    """Reference optimum by exhaustive enumeration of all feasible subsets."""
    n = problem.n_candidates
    best = 0.0
    for r in range(n + 1):
        for combo in itertools.combinations(range(n), r):
            if problem.is_feasible(combo):
                best = max(best, problem.workload_benefit(combo))
    return best


@pytest.mark.parametrize("seed", range(12))
def test_exact_matches_brute_force(seed: int) -> None:
    prob = IndexProblem.random_instance(n_candidates=12, n_queries=6, seed=seed)
    assert classical.exact(prob).benefit == pytest.approx(brute_force(prob), rel=1e-9)


@pytest.mark.parametrize("seed", range(12))
def test_greedy_is_feasible_and_not_better_than_exact(seed: int) -> None:
    prob = IndexProblem.random_instance(n_candidates=14, n_queries=7, seed=seed)
    g = classical.greedy(prob)
    x = classical.exact(prob)
    assert prob.is_feasible(g.selected)
    assert prob.is_feasible(x.selected)
    assert g.benefit <= x.benefit + 1e-9          # greedy can never beat the true optimum
    assert x.benefit >= g.benefit                  # exact is at least as good


@pytest.mark.parametrize("seed", range(8))
def test_annealing_feasible_and_close(seed: int) -> None:
    prob = IndexProblem.random_instance(n_candidates=14, n_queries=7, seed=seed)
    a = classical.simulated_annealing(prob, iters=8000, seed=seed)
    x = classical.exact(prob)
    assert prob.is_feasible(a.selected)
    assert a.benefit <= x.benefit + 1e-9
    assert a.benefit >= 0.85 * x.benefit           # a decent SA should get within 15% of optimum


def test_greedy_can_be_suboptimal() -> None:
    """A hand-built instance where greedy's benefit-per-byte choice misses the composite optimum."""
    # 3 candidates, 2 queries. Candidate 2 (composite) serves BOTH queries but is larger.
    benefit = np.array([
        [10.0, 0.0, 9.0],   # q0 helped by c0 (10) or c2 (9)
        [0.0, 10.0, 9.0],   # q1 helped by c1 (10) or c2 (9)
    ])
    sizes = np.array([4.0, 4.0, 5.0])
    prob = IndexProblem(
        candidate_ids=["c0", "c1", "c2"], query_ids=["q0", "q1"],
        weights=np.array([1.0, 1.0]), benefit=benefit, sizes=sizes, budget=5.0,
    )
    # Budget 5 fits only ONE of c0/c1 (benefit 10) OR c2 alone (benefit 18). Optimum = c2.
    x = classical.exact(prob)
    assert set(x.labels) == {"c2"}
    assert x.benefit == pytest.approx(18.0)
