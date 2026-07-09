"""QUBO formulation of the index-selection problem.

We minimize  x^T Q x + offset  over x ∈ {0,1}^Nc, where x_i = "build candidate index i".

Two pieces:

1. Benefit (to maximize → we minimize its negative). The true objective Σ_q w_q · max_{i∈S} b_{q,i} has a
   `max` that isn't quadratic, so we use the standard pairwise linearization:

       benefit(x) ≈ Σ_i L_i x_i  −  Σ_{i<j} O_ij x_i x_j ,
       L_i  = Σ_q w_q b_{q,i}                        (total benefit if i were the only index)
       O_ij = Σ_q w_q min(b_{q,i}, b_{q,j})          (benefit double-counted when i and j both serve a query)

   This is EXACT whenever at most two selected indexes serve any given query (the usual case at an optimum)
   and a principled approximation otherwise.

2. Storage budget Σ_i s_i x_i ≤ B via **unbalanced penalization** (Montañez-Barrera et al. 2022) — an
   inequality penalty that needs NO slack qubits:  penalty(x) = λ1·h(x) + λ2·h(x)²,  h(x) = Σ_i ŝ_i x_i − 1,
   with sizes normalized ŝ_i = s_i / B so the budget is 1 and λ's are O(1).

Benefits are normalized by max_i L_i so all coefficients are O(1) and QAOA stays well-conditioned.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from .model import IndexProblem


@dataclass
class QUBO:
    Q: np.ndarray                 # (n, n) symmetric; energy = x^T Q x + offset
    offset: float
    candidate_ids: list[str]
    benefit_scale: float          # multiply normalized benefit back to planner-cost units
    meta: dict

    @property
    def n(self) -> int:
        return self.Q.shape[0]

    def energy(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float)
        return float(x @ self.Q @ x + self.offset)

    def brute_force_min(self) -> tuple[np.ndarray, float]:
        """Exact QUBO minimizer by enumeration (for validation on small n)."""
        best_x, best_e = None, np.inf
        for bits in itertools.product((0, 1), repeat=self.n):
            x = np.array(bits, dtype=float)
            e = self.energy(x)
            if e < best_e:
                best_x, best_e = x, e
        return best_x, best_e

    def lowest_energy_bitstrings(self, k: int) -> list[np.ndarray]:
        """The k lowest-energy bitstrings (brute force; for validation and classical post-selection on small n)."""
        states = [np.array(bits, dtype=float) for bits in itertools.product((0, 1), repeat=self.n)]
        states.sort(key=self.energy)
        return states[:k]


def build_qubo(
    problem: IndexProblem,
    lambda1: float = 0.9,
    lambda2: float = 2.5,
) -> QUBO:
    n = problem.n_candidates
    w = problem.weights
    b = problem.benefit

    # --- benefit terms (normalized) ---
    L = (w[:, None] * b).sum(axis=0)                      # (n,)
    scale = float(L.max()) if L.max() > 0 else 1.0
    Ln = L / scale
    O = np.zeros((n, n))
    for i, j in itertools.combinations(range(n), 2):
        overlap = float((w * np.minimum(b[:, i], b[:, j])).sum()) / scale
        O[i, j] = O[j, i] = overlap

    # --- normalized budget: ŝ_i = s_i / B, constraint Σ ŝ_i x_i ≤ 1 ---
    s_hat = problem.sizes / problem.budget

    Q = np.zeros((n, n))
    # benefit: minimize −benefit  →  diagonal −L_i, off-diagonal +O_ij (split symmetrically)
    for i in range(n):
        Q[i, i] += -Ln[i]
    for i, j in itertools.combinations(range(n), 2):
        Q[i, j] += O[i, j] / 2.0
        Q[j, i] += O[i, j] / 2.0

    # penalty λ1·h + λ2·h², h = Σ ŝ_i x_i − 1
    #   λ1·h            → diag: λ1·ŝ_i ;                       const: −λ1
    #   λ2·(Σŝx − 1)²   → diag: λ2·(ŝ_i² − 2ŝ_i) ; off: λ2·2ŝ_iŝ_j ; const: λ2
    for i in range(n):
        Q[i, i] += lambda1 * s_hat[i] + lambda2 * (s_hat[i] ** 2 - 2.0 * s_hat[i])
    for i, j in itertools.combinations(range(n), 2):
        Q[i, j] += lambda2 * s_hat[i] * s_hat[j]
        Q[j, i] += lambda2 * s_hat[i] * s_hat[j]
    offset = -lambda1 + lambda2

    return QUBO(
        Q=Q, offset=offset, candidate_ids=list(problem.candidate_ids),
        benefit_scale=scale,
        meta={"lambda1": lambda1, "lambda2": lambda2, "budget_bytes": float(problem.budget)},
    )
