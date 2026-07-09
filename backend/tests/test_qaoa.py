"""QAOA core — on small instances (surrogate exact) the quantum solver must recover the true optimum.

Kept small (8 qubits) so the statevector simulation runs in seconds inside CI."""

from __future__ import annotations

import pytest

from qurator.model import IndexProblem
from qurator.qubo import build_qubo
from qurator.solvers import classical
from qurator.solvers.qaoa import cost_hamiltonian, run_qaoa


def test_cost_hamiltonian_is_diagonal_energy() -> None:
    """H_C's diagonal must equal the QUBO energy of each basis state (Ising mapping is correct)."""
    import numpy as np
    from qiskit.quantum_info import Statevector

    prob = IndexProblem.random_instance(n_candidates=6, n_queries=4, seed=2)
    Q = build_qubo(prob)
    hc = cost_hamiltonian(Q)
    mat = hc.to_matrix()
    for k in range(2 ** Q.n):
        x = np.array([(k >> i) & 1 for i in range(Q.n)], dtype=float)  # little-endian: bit i -> qubit i
        assert mat[k, k].real == pytest.approx(Q.energy(x), rel=1e-9, abs=1e-9)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_qaoa_recovers_exact_small(seed: int) -> None:
    prob = IndexProblem.random_instance(n_candidates=8, n_queries=5, seed=seed, max_helpers=2)
    Q = build_qubo(prob)
    exact = classical.exact(prob)
    r = run_qaoa(prob, Q, reps=3, maxiter=120, seed=seed)
    assert r.solution.benefit == pytest.approx(exact.benefit, rel=1e-9)
    assert prob.is_feasible(r.solution.selected)
