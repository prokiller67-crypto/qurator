import type { ReactNode } from "react";

export function Panel({
  children,
  className = "",
  title,
  hint,
  accent,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  hint?: string;
  accent?: string;
}) {
  return (
    <section className={`panel p-5 ${className}`}>
      {title && (
        <div className="mb-4 flex items-baseline justify-between gap-3">
          <h2 className="text-sm font-semibold tracking-wide" style={{ color: accent }}>
            {title}
          </h2>
          {hint && <span className="text-[11px] text-[var(--text-faint)]">{hint}</span>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  sub,
  accent,
  big,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: string;
  big?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wider text-[var(--text-faint)]">{label}</span>
      <span
        className={`mono font-semibold leading-none ${big ? "text-3xl" : "text-xl"}`}
        style={{ color: accent ?? "var(--text)" }}
      >
        {value}
      </span>
      {sub && <span className="text-[11px] text-[var(--text-dim)]">{sub}</span>}
    </div>
  );
}

export function Tag({ children, color }: { children: ReactNode; color: string }) {
  return (
    <span
      className="chip"
      style={{ color, borderColor: `color-mix(in srgb, ${color} 40%, transparent)`, background: `color-mix(in srgb, ${color} 12%, transparent)` }}
    >
      {children}
    </span>
  );
}
