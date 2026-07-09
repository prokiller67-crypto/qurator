"""Qurator HTTP + WebSocket API.

  GET  /api/health           liveness
  GET  /api/run              the full cached RunArtifact (everything the frontend renders)
  GET  /api/run/live         recompute the pipeline live (slow; optional ?budget_mb=&reps=)
  WS   /ws/replay            stream the QAOA search as timed frames (deterministic → demo-safe theater)

The WebSocket replays the CACHED run by default, so the "optimization theater" animation is smooth and
identical every time on stage. A live recompute is available for the brave.
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .pipeline import load_cached_run, run_pipeline

app = FastAPI(title="Qurator API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",  # any local dev port
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    cached = load_cached_run() is not None
    return {"status": "ok", "cached_run_available": cached}


@app.get("/api/run")
def get_run() -> dict:
    art = load_cached_run()
    if art is None:
        return {"error": "no cached run — run `qurator cache` first"}
    return art


@app.get("/api/run/live")
def get_run_live(budget_mb: float | None = None, reps: int = 4, with_latency: bool = True) -> dict:
    return run_pipeline(budget_mb=budget_mb, with_latency=with_latency, reps=reps)


async def _send(ws: WebSocket, payload: dict) -> None:
    await ws.send_json(payload)


@app.websocket("/ws/replay")
async def replay(ws: WebSocket) -> None:
    """Replay the cached QAOA search as a paced sequence of frames for the theater animation."""
    await ws.accept()
    art = load_cached_run()
    if art is None:
        await _send(ws, {"type": "error", "message": "no cached run"})
        await ws.close()
        return

    try:
        await _send(ws, {"type": "meta", "meta": art["meta"], "workload": art["workload"]})
        await asyncio.sleep(0.3)
        await _send(ws, {"type": "candidates", "candidates": art["candidates"],
                         "active": art["active_candidates"], "edges": art["interaction_edges"]})
        await asyncio.sleep(0.4)
        await _send(ws, {"type": "greedy", "solution": art["solvers"]["greedy"]})
        await asyncio.sleep(0.6)

        # QAOA convergence — downsample energies to ~60 frames, attach probability snapshots by eval index.
        energies = art["qaoa"]["energies"]
        snaps = {s["eval"]: s for s in art["qaoa"]["prob_snapshots"]}
        n = len(energies)
        frames = 60
        step = max(1, n // frames)
        await _send(ws, {"type": "qaoa_start", "n_qubits": art["qaoa"]["n_qubits"],
                         "reps": art["qaoa"]["reps"], "n_evals": n})
        for i in range(0, n, step):
            frame = {"type": "qaoa_step", "i": i, "energy": energies[i]}
            if i in snaps:
                frame["top"] = snaps[i]["top"]
            await _send(ws, frame)
            await asyncio.sleep(0.06)

        await _send(ws, {"type": "qaoa_done",
                         "final_distribution": art["qaoa"]["final_distribution"],
                         "matches_exact": art["qaoa"]["matches_exact"],
                         "solution": art["solvers"]["qaoa"]})
        await asyncio.sleep(0.4)
        await _send(ws, {"type": "result",
                         "solvers": art["solvers"],
                         "latency": art.get("latency"),
                         "headline": art.get("headline")})
    except WebSocketDisconnect:
        return
    finally:
        try:
            await ws.close()
        except RuntimeError:
            pass
