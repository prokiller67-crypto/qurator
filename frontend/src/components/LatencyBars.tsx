"use client";

import { fmtMs } from "@/lib/api";
import type { Headline, LatencyCfg, WorkloadQuery } from "@/lib/types";

interface Props {
  latency: Record<string, LatencyCfg>;
  headline: Headline;
  workload: WorkloadQuery[];
  reveal: boolean;
}

export default function LatencyBars({ latency, headline, workload, reveal }: Props) {
  const base = latency["baseline"];
  const greedy = latency["greedy"];
  const quantum = latency["exact/quantum"];
  if (!base || !quantum) return null;

  const maxMs = base.weighted_ms;
  const bars = [
    { key: "baseline", label: "No indexes", cfg: base, color: "var(--rose)" },
    { key: "greedy", label: "Greedy DBA", cfg: greedy, color: "var(--amber)" },
    { key: "quantum", label: "Quantum-selected", cfg: quantum, color: "var(--emerald)" },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-3 items-end gap-4" style={{ minHeight: 200 }}>
        {bars.map((b) => {
          const h = reveal ? Math.max(6, (b.cfg.weighted_ms / maxMs) * 170) : 6;
          return (
            <div key={b.key} className="flex flex-col items-center justify-end gap-2">
              <span className="mono text-lg font-semibold" style={{ color: b.color }}>
                {reveal ? fmtMs(b.cfg.weighted_ms) : "—"}
              </span>
              <div
                className="w-full rounded-t-lg transition-all duration-[900ms] ease-out"
                style={{
                  height: h,
                  background: `linear-gradient(to top, ${b.color}, color-mix(in srgb, ${b.color} 45%, transparent))`,
                  boxShadow: b.key === "quantum" ? "0 0 24px -6px var(--emerald)" : "none",
                }}
              />
              <span className="text-center text-[11px] text-[var(--text-dim)]">{b.label}</span>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 border-t border-[var(--border-soft)] pt-4">
        <div className="text-center">
          <div className="q-text mono text-3xl font-bold">{headline.speedup}×</div>
          <div className="text-[11px] text-[var(--text-dim)]">faster than unindexed</div>
        </div>
        <div className="text-center">
          <div className="mono text-3xl font-bold" style={{ color: "var(--amber)" }}>
            {headline.greedy_slowdown}×
          </div>
          <div className="text-[11px] text-[var(--text-dim)]">greedy is slower — same budget</div>
        </div>
      </div>

      {/* per-query breakdown */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[12px]">
          <thead className="text-[var(--text-faint)]">
            <tr>
              <th className="pb-2 font-medium">query</th>
              <th className="pb-2 text-right font-medium">no indexes</th>
              <th className="pb-2 text-right font-medium">quantum</th>
              <th className="pb-2 text-right font-medium">speedup</th>
            </tr>
          </thead>
          <tbody className="mono">
            {workload.map((q) => {
              const b = base.per_query_ms[q.id] ?? 0;
              const s = quantum.per_query_ms[q.id] ?? 0;
              const x = s > 0 ? b / s : 0;
              return (
                <tr key={q.id} className="border-t border-[var(--border-soft)]">
                  <td className="py-1.5 text-[var(--text-dim)]">{q.id}</td>
                  <td className="py-1.5 text-right" style={{ color: "var(--rose)" }}>{b.toFixed(1)}ms</td>
                  <td className="py-1.5 text-right" style={{ color: "var(--emerald)" }}>{s.toFixed(1)}ms</td>
                  <td className="py-1.5 text-right text-[var(--text)]">{reveal ? `${x.toFixed(1)}×` : ""}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
