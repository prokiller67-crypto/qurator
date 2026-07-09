# Deploying Qurator

The submission needs a **live demo link**. The fastest, most reliable path deploys the frontend alone — it
bundles the demo artifact, so it needs no backend.

## Option A — Frontend-only on Vercel (recommended for the live demo link)

The frontend ships `public/demo_run.json` (the real pipeline output). With `NEXT_PUBLIC_STATIC_ONLY=1` it renders
the entire experience — theater, probability cloud, latency reveal — with **no server**.

1. Push the repo to GitHub.
2. On Vercel: **New Project** → import the repo → set **Root Directory = `frontend`**.
3. Environment variable: `NEXT_PUBLIC_STATIC_ONLY = 1`.
4. Deploy. Share the URL — append `?autorun=1` so it auto-plays the search for judges:
   `https://<your-app>.vercel.app/?autorun=1`

To refresh the demo data: `make cache` (regenerates `frontend/public/demo_run.json`) and redeploy.

## Option B — Full stack (live runs)

For genuinely live probing/QAOA you need the backend + a Postgres with HypoPG.

**Backend** (FastAPI + Qiskit) — container, e.g. Fly.io or Render:
```bash
docker build -t qurator-backend ./backend
# deploy the image; set QURATOR_PG_* to point at your database
```
The image serves the cached artifact out of the box and runs the live pipeline when the DB is reachable.

**Database** — Postgres 16 with the HypoPG extension. The `db/` image builds it; host it anywhere that allows
custom extensions (a VM running the `db/Dockerfile`, or any managed Postgres that permits `CREATE EXTENSION
hypopg`). Then seed: `QURATOR_PG_HOST=… make seed`.

**Frontend** — set `NEXT_PUBLIC_STATIC_ONLY=0` and `NEXT_PUBLIC_API_URL=https://<backend-url>`; it calls the live
API and falls back to the bundled snapshot if the backend is unreachable.

## Local full stack in one command
```bash
make up      # db + backend API in Docker
make dev     # frontend
```

## Devpost submission checklist
- [x] GitHub repository (this repo)
- [x] Description + problem/impact writeup → `docs/SUBMISSION.md`
- [x] Screenshots → `docs/screenshot-hero.png`, `docs/screenshot-full.png`
- [x] Technologies used → see README
- [x] Installation instructions → README “Quickstart”
- [ ] Live demo link → Option A above
- [ ] 2–5 min demo video → shot list in `PLAN.md` (“The winning demo”)
