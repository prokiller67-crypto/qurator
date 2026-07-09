"""The index-selection optimization instance.

Benefit model (honest and standard): Postgres uses (at most) one index per table scan, so a query gets the
benefit of the SINGLE BEST index it has available. For a chosen set S of candidate indexes,

    workload_benefit(S) = Σ_q  weight_q · max_{i ∈ S} benefit[q, i]

subject to a storage budget  Σ_{i ∈ S} size_i ≤ budget.

This is budgeted **weighted maximum coverage** — NP-hard, submodular, and exactly where a greedy DBA heuristic
provably leaves value on the table (the (1−1/e) gap). The `max_{i∈S}` is what a QUBO must linearize (Week 2),
and what makes composite indexes *interact* with the singles they dominate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def mask_from_indices(n: int, indices) -> np.ndarray:
    m = np.zeros(n, dtype=bool)
    for i in indices:
        m[i] = True
    return m


def repair_to_feasible(problem: "IndexProblem", sel) -> list[int]:
    """Make a selection fit the budget by dropping the worst standalone benefit-per-byte index until feasible.

    QAOA (and any unbalanced-penalty QUBO) can return a slightly over-budget bitstring; repair + evaluating the
    TRUE objective is the standard way to turn a heuristic sample into a valid, scored solution.
    """
    mask = problem._as_mask(sel).copy()
    while problem.total_size(mask) > problem.budget + 1e-9:
        chosen = np.where(mask)[0]
        standalone = (problem.weights[:, None] * problem.benefit[:, chosen]).sum(axis=0)
        worst = chosen[np.argmin(standalone / np.maximum(problem.sizes[chosen], 1.0))]
        mask[worst] = False
    return [int(i) for i in np.where(mask)[0]]


@dataclass
class IndexProblem:
    candidate_ids: list[str]
    query_ids: list[str]
    weights: np.ndarray            # (Nq,)
    benefit: np.ndarray            # (Nq, Nc)  per-query planner-cost reduction from each index, clamped ≥ 0
    sizes: np.ndarray              # (Nc,)     estimated index size in bytes
    budget: float                  # bytes
    baseline_cost: np.ndarray = field(default_factory=lambda: np.zeros(0))  # (Nq,) cost with no candidate index

    def __post_init__(self) -> None:
        self.weights = np.asarray(self.weights, dtype=float)
        self.benefit = np.asarray(self.benefit, dtype=float)
        self.sizes = np.asarray(self.sizes, dtype=float)
        if self.baseline_cost.size == 0:
            self.baseline_cost = np.zeros(self.n_queries)

    @property
    def n_candidates(self) -> int:
        return len(self.candidate_ids)

    @property
    def n_queries(self) -> int:
        return len(self.query_ids)

    # ---- objective ------------------------------------------------------------------

    def _as_mask(self, sel) -> np.ndarray:
        if isinstance(sel, np.ndarray) and sel.dtype == bool:
            return sel
        return mask_from_indices(self.n_candidates, sel)

    def workload_benefit(self, sel) -> float:
        """Total weighted cost reduction of selecting index set `sel` (higher = better)."""
        mask = self._as_mask(sel)
        if not mask.any():
            return 0.0
        best_per_query = self.benefit[:, mask].max(axis=1)  # best available index per query
        return float((self.weights * best_per_query).sum())

    def total_size(self, sel) -> float:
        return float(self.sizes[self._as_mask(sel)].sum())

    def is_feasible(self, sel) -> bool:
        return self.total_size(sel) <= self.budget + 1e-9

    def baseline_workload_cost(self) -> float:
        return float((self.weights * self.baseline_cost).sum())

    def residual_workload_cost(self, sel) -> float:
        """Estimated total weighted workload cost AFTER applying `sel` (lower = better)."""
        return self.baseline_workload_cost() - self.workload_benefit(sel)

    # ---- helpers --------------------------------------------------------------------

    def selected_labels(self, sel) -> list[str]:
        mask = self._as_mask(sel)
        return [self.candidate_ids[i] for i in range(self.n_candidates) if mask[i]]

    def prune(self, min_total_benefit: float = 0.0) -> tuple["IndexProblem", list[int]]:
        """Drop candidates whose total weighted benefit is ≤ threshold (they can never be worth their bytes).

        Returns the reduced problem and the list of ORIGINAL candidate indices it kept — so a solution over
        the pruned problem maps back to real candidates. Shrinking the candidate set is what keeps the QAOA
        qubit count in the demoable 14–18 range.
        """
        totals = (self.weights[:, None] * self.benefit).sum(axis=0)  # (Nc,)
        keep = [i for i in range(self.n_candidates) if totals[i] > min_total_benefit]
        reduced = IndexProblem(
            candidate_ids=[self.candidate_ids[i] for i in keep],
            query_ids=list(self.query_ids),
            weights=self.weights.copy(),
            benefit=self.benefit[:, keep].copy(),
            sizes=self.sizes[keep].copy(),
            budget=self.budget,
            baseline_cost=self.baseline_cost.copy(),
        )
        return reduced, keep

    @classmethod
    def random_instance(
        cls, n_candidates: int = 14, n_queries: int = 8, budget_frac: float = 0.4, seed: int = 0,
        max_helpers: int = 3,
    ) -> "IndexProblem":
        """Synthetic instance for tests (no DB needed). Sparse, interacting benefits + heterogeneous sizes.

        `max_helpers` caps how many candidates can help a single query; with max_helpers=2 the pairwise QUBO
        surrogate is exact, so QUBO-min must equal the true optimum.
        """
        rng = np.random.default_rng(seed)
        benefit = np.zeros((n_queries, n_candidates))
        for q in range(n_queries):
            k = int(rng.integers(1, max_helpers + 1))
            helpers = rng.choice(n_candidates, size=k, replace=False)
            benefit[q, helpers] = rng.uniform(50, 1000, size=len(helpers))
        sizes = rng.uniform(5, 60, size=n_candidates) * 1e6
        weights = rng.uniform(1, 5, size=n_queries)
        budget = budget_frac * sizes.sum()
        baseline = benefit.max(axis=1) + rng.uniform(10, 100, size=n_queries)
        return cls(
            candidate_ids=[f"c{i}" for i in range(n_candidates)],
            query_ids=[f"q{j}" for j in range(n_queries)],
            weights=weights, benefit=benefit, sizes=sizes, budget=budget, baseline_cost=baseline,
        )
