export interface Candidate {
  id: string;
  label: string;
  size_bytes: number;
  size_mb: number;
  total_benefit: number;
  helps: string[];
}

export interface WorkloadQuery {
  id: string;
  weight: number;
  note: string;
  baseline_cost: number;
}

export interface Solution {
  method: string;
  selected: string[];
  selected_detail: { id: string; label: string }[];
  size_mb: number;
  benefit: number;
  pct_of_optimum: number;
  residual_cost: number;
}

export interface DistItem {
  labels: string[];
  prob: number;
  size_mb: number;
  benefit: number;
  feasible: boolean;
}

export interface ProbSnapshot {
  eval: number;
  reps: number;
  energy: number;
  top: DistItem[];
}

export interface Edge {
  source: string;
  target: string;
  weight: number;
}

export interface LatencyCfg {
  per_query_ms: Record<string, number>;
  total_ms: number;
  weighted_ms: number;
  build_ms: number;
  applied: string[];
}

export interface Headline {
  baseline_weighted_ms: number;
  optimum_weighted_ms: number;
  greedy_weighted_ms: number;
  speedup: number;
  greedy_slowdown: number;
}

export interface Artifact {
  generated_at: string;
  meta: {
    budget_mb: number;
    total_candidate_mb: number;
    n_candidates_total: number;
    n_candidates_active: number;
    n_qubits: number;
    baseline_workload_cost: number;
  };
  workload: WorkloadQuery[];
  candidates: Candidate[];
  active_candidates: string[];
  interaction_edges: Edge[];
  solvers: { greedy: Solution; anneal: Solution; exact: Solution; qaoa: Solution };
  qaoa: {
    n_qubits: number;
    reps: number;
    n_evals: number;
    optimal_value: number;
    matches_exact: boolean;
    energies: number[];
    prob_snapshots: ProbSnapshot[];
    final_distribution: DistItem[];
  };
  latency?: Record<string, LatencyCfg>;
  headline?: Headline;
}

export type Phase = "idle" | "probing" | "greedy" | "quantum" | "applying" | "done";
