"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchArtifact } from "./api";
import type { Artifact, DistItem, Phase } from "./types";

// Replay timeline (seconds). The quantum phase is the long one — the search animates over it.
const T = {
  probing: 1.2,
  greedy: 1.4,
  quantum: 6.0,
  applying: 1.4,
};
const T_PROBING = T.probing;
const T_GREEDY = T_PROBING + T.greedy;
const T_QUANTUM = T_GREEDY + T.quantum;
const T_APPLYING = T_QUANTUM + T.applying;

export interface RunState {
  artifact: Artifact | null;
  loading: boolean;
  error: string | null;
  phase: Phase;
  quantumProgress: number; // 0..1 during quantum phase
  energyIndex: number; // index into qaoa.energies revealed so far
  currentDist: DistItem[]; // probability cloud snapshot to show right now
  isReplaying: boolean;
  run: () => void;
  reset: () => void;
  showDone: () => void;
}

export function useRun(): RunState {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [phase, setPhase] = useState<Phase>("idle");
  const [quantumProgress, setQuantumProgress] = useState(0);
  const [energyIndex, setEnergyIndex] = useState(0);
  const [currentDist, setCurrentDist] = useState<DistItem[]>([]);
  const [isReplaying, setIsReplaying] = useState(false);

  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);

  useEffect(() => {
    let alive = true;
    fetchArtifact()
      .then((a) => alive && (setArtifact(a), setLoading(false)))
      .catch((e) => alive && (setError(String(e.message ?? e)), setLoading(false)));
    return () => {
      alive = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const reset = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    setPhase("idle");
    setQuantumProgress(0);
    setEnergyIndex(0);
    setCurrentDist([]);
    setIsReplaying(false);
  }, []);

  // Jump straight to the final state (no animation) — used for deterministic headless screenshots.
  const showDone = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (!artifact) return;
    setPhase("done");
    setQuantumProgress(1);
    setEnergyIndex(artifact.qaoa.energies.length - 1);
    setCurrentDist(artifact.qaoa.final_distribution.slice(0, 6));
    setIsReplaying(false);
  }, [artifact]);

  const run = useCallback(() => {
    if (!artifact) return;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    const energies = artifact.qaoa.energies;
    const snaps = artifact.qaoa.prob_snapshots;
    setIsReplaying(true);
    startRef.current = performance.now();

    const tick = (now: number) => {
      const t = (now - startRef.current) / 1000;

      if (t < T_PROBING) {
        setPhase("probing");
      } else if (t < T_GREEDY) {
        setPhase("greedy");
      } else if (t < T_QUANTUM) {
        setPhase("quantum");
        const p = (t - T_GREEDY) / T.quantum;
        setQuantumProgress(p);
        const idx = Math.min(energies.length - 1, Math.floor(p * (energies.length - 1)));
        setEnergyIndex(idx);
        // show the most recent probability snapshot at or before this eval index
        let snap = snaps[0];
        for (const s of snaps) if (s.eval <= idx) snap = s;
        if (snap) setCurrentDist(snap.top);
      } else if (t < T_APPLYING) {
        setPhase("applying");
        setQuantumProgress(1);
        setEnergyIndex(energies.length - 1);
        setCurrentDist(artifact.qaoa.final_distribution.slice(0, 6));
      } else {
        setPhase("done");
        setQuantumProgress(1);
        setEnergyIndex(energies.length - 1);
        setCurrentDist(artifact.qaoa.final_distribution.slice(0, 6));
        setIsReplaying(false);
        return; // stop the loop
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [artifact]);

  return {
    artifact,
    loading,
    error,
    phase,
    quantumProgress,
    energyIndex,
    currentDist,
    isReplaying,
    run,
    reset,
    showDone,
  };
}
