"use client";

import type { Candidate, Edge } from "@/lib/types";

interface Props {
  active: string[];
  candidates: Candidate[];
  edges: Edge[];
  greedy: string[];
  quantum: string[];
  showSelection: boolean;
}

const W = 440;
const H = 360;

export default function InteractionGraph({ active, candidates, edges, greedy, quantum, showSelection }: Props) {
  const byId = new Map(candidates.map((c) => [c.id, c]));
  const N = active.length;
  const cx = W / 2;
  const cy = H / 2;
  const R = 138;

  const pos = new Map<string, { x: number; y: number }>();
  active.forEach((id, i) => {
    const a = (2 * Math.PI * i) / N - Math.PI / 2;
    pos.set(id, { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) });
  });

  const maxBenefit = Math.max(...active.map((id) => byId.get(id)?.total_benefit ?? 0), 1);
  const maxW = Math.max(...edges.map((e) => e.weight), 1);

  const nodeColor = (id: string) => {
    if (!showSelection) return "var(--text-faint)";
    const inQ = quantum.includes(id);
    const inG = greedy.includes(id);
    if (inQ) return "var(--emerald)";
    if (inG) return "var(--amber)";
    return "var(--text-faint)";
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 380 }}>
      {edges.map((e, i) => {
        const a = pos.get(e.source);
        const b = pos.get(e.target);
        if (!a || !b) return null;
        const op = 0.06 + 0.5 * (e.weight / maxW);
        return (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="var(--violet)"
            strokeOpacity={op}
            strokeWidth={0.5 + 2.5 * (e.weight / maxW)}
          />
        );
      })}
      {active.map((id) => {
        const p = pos.get(id)!;
        const c = byId.get(id);
        const r = 6 + 12 * Math.sqrt((c?.total_benefit ?? 0) / maxBenefit);
        const color = nodeColor(id);
        const selected = showSelection && (quantum.includes(id) || greedy.includes(id));
        return (
          <g key={id}>
            <circle
              cx={p.x}
              cy={p.y}
              r={r}
              fill={color}
              fillOpacity={selected ? 0.9 : 0.28}
              stroke={color}
              strokeWidth={selected ? 2 : 1}
              style={selected && quantum.includes(id) ? { filter: "drop-shadow(0 0 6px var(--emerald))" } : undefined}
            />
            <text
              x={p.x}
              y={p.y - r - 4}
              textAnchor="middle"
              fontSize={8}
              fill={selected ? color : "var(--text-faint)"}
              className="mono"
            >
              {id.replace(/^txn_/, "").replace(/^led_/, "L·").replace(/^mer_/, "M·")}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
