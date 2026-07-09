"use client";

import { useEffect, useRef } from "react";
import { useRun } from "@/lib/useRun";
import { fmtMs, fmtNum } from "@/lib/api";
import { Panel, Stat, Tag } from "@/components/ui";
import EnergyChart from "@/components/EnergyChart";
import ProbabilityCloud from "@/components/ProbabilityCloud";
import InteractionGraph from "@/components/InteractionGraph";
import LatencyBars from "@/components/LatencyBars";
import type { Phase } from "@/lib/types";

const PHASE_LABEL: Record<Phase, string> = {
  idle: "ready",
  probing: "measuring what-if costs (HypoPG)",
  greedy: "running greedy DBA heuristic",
  quantum: "QAOA searching superposition",
  applying: "applying indexes · re-benchmarking",
  done: "done",
};

const METHOD_COLOR: Record<string, string> = {
  greedy: "var(--amber)",
  anneal: "var(--blue)",
  exact: "var(--violet)",
  qaoa: "var(--emerald)",
};

export default function Home() {
  const r = useRun();
  const a = r.artifact;

  // ?autorun — auto-play the theater once the artifact is ready (used by the deployed demo link so judges
  // who open it see the search run itself, and for headless screenshots).
  const autorunFired = useRef(false);
  useEffect(() => {
    if (!a || autorunFired.current) return;
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("state") === "done") {
      autorunFired.current = true;
      r.showDone();
      return;
    }
    if (!params.has("autorun")) return;
    autorunFired.current = true;
    const t = setTimeout(r.run, 500);
    return () => clearTimeout(t);
  }, [a, r]);

  if (r.loading) return <Center>booting the quantum tuning advisor…</Center>;
  if (r.error || !a)
    return (
      <Center>
        <div className="text-center">
          <div className="mb-2" style={{ color: "var(--rose)" }}>backend unreachable</div>
          <div className="text-[12px] text-[var(--text-dim)]">{r.error}</div>
          <div className="mono mt-3 text-[11px] text-[var(--text-faint)]">
            start it with: <span className="text-[var(--cyan)]">uvicorn qurator.api:app --port 8088</span> · then
            <span className="text-[var(--cyan)]"> qurator cache</span>
          </div>
        </div>
      </Center>
    );

  const showGreedy = r.phase !== "idle" && r.phase !== "probing";
  const showResult = r.phase === "done";
  const q = a.qaoa;
  const s = a.solvers;
  const runLabel = r.isReplaying ? "running…" : r.phase === "done" ? "↻ replay" : "▶ run";

  return (
    <main className="mx-auto max-w-[1180px] px-5 py-6">
      {/* ---- header ---- */}
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-lg glow-violet" style={{ background: "var(--q-grad)" }}>
              <span className="text-lg font-bold text-black">Q</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Qurator</h1>
            <Tag color="var(--violet)">Quantum × Databases</Tag>
          </div>
          <p className="mt-1 text-[13px] text-[var(--text-dim)]">
            QAOA picks your Postgres indexes and makes real queries <span className="q-text font-semibold">measurably faster</span>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[11px] uppercase tracking-wider text-[var(--text-faint)]">status</div>
            <div className="mono text-[12px]" style={{ color: r.isReplaying ? "var(--cyan)" : "var(--text-dim)" }}>
              <span className={r.isReplaying ? "pulse" : ""}>●</span> {PHASE_LABEL[r.phase]}
            </div>
          </div>
          <button
            onClick={() => (r.phase === "done" ? (r.reset(), setTimeout(r.run, 60)) : r.run())}
            disabled={r.isReplaying}
            className="rounded-lg px-5 py-2.5 text-sm font-semibold text-black transition disabled:opacity-50"
            style={{ background: "var(--q-grad)" }}
          >
            {runLabel}
          </button>
        </div>
      </header>

      {/* ---- hero stats ---- */}
      <div className="panel mb-6 grid grid-cols-2 gap-6 p-5 sm:grid-cols-4 lg:grid-cols-5">
        <Stat label="workload" value={`${a.workload.length} queries`} sub={`baseline ${fmtMs(a.headline?.baseline_weighted_ms ?? 0)}`} />
        <Stat label="candidate indexes" value={a.meta.n_candidates_total} sub={`${a.meta.n_candidates_active} active → qubits`} />
        <Stat label="storage budget" value={`${a.meta.budget_mb} MB`} sub={`of ${a.meta.total_candidate_mb} MB possible`} />
        <Stat label="search space" value={`2^${a.meta.n_qubits}`} sub={`${fmtNum(Math.pow(2, a.meta.n_qubits))} combos`} accent="var(--violet)" />
        <Stat
          label={showResult ? "quantum result" : "target"}
          value={showResult ? fmtMs(a.headline?.optimum_weighted_ms ?? 0) : "—"}
          sub={showResult ? `${a.headline?.speedup}× faster` : "press run"}
          accent="var(--emerald)"
          big={showResult}
        />
      </div>

      {/* ---- problem + candidates ---- */}
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <Panel title="THE WORKLOAD" hint="dashboard + fraud-scan queries" accent="var(--cyan)">
          <div className="flex flex-col divide-y divide-[var(--border-soft)]">
            {a.workload.map((wq) => (
              <div key={wq.id} className="flex items-start justify-between gap-3 py-2">
                <div>
                  <div className="mono text-[13px]">{wq.id}</div>
                  <div className="text-[11px] text-[var(--text-faint)]">{wq.note}</div>
                </div>
                <Tag color="var(--text-dim)">×{wq.weight}</Tag>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="CANDIDATE INDEXES" hint={`${a.meta.n_candidates_active} help the workload`} accent="var(--cyan)">
          <div className="max-h-[360px] overflow-y-auto pr-1">
            <table className="w-full text-left text-[12px]">
              <thead className="sticky top-0 z-10 text-[var(--text-faint)]" style={{ background: "var(--bg-panel)" }}>
                <tr>
                  <th className="pb-2 font-medium">index</th>
                  <th className="pb-2 text-right font-medium">MB</th>
                  <th className="pb-2 text-right font-medium">benefit</th>
                </tr>
              </thead>
              <tbody className="mono">
                {a.candidates.map((c) => {
                  const active = a.active_candidates.includes(c.id);
                  const inQ = showResult && s.qaoa.selected.includes(c.id);
                  const inG = showGreedy && s.greedy.selected.includes(c.id);
                  return (
                    <tr key={c.id} className="border-t border-[var(--border-soft)]" style={{ opacity: active ? 1 : 0.4 }}>
                      <td className="py-1.5">
                        <span style={{ color: inQ ? "var(--emerald)" : inG ? "var(--amber)" : "var(--text-dim)" }}>{c.label}</span>
                        {inQ && <span className="ml-1" style={{ color: "var(--emerald)" }}>★</span>}
                      </td>
                      <td className="py-1.5 text-right text-[var(--text-faint)]">{c.size_mb.toFixed(0)}</td>
                      <td className="py-1.5 text-right" style={{ color: c.total_benefit > 0 ? "var(--text)" : "var(--text-faint)" }}>
                        {c.total_benefit > 0 ? fmtNum(c.total_benefit) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      {/* ---- the theater ---- */}
      <Panel className="mb-6" title="⚛ OPTIMIZATION THEATER" hint={`${q.n_qubits}-qubit QAOA · p=${q.reps} · ${q.n_evals} circuit evals`} accent="var(--violet)">
        <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          <div className="flex flex-col gap-4">
            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wider text-[var(--text-faint)]">energy convergence ⟨H⟩</div>
              <EnergyChart energies={q.energies} revealed={r.energyIndex} reps={q.reps} />
            </div>
            <div>
              <div className="mb-1 text-[11px] uppercase tracking-wider text-[var(--text-faint)]">
                index-interaction graph {showResult && <span style={{ color: "var(--emerald)" }}>· quantum picks the hubs</span>}
              </div>
              <InteractionGraph
                active={a.active_candidates}
                candidates={a.candidates}
                edges={a.interaction_edges}
                greedy={s.greedy.selected}
                quantum={s.qaoa.selected}
                showSelection={showResult}
              />
            </div>
          </div>
          <div>
            <div className="mb-1 text-[11px] uppercase tracking-wider text-[var(--text-faint)]">
              probability cloud {r.phase === "quantum" ? "· collapsing…" : showResult ? "· collapsed" : ""}
            </div>
            <ProbabilityCloud dist={r.currentDist} optimalLabels={s.exact.selected} collapsed={r.phase === "done" || r.phase === "applying"} />
            {showResult && (
              <div className="mono mt-4 rounded-lg border border-[var(--border-soft)] p-3 text-[12px]">
                {q.matches_exact ? (
                  <span style={{ color: "var(--emerald)" }}>✓ QAOA recovered the exact optimum ({q.n_qubits} qubits) — verified against brute-force.</span>
                ) : (
                  <span style={{ color: "var(--amber)" }}>QAOA reached {s.qaoa.pct_of_optimum}% of the exact optimum.</span>
                )}
              </div>
            )}
          </div>
        </div>
      </Panel>

      {/* ---- results ---- */}
      {showResult && a.latency && a.headline && (
        <div className="mb-6 grid gap-6 lg:grid-cols-[1fr_1.15fr]">
          <Panel title="THE REVEAL · REAL MEASURED LATENCY" accent="var(--emerald)">
            <LatencyBars latency={a.latency} headline={a.headline} workload={a.workload} reveal={showResult} />
          </Panel>

          <Panel title="HONESTY PANEL · quantum vs classical" accent="var(--violet)">
            <div className="flex flex-col gap-3">
              {(["greedy", "anneal", "exact", "qaoa"] as const).map((k) => {
                const sol = s[k];
                return (
                  <div key={k}>
                    <div className="mb-1 flex items-center justify-between text-[12px]">
                      <span className="font-semibold" style={{ color: METHOD_COLOR[k] }}>
                        {k === "qaoa" ? "QAOA (quantum)" : k === "exact" ? "exact optimum" : k === "anneal" ? "simulated annealing" : "greedy DBA"}
                      </span>
                      <span className="mono text-[var(--text-dim)]">{sol.pct_of_optimum}% · {sol.size_mb}MB</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,0.04)" }}>
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${sol.pct_of_optimum}%`, background: METHOD_COLOR[k] }} />
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="mt-4 text-[11px] leading-relaxed text-[var(--text-faint)]">
              At {q.n_qubits} qubits a classical solver still matches QAOA — so this is a{" "}
              <span className="text-[var(--text-dim)]">correct, principled pipeline and an honest demonstration</span>, not a speedup claim. The value is a real formulation that plugs straight into scaling quantum hardware.
            </p>
          </Panel>
        </div>
      )}

      {/* ---- footer ---- */}
      <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border-soft)] pt-5 text-[11px] text-[var(--text-faint)]">
        <div>Postgres 16 + HypoPG · QUBO · QAOA (Qiskit Aer) · FastAPI · Next.js</div>
        <div>lineage: Trummer &amp; Koch (VLDB&apos;16) · Schönberger &amp; Mauerer (SIGMOD&apos;22–23)</div>
      </footer>
    </main>
  );
}

function Center({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="text-[13px] text-[var(--text-dim)]">{children}</div>
    </main>
  );
}
