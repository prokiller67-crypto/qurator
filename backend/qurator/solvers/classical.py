"""Classical baselines — the honest ground truth QAOA is measured against.

  * greedy   — what a DBA (or a naive advisor) does: repeatedly add the best benefit-per-byte index that fits.
               Fast, but provably sub-optimal on interacting instances — this is the gap Qurator exploits.
  * exact    — branch-and-bound over all feasible subsets, maximizing the true max-coverage benefit. The
               verified optimum (feasible for n ≲ 24 thanks to a monotone-coverage bound).
  * anneal   — simulated annealing; a strong classical stochastic baseline for the honesty panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..model import IndexProblem, mask_from_indices


@dataclass
class Solution:
    selected: list[int]
    benefit: float
    size: float
    labels: list[str] = field(default_factory=list)
    method: str = ""

    def mask(self, n: int) -> np.ndarray:
        return mask_from_indices(n, self.selected)


def _finalize(problem: IndexProblem, selected: list[int], method: str) -> Solution:
    selected = sorted(selected)
    return Solution(
        selected=selected,
        benefit=problem.workload_benefit(selected),
        size=problem.total_size(selected),
        labels=[problem.candidate_ids[i] for i in selected],
        method=method,
    )


def greedy(problem: IndexProblem) -> Solution:
    """Budgeted max-coverage greedy: add the candidate with the best marginal benefit-per-byte that fits."""
    n = problem.n_candidates
    selected: list[int] = []
    used = 0.0
    cur_benefit = 0.0
    remaining = set(range(n))

    while True:
        best_i, best_ratio, best_gain = None, 0.0, 0.0
        for i in list(remaining):
            if used + problem.sizes[i] > problem.budget + 1e-9:
                continue
            gain = problem.workload_benefit(selected + [i]) - cur_benefit
            if gain <= 0:
                continue
            ratio = gain / max(problem.sizes[i], 1.0)
            if ratio > best_ratio:
                best_i, best_ratio, best_gain = i, ratio, gain
        if best_i is None:
            break
        selected.append(best_i)
        remaining.discard(best_i)
        used += problem.sizes[best_i]
        cur_benefit += best_gain

    return _finalize(problem, selected, "greedy")


def exact(problem: IndexProblem, max_candidates: int = 24) -> Solution:
    """Branch-and-bound exact optimum. Bound: adding all undecided candidates is an upper bound (coverage is
    monotone), so if that can't beat the incumbent we prune the whole subtree."""
    n = problem.n_candidates
    if n > max_candidates:
        raise ValueError(f"exact() refuses n={n} > {max_candidates}; prune candidates or raise the cap")

    sizes = problem.sizes
    budget = problem.budget
    all_idx = list(range(n))

    # Warm-start the incumbent with greedy to make the bound bite immediately.
    incumbent = greedy(problem)
    best = {"benefit": incumbent.benefit, "selected": list(incumbent.selected)}

    def dfs(d: int, selected: list[int], used: float) -> None:
        # Optimistic bound: everything still selectable (undecided) added on top of `selected`.
        optimistic = problem.workload_benefit(selected + all_idx[d:])
        if optimistic <= best["benefit"] + 1e-9:
            return
        # `selected` is always feasible — score it as a candidate incumbent.
        b = problem.workload_benefit(selected)
        if b > best["benefit"]:
            best["benefit"], best["selected"] = b, list(selected)
        if d == n:
            return
        # include d (if it fits), then exclude d
        if used + sizes[d] <= budget + 1e-9:
            selected.append(d)
            dfs(d + 1, selected, used + sizes[d])
            selected.pop()
        dfs(d + 1, selected, used)

    dfs(0, [], 0.0)
    return _finalize(problem, best["selected"], "exact")


def simulated_annealing(
    problem: IndexProblem, iters: int = 40_000, seed: int = 0, t0: float = 1.0, t1: float = 1e-3
) -> Solution:
    """SA over feasible index sets. Neighbor = flip one candidate; over-budget states are repaired by dropping
    the worst benefit-per-byte selected index until feasible."""
    rng = np.random.default_rng(seed)
    n = problem.n_candidates
    sizes = problem.sizes

    def repair(mask: np.ndarray) -> np.ndarray:
        mask = mask.copy()
        while problem.total_size(mask) > problem.budget + 1e-9:
            chosen = np.where(mask)[0]
            # drop the selected index with the worst standalone benefit-per-byte
            standalone = (problem.weights[:, None] * problem.benefit[:, chosen]).sum(axis=0)
            worst = chosen[np.argmin(standalone / np.maximum(sizes[chosen], 1.0))]
            mask[worst] = False
        return mask

    cur = repair(greedy(problem).mask(n))
    cur_val = problem.workload_benefit(cur)
    best, best_val = cur.copy(), cur_val

    for it in range(iters):
        t = t0 * (t1 / t0) ** (it / max(iters - 1, 1))
        cand = cur.copy()
        cand[rng.integers(n)] ^= True
        cand = repair(cand)
        val = problem.workload_benefit(cand)
        if val >= cur_val or rng.random() < np.exp((val - cur_val) / max(t * abs(best_val or 1.0), 1e-9)):
            cur, cur_val = cand, val
            if val > best_val:
                best, best_val = cand.copy(), val

    return _finalize(problem, list(np.where(best)[0]), "anneal")
