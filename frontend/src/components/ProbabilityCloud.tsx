"use client";

import type { DistItem } from "@/lib/types";

interface Props {
  dist: DistItem[];
  optimalLabels: string[];
  collapsed: boolean; // true once converged (done/applying)
}

const sameSet = (a: string[], b: string[]) =>
  a.length === b.length && [...a].sort().join() === [...b].sort().join();

export default function ProbabilityCloud({ dist, optimalLabels, collapsed }: Props) {
  const items = [...dist].sort((a, b) => b.prob - a.prob).slice(0, 6);
  const maxP = Math.max(...items.map((d) => d.prob), 1e-9);

  if (items.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center text-sm text-[var(--text-faint)]">
        press <span className="q-text mx-1 font-semibold">RUN</span> to put every index combination into superposition
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {items.map((d, i) => {
        const isWinner = d.feasible && sameSet(d.labels, optimalLabels);
        const barColor = isWinner ? "var(--emerald)" : d.feasible ? "var(--cyan)" : "var(--rose)";
        const w = Math.max(4, (d.prob / maxP) * 100);
        return (
          <div key={i} className="rise" style={{ animationDelay: `${i * 30}ms` }}>
            <div className="mb-1 flex items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-1">
                {d.labels.length === 0 ? (
                  <span className="text-[11px] text-[var(--text-faint)]">∅ (no indexes)</span>
                ) : (
                  d.labels.map((l) => (
                    <span
                      key={l}
                      className="mono rounded px-1.5 py-0.5 text-[10px]"
                      style={{
                        background: isWinner ? "rgba(52,211,153,0.14)" : "rgba(255,255,255,0.05)",
                        color: isWinner ? "var(--emerald)" : "var(--text-dim)",
                      }}
                    >
                      {l}
                    </span>
                  ))
                )}
              </div>
              <div className="mono flex shrink-0 items-center gap-2 text-[10px]">
                {!d.feasible && <span style={{ color: "var(--rose)" }}>over-budget</span>}
                {isWinner && collapsed && <span style={{ color: "var(--emerald)" }}>★ optimum</span>}
                <span className="text-[var(--text-faint)]">p={d.prob.toFixed(3)}</span>
              </div>
            </div>
            <div className="h-2 overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,0.04)" }}>
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${w}%`,
                  background: barColor,
                  boxShadow: isWinner ? "0 0 12px -2px var(--emerald)" : "none",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
