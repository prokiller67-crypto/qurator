"use client";

interface Props {
  energies: number[];
  revealed: number; // index revealed so far
  reps: number;
}

const W = 560;
const H = 220;
const PAD = { l: 44, r: 16, t: 16, b: 26 };

export default function EnergyChart({ energies, revealed }: Props) {
  if (energies.length === 0) return null;
  const min = Math.min(...energies);
  const max = Math.max(...energies);
  const span = max - min || 1;
  const n = energies.length;

  const x = (i: number) => PAD.l + (i / (n - 1)) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - (v - min) / span) * (H - PAD.t - PAD.b);

  const shown = Math.max(1, revealed);
  const pts = energies.slice(0, shown + 1).map((v, i) => `${x(i)},${y(v)}`).join(" ");
  const headI = Math.min(shown, n - 1);
  const headV = energies[headI];

  const gridY = [0, 0.25, 0.5, 0.75, 1].map((f) => min + f * span);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 240 }}>
      <defs>
        <linearGradient id="egrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--violet)" />
          <stop offset="100%" stopColor="var(--cyan)" />
        </linearGradient>
        <linearGradient id="efill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(139,92,246,0.22)" />
          <stop offset="100%" stopColor="rgba(34,211,238,0.02)" />
        </linearGradient>
      </defs>

      {gridY.map((v, i) => (
        <g key={i}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="var(--border-soft)" strokeWidth={1} />
          <text x={PAD.l - 8} y={y(v) + 3} textAnchor="end" fontSize={9} fill="var(--text-faint)" className="mono">
            {v.toFixed(1)}
          </text>
        </g>
      ))}

      {/* area under revealed curve */}
      {shown > 1 && (
        <polygon
          points={`${x(0)},${H - PAD.b} ${pts} ${x(headI)},${H - PAD.b}`}
          fill="url(#efill)"
        />
      )}
      <polyline points={pts} fill="none" stroke="url(#egrad)" strokeWidth={2.2} strokeLinejoin="round" />

      {/* moving head */}
      <circle cx={x(headI)} cy={y(headV)} r={4.5} fill="var(--cyan)" className="glow-emerald" />
      <circle cx={x(headI)} cy={y(headV)} r={9} fill="none" stroke="var(--cyan)" strokeWidth={1} opacity={0.4} className="pulse" />

      <text x={PAD.l} y={H - 8} fontSize={9} fill="var(--text-faint)" className="mono">
        circuit evaluations →
      </text>
      <text x={W - PAD.r} y={H - 8} textAnchor="end" fontSize={9} fill="var(--text-faint)" className="mono">
        ⟨H⟩ energy
      </text>
    </svg>
  );
}
