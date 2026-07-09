"""HypoPG Cost Probe — turn a live database + workload into an IndexProblem.

For each candidate we register it as a *hypothetical* index (HypoPG), re-EXPLAIN every query, and record the
estimated cost reduction. Nothing is built on disk, so probing ~21 candidates × 8 queries is a few hundred
cheap EXPLAINs — sub-second. The resulting benefit matrix + estimated index sizes define the optimization.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from rich.console import Console

from .candidates import CANDIDATES, Candidate
from .db import connect, explain_cost, hypo_create, hypo_reset, hypo_size_bytes
from .model import IndexProblem
from .workload import WORKLOAD

console = Console()


@dataclass
class ProbeResult:
    problem: IndexProblem
    candidates: list[Candidate]
    baseline_cost: np.ndarray       # (Nq,)
    benefit: np.ndarray             # (Nq, Nc)
    sizes: np.ndarray               # (Nc,) bytes

    def report(self) -> dict:
        c = self.candidates
        q = WORKLOAD
        return {
            "queries": [{"id": qq.id, "weight": qq.weight, "baseline_cost": float(self.baseline_cost[j])}
                        for j, qq in enumerate(q)],
            "candidates": [
                {
                    "id": cc.id, "label": cc.label, "size_bytes": int(self.sizes[i]),
                    "size_mb": round(self.sizes[i] / 1e6, 2),
                    "total_benefit": float((np.asarray([qq.weight for qq in q]) * self.benefit[:, i]).sum()),
                    "helps": [q[j].id for j in range(len(q)) if self.benefit[j, i] > 0],
                }
                for i, cc in enumerate(c)
            ],
            "budget_bytes": int(self.problem.budget),
            "budget_mb": round(self.problem.budget / 1e6, 2),
        }


def probe(budget_mb: float | None = None, budget_frac: float | None = None) -> ProbeResult:
    cands = CANDIDATES
    nq, nc = len(WORKLOAD), len(cands)
    baseline = np.zeros(nq)
    benefit = np.zeros((nq, nc))
    sizes = np.zeros(nc)
    weights = np.array([q.weight for q in WORKLOAD], dtype=float)

    with connect() as conn, conn.cursor() as cur:
        hypo_reset(cur)
        console.log("probing baseline costs (no indexes)…")
        for j, q in enumerate(WORKLOAD):
            baseline[j] = explain_cost(cur, q.sql)

        console.log(f"probing {nc} candidates × {nq} queries via HypoPG…")
        for i, cand in enumerate(cands):
            hypo_reset(cur)
            relid, _name = hypo_create(cur, cand.create_sql(hypothetical=True))
            sizes[i] = hypo_size_bytes(cur, relid)
            for j, q in enumerate(WORKLOAD):
                cost_with = explain_cost(cur, q.sql)
                benefit[j, i] = max(0.0, baseline[j] - cost_with)
            hypo_reset(cur)

    total_size = sizes.sum()
    if budget_mb is not None:
        budget = budget_mb * 1e6
    elif budget_frac is not None:
        budget = budget_frac * total_size
    else:
        from .config import settings
        budget = settings.demo_budget_mb * 1e6

    problem = IndexProblem(
        candidate_ids=[c.id for c in cands],
        query_ids=[q.id for q in WORKLOAD],
        weights=weights, benefit=benefit, sizes=sizes, budget=budget, baseline_cost=baseline,
    )
    console.log(
        f"[green]probe done. total candidate size={total_size/1e6:.1f}MB  budget={budget/1e6:.1f}MB "
        f"({100*budget/total_size:.0f}%)"
    )
    return ProbeResult(problem, list(cands), baseline, benefit, sizes)
