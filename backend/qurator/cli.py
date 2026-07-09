"""Qurator command line — seed, probe, and solve the index-selection problem."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from .costprobe import probe as run_probe
from .solvers import classical

app = typer.Typer(add_completion=False, help="Qurator — quantum index tuning advisor.")
console = Console()


@app.command()
def seed(
    transactions: int = typer.Option(None, help="number of transactions (default from env/config)"),
) -> None:
    """Seed the demo fintech dataset."""
    from .seed import seed as run_seed

    run_seed(n_transactions=transactions)


@app.command()
def probe(budget_mb: float = typer.Option(None, help="storage budget in MB (default 35% of total)")) -> None:
    """Measure candidate index benefits with HypoPG and print the problem."""
    result = run_probe(budget_mb=budget_mb)
    rep = result.report()

    t = Table(title="Candidate indexes (HypoPG what-if)", show_lines=False)
    t.add_column("#", justify="right")
    t.add_column("candidate")
    t.add_column("size MB", justify="right")
    t.add_column("Σ weighted benefit", justify="right")
    t.add_column("helps")
    for i, c in enumerate(rep["candidates"]):
        t.add_row(str(i), c["label"], f"{c['size_mb']:.1f}", f"{c['total_benefit']:,.0f}",
                  ", ".join(c["helps"]) or "—")
    console.print(t)
    console.print(f"[cyan]budget: {rep['budget_mb']:.1f} MB[/]  "
                  f"(total candidate size {sum(c['size_mb'] for c in rep['candidates']):.1f} MB)")


@app.command()
def solve(
    budget_mb: float = typer.Option(None, help="storage budget in MB (default 35% of total)"),
    anneal_iters: int = typer.Option(40_000, help="simulated-annealing iterations"),
) -> None:
    """Run classical baselines (greedy vs exact vs simulated annealing) and compare."""
    result = run_probe(budget_mb=budget_mb)
    problem = result.problem

    g = classical.greedy(problem)
    x = classical.exact(problem)
    a = classical.simulated_annealing(problem, iters=anneal_iters)

    baseline = problem.baseline_workload_cost()

    t = Table(title="Solver comparison", show_lines=True)
    t.add_column("method")
    t.add_column("selected indexes")
    t.add_column("size MB", justify="right")
    t.add_column("Σ benefit", justify="right")
    t.add_column("residual cost", justify="right")
    t.add_column("% of optimum", justify="right")
    for sol in (g, a, x):
        pct = 100.0 * sol.benefit / x.benefit if x.benefit else 0.0
        t.add_row(
            sol.method,
            ", ".join(sol.labels),
            f"{sol.size/1e6:.1f}",
            f"{sol.benefit:,.0f}",
            f"{baseline - sol.benefit:,.0f}",
            f"{pct:.1f}%",
        )
    console.print(t)

    gap = x.benefit - g.benefit
    if gap > 1e-6:
        console.print(
            f"\n[bold green]✓ greedy is SUB-OPTIMAL[/]: exact beats greedy by "
            f"[bold]{gap:,.0f}[/] benefit units ({100*gap/x.benefit:.1f}%). "
            f"Greedy picked {g.labels}; optimum is {x.labels}."
        )
    else:
        console.print("\n[yellow]greedy matched exact on this instance — tune budget/candidates for a gap.[/]")


@app.command()
def bench(
    budget_mb: float = typer.Option(None, help="storage budget in MB (default: demo budget)"),
    runs: int = typer.Option(3, help="measured runs per query (median)"),
) -> None:
    """Apply greedy vs exact index sets for real and measure the actual latency drop."""
    from .apply import benchmark_config
    from .workload import WORKLOAD

    result = run_probe(budget_mb=budget_mb)
    problem = result.problem
    g = classical.greedy(problem)
    x = classical.exact(problem)
    console.log(f"greedy: {g.labels}")
    console.log(f"exact : {x.labels}")

    base = benchmark_config([], "baseline", runs=runs)
    gb = benchmark_config(g.labels, "greedy", runs=runs)
    xb = benchmark_config(x.labels, "exact/quantum", runs=runs)

    t = Table(title="Real measured latency", show_lines=False)
    t.add_column("query")
    t.add_column("baseline", justify="right")
    t.add_column("greedy", justify="right")
    t.add_column("exact/quantum", justify="right")
    for q in WORKLOAD:
        t.add_row(q.id, f"{base.per_query_ms[q.id]:.1f}ms", f"{gb.per_query_ms[q.id]:.1f}ms",
                  f"{xb.per_query_ms[q.id]:.1f}ms")
    t.add_row("TOTAL (weighted)", f"{base.weighted_ms:.0f}ms", f"{gb.weighted_ms:.0f}ms",
              f"{xb.weighted_ms:.0f}ms", style="bold")
    console.print(t)
    console.print(
        f"[bold green]baseline → optimum: {base.weighted_ms/xb.weighted_ms:.1f}× faster[/]  |  "
        f"greedy is {gb.weighted_ms/xb.weighted_ms:.2f}× slower than the quantum-selected set (same budget)"
    )


@app.command()
def quantum(
    budget_mb: float = typer.Option(None, help="storage budget in MB (default: demo budget)"),
    reps: int = typer.Option(4, help="QAOA layers (p)"),
) -> None:
    """Run the full quantum pipeline (probe → QUBO → QAOA) and compare to classical baselines."""
    from .pipeline import run_pipeline

    art = run_pipeline(budget_mb=budget_mb, with_latency=False, reps=reps)
    s = art["solvers"]
    t = Table(title=f"Quantum vs classical  ({art['meta']['n_qubits']} qubits, budget {art['meta']['budget_mb']}MB)")
    t.add_column("method"); t.add_column("selected"); t.add_column("size MB", justify="right")
    t.add_column("benefit", justify="right"); t.add_column("% optimum", justify="right")
    for key in ("greedy", "anneal", "exact", "qaoa"):
        sol = s[key]
        t.add_row(key, ", ".join(sol["selected"]), f"{sol['size_mb']:.1f}",
                  f"{sol['benefit']:,.0f}", f"{sol['pct_of_optimum']:.1f}%")
    console.print(t)
    q = art["qaoa"]
    verdict = "✓ QAOA matched the exact optimum" if q["matches_exact"] else "✗ QAOA below exact"
    console.print(f"[bold]{verdict}[/]  ({q['n_evals']} circuit evals, energy → {q['optimal_value']})")


@app.command()
def reset() -> None:
    """Drop all Qurator-created indexes (qur_*) — restores the clean baseline."""
    from .apply import drop_qurator_indexes
    from .db import connect

    with connect() as conn, conn.cursor() as cur:
        drop_qurator_indexes(cur)
        cur.execute("ANALYZE")
    console.print("[green]dropped all qur_* indexes — baseline restored.")


@app.command()
def cache(
    budget_mb: float = typer.Option(None, help="storage budget in MB (default: demo budget)"),
    reps: int = typer.Option(4, help="QAOA layers (p)"),
) -> None:
    """Run the full pipeline WITH real latency and cache the artifact for a stable demo."""
    from .pipeline import cache_run

    path = cache_run(budget_mb=budget_mb, reps=reps)
    console.print(f"[green]cached demo run → {path}")


if __name__ == "__main__":
    app()
