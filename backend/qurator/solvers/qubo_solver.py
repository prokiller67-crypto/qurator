"""Decode QUBO/QAOA bitstrings into scored, feasible index selections.

QAOA (and the unbalanced-penalty QUBO) return a DISTRIBUTION over bitstrings, not a guaranteed-feasible
optimum. The standard, honest way to extract an answer: take the most promising (lowest-energy / highest-
probability) samples, REPAIR each to fit the budget, then post-select the one with the best TRUE workload
benefit. Feasibility and optimality are always judged by the real objective — the QUBO only shapes where the
sampler looks.
"""

from __future__ import annotations

import numpy as np

from ..model import IndexProblem, repair_to_feasible
from ..qubo import QUBO
from .classical import Solution, _finalize


def decode_and_score(problem: IndexProblem, x: np.ndarray, method: str = "qubo") -> Solution:
    """Repair one bitstring to feasibility and score it by the true objective."""
    sel = repair_to_feasible(problem, [i for i in range(problem.n_candidates) if x[i] > 0.5])
    return _finalize(problem, sel, method)


def best_of(problem: IndexProblem, bitstrings: list[np.ndarray], method: str = "qubo") -> Solution:
    """Post-select the feasible-repaired bitstring with the highest true workload benefit."""
    best: Solution | None = None
    for x in bitstrings:
        sol = decode_and_score(problem, x, method)
        if best is None or sol.benefit > best.benefit:
            best = sol
    return best if best is not None else _finalize(problem, [], method)


def solve_qubo_bruteforce(problem: IndexProblem, qubo: QUBO, k: int = 32) -> Solution:
    """Classical reference for the QAOA path: post-select over the k lowest-energy QUBO states.

    Mirrors exactly what the QAOA solver does with its samples, so QAOA can be compared apples-to-apples.
    """
    return best_of(problem, qubo.lowest_energy_bitstrings(k), method="qubo-bruteforce")
