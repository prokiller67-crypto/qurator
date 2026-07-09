import type { Artifact } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8088";

// When true (default in production), skip the live API and serve the bundled snapshot — so the deployed
// live-demo link works with no backend running.
const STATIC_ONLY = process.env.NEXT_PUBLIC_STATIC_ONLY === "1";

async function fetchStatic(): Promise<Artifact> {
  const res = await fetch("/demo_run.json", { cache: "force-cache" });
  if (!res.ok) throw new Error(`static artifact ${res.status}`);
  return (await res.json()) as Artifact;
}

export async function fetchArtifact(): Promise<Artifact> {
  if (STATIC_ONLY) return fetchStatic();
  try {
    const res = await fetch(`${API_BASE}/api/run`, { cache: "no-store" });
    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data as Artifact;
  } catch {
    // Backend unreachable → fall back to the bundled snapshot so the demo always renders.
    return fetchStatic();
  }
}

export const fmtMs = (ms: number) =>
  ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms.toFixed(0)}ms`;

export const fmtNum = (n: number) =>
  n.toLocaleString("en-US", { maximumFractionDigits: 0 });
