"""QAOA quantum core — solve the index-selection QUBO on a real quantum circuit (statevector simulation).

Pipeline: QUBO Q  →  Ising cost Hamiltonian H_C  →  QAOAAnsatz(reps=p)  →  optimize ⟨H_C⟩ with COBYLA  →
sample the final state's bitstring distribution  →  decode + post-select by the TRUE objective.

We simulate the circuit exactly with `Statevector`, which gives noise-free probabilities — ideal for the
"probability cloud collapsing onto the winning bitstring" animation. Every optimizer step is recorded
(energy + top subset probabilities) so the frontend can replay the search. A shots-based Aer / IBM-hardware
path can be swapped in later without touching the rest of the pipeline.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp, Statevector
from scipy.optimize import minimize

from ..model import IndexProblem
from ..qubo import QUBO
from .classical import Solution, greedy
from .qubo_solver import best_of


# ---- QUBO → Ising Hamiltonian -----------------------------------------------------------

def qubo_to_ising(Q: np.ndarray, offset: float) -> tuple[float, np.ndarray, np.ndarray]:
    """Map minimize xᵀQx+offset (x∈{0,1}) to an Ising model over z∈{−1,+1} via x=(1−z)/2.

    Returns (constant, h, J) with energy = constant + Σ hᵢ zᵢ + Σ_{i<j} J_ij zᵢ zⱼ.
    """
    n = Q.shape[0]
    a = np.diag(Q).astype(float)                       # linear coeff of xᵢ
    b = np.zeros((n, n))                               # pairwise coeff of xᵢxⱼ (i<j)
    for i, j in itertools.combinations(range(n), 2):
        b[i, j] = Q[i, j] + Q[j, i]

    const = offset + 0.5 * a.sum() + 0.25 * b[np.triu_indices(n, 1)].sum()
    h = -0.5 * a
    for i, j in itertools.combinations(range(n), 2):
        h[i] -= 0.25 * b[i, j]
        h[j] -= 0.25 * b[i, j]
    J = 0.25 * b
    return float(const), h, J


def cost_hamiltonian(qubo: QUBO) -> SparsePauliOp:
    const, h, J = qubo_to_ising(qubo.Q, qubo.offset)
    n = qubo.n
    terms: list[tuple[str, list[int], float]] = []
    if abs(const) > 1e-12:
        terms.append(("", [], const))
    for i in range(n):
        if abs(h[i]) > 1e-12:
            terms.append(("Z", [i], float(h[i])))
    for i, j in itertools.combinations(range(n), 2):
        if abs(J[i, j]) > 1e-12:
            terms.append(("ZZ", [i, j], float(J[i, j])))
    return SparsePauliOp.from_sparse_list(terms, num_qubits=n)


# ---- QAOA run ---------------------------------------------------------------------------

@dataclass
class QAOATrace:
    energies: list[float] = field(default_factory=list)          # ⟨H_C⟩ per optimizer evaluation
    prob_snapshots: list[dict] = field(default_factory=list)     # top-k {selection_label: prob} checkpoints


@dataclass
class QAOAResult:
    solution: Solution
    n_qubits: int
    reps: int
    n_evals: int
    optimal_value: float
    final_distribution: list[dict]         # top-k [{labels, prob, benefit, feasible}]
    trace: QAOATrace
    optimal_params: list[float]


def _bits_to_x(bitstring: str, n: int) -> np.ndarray:
    # Statevector keys are little-endian: rightmost char is qubit 0 == candidate 0.
    return np.array([int(bitstring[n - 1 - i]) for i in range(n)], dtype=float)


def _prepare(qubo: QUBO, reps: int):
    hc = cost_hamiltonian(qubo)
    ansatz = QAOAAnsatz(cost_operator=hc, reps=reps)
    # Expand PauliEvolutionGate into basic gates once (symbolically) so Statevector can simulate quickly.
    prepared = ansatz.decompose(reps=4)
    return hc, prepared


def _interp(params: np.ndarray, reps: int) -> np.ndarray:
    """INTERP heuristic: extend an optimal (β,γ) schedule from p→p+1 reps by linear interpolation.

    QAOAAnsatz orders parameters as [β_0..β_{p-1}, γ_0..γ_{p-1}]. We stretch each half onto p+1 points; this
    is the standard trick that lets QAOA reliably concentrate probability at higher depth."""
    betas, gammas = params[:reps], params[reps:]

    def stretch(vec: np.ndarray) -> np.ndarray:
        old = np.linspace(0.0, 1.0, len(vec))
        new = np.linspace(0.0, 1.0, len(vec) + 1)
        return np.interp(new, old, vec)

    return np.concatenate([stretch(betas), stretch(gammas)])


def _topk_selection_probs(
    problem: IndexProblem, qubo: QUBO, probs: dict[str, float], k: int
) -> list[dict]:
    n = qubo.n
    rows = []
    for bit, p in sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:k]:
        x = _bits_to_x(bit, n)
        sel = [i for i in range(n) if x[i] > 0.5]
        rows.append({
            "labels": [qubo.candidate_ids[i] for i in sel],
            "prob": float(p),
            "size_mb": round(problem.total_size(sel) / 1e6, 1),
            "benefit": float(problem.workload_benefit(sel)),
            "feasible": bool(problem.is_feasible(sel)),
        })
    return rows


def run_qaoa(
    problem: IndexProblem,
    qubo: QUBO,
    reps: int = 4,
    maxiter: int = 140,
    seed: int = 7,
    snapshot_every: int = 6,
    topk: int = 16,
    pool: int = 256,
) -> QAOAResult:
    """Optimize the QAOA circuit with layerwise INTERP growth (p:1→reps) and decode the best feasible index
    set from the final state's distribution (post-selected by the TRUE objective)."""
    hc = cost_hamiltonian(qubo)
    n = qubo.n
    trace = QAOATrace()
    eval_count = {"n": 0}
    params: np.ndarray | None = None
    prepared_final = None

    for p in range(1, reps + 1):
        _, prepared = _prepare(qubo, p)
        x0 = (
            np.concatenate([np.linspace(0.4, 0.1, p), np.linspace(0.2, 0.6, p)])
            if params is None
            else _interp(params, p - 1)
        )

        def energy(pr: np.ndarray, _prepared=prepared) -> float:
            sv = Statevector(_prepared.assign_parameters(list(pr)))
            val = float(sv.expectation_value(hc).real)
            trace.energies.append(val)
            if eval_count["n"] % snapshot_every == 0:
                trace.prob_snapshots.append(
                    {"eval": eval_count["n"], "reps": p, "energy": val,
                     "top": _topk_selection_probs(problem, qubo, sv.probabilities_dict(), 6)}
                )
            eval_count["n"] += 1
            return val

        res = minimize(energy, x0, method="COBYLA", options={"maxiter": maxiter, "rhobeg": 0.2})
        params = np.asarray(res.x)
        prepared_final = prepared
        best_val = float(res.fun)

    # Decode the final state: post-select the best feasible bitstring by TRUE benefit over a wide pool.
    final_sv = Statevector(prepared_final.assign_parameters(list(params)))
    probs = final_sv.probabilities_dict()
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    top_bitstrings = [_bits_to_x(b, n) for b, _ in ranked[:pool]]
    solution = best_of(problem, top_bitstrings, method="qaoa")

    return QAOAResult(
        solution=solution,
        n_qubits=n,
        reps=reps,
        n_evals=eval_count["n"],
        optimal_value=best_val,
        final_distribution=_topk_selection_probs(problem, qubo, probs, topk),
        trace=trace,
        optimal_params=[float(v) for v in params],
    )
