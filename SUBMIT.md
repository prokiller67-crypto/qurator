# Qurator — how to submit (video + Devpost)

Everything technical is done and live. This is the step-by-step to finish the submission.

## Status

| Deliverable | Done? | Link / file |
|---|---|---|
| Live demo | ✅ | https://qurator-inky.vercel.app/?autorun=1 |
| GitHub repo | ✅ | https://github.com/prokiller67-crypto/qurator |
| Description / problem / impact text | ✅ | `docs/SUBMISSION.md` (copy-paste into Devpost) |
| Screenshots | ✅ | `docs/screenshot-hero.png`, `docs/screenshot-full.png` |
| Technologies + install instructions | ✅ | `README.md` |
| **2–5 min demo video** | ⬜ | **you record it — steps below** |
| Devpost form filled + submitted | ⬜ | steps below |

Deadline: **Aug 20, 2026, 5pm PDT** — no rush.

---

## 1. Record the demo video (2–5 min)

**Record with:** macOS QuickTime (`Cmd+Shift+5` → Record Selected/Entire Screen) or [Loom](https://loom.com) (easiest — records screen + your voice + webcam bubble and gives a shareable link instantly).

**Setup:**
1. Open the demo full-screen: `https://qurator-inky.vercel.app` (do NOT add `?autorun=1` — you want to click **run** yourself for timing).
2. Start recording. Speak clearly. Aim for **~3 minutes**.

**Beat-by-beat script** (numbers match the live demo):

- **0:00–0:30 — the problem.** *"This is a live fintech Postgres — 2 million transactions. These 8 dashboard and fraud-scan queries take 1.9 seconds. A DBA has to choose which indexes to build — 21 candidates, a 250 MB storage budget, over 32,000 combinations, and the indexes interfere with each other. This is NP-hard."* (Point at the WORKLOAD and CANDIDATE INDEXES panels.)
- **0:30–1:00 — the workbench.** *"Qurator measures each index's real benefit with HypoPG — no index is built yet."* (Point at the benefit column.) *"A greedy DBA heuristic grabs the cheap single-column indexes."*
- **1:00–2:00 — quantum solve.** Hit **▶ run**. *"Qurator puts all 32,000 combinations into superposition and runs QAOA — a real quantum circuit, 15 qubits, on Qiskit."* Narrate the **energy convergence** dropping, the **probability cloud** collapsing, the **interaction graph**. *"The cloud collapses onto one winning index set."*
- **2:00–2:45 — the reveal.** Scroll to **THE REVEAL**. *"These are real, measured latencies. No indexes: 1.9 seconds. The greedy plan: 469 ms. The quantum-selected plan: 346 ms — 5.4× faster, and it beats greedy within the same storage budget."* Point at a per-query win: *"velocity-check went from 56 ms to 0.3 ms — 200×."*
- **2:45–3:15 — honesty + impact.** Point at the **HONESTY PANEL**. *"We're honest: at 15 qubits a classical solver still matches QAOA — so this is a correct, principled pipeline and an honest demonstration, not a speedup claim. But it's a real QUBO formulation on real data that plugs straight into scaling quantum hardware. Backed by real research — Trummer & Koch, Schönberger & Mauerer."* Close on the 5.4× number.

**Tips:**
- Rehearse once. The numbers are stable (cached run), so they'll look identical every take.
- If you fluff a line, keep going — you can trim in Loom/QuickTime.
- Show the honesty panel; judges reward candor.

**Upload:** YouTube (set **Unlisted**) or Vimeo. Copy the link.

---

## 2. Fill out the Devpost form

Go to https://quantumhacks.devpost.com → **Submit a project**. Fields:

- **Project name:** Qurator
- **Tagline:** *Quantum optimization that picks your database indexes — and makes real queries measurably faster.*
- **Inspiration / What it does / How we built it / Challenges / Accomplishments / What we learned / What's next:** copy from `docs/SUBMISSION.md`.
- **Built with (tags):** postgresql, hypopg, python, qiskit, qiskit-aer, numpy, scipy, fastapi, nextjs, react, typescript, tailwindcss, docker
- **Try it out links:** the live demo URL + the GitHub repo URL.
- **Video demo link:** the YouTube/Vimeo link from step 1.
- **Image gallery:** upload `docs/screenshot-hero.png` and `docs/screenshot-full.png`.
- **Themes:** Quantum, Databases, Fintech.

---

## 3. Final pre-submit checklist

- [ ] Live URL opens for a logged-out visitor (test in a private/incognito window — it must NOT ask for a Vercel login).
- [ ] GitHub repo is public and the README renders with screenshots.
- [ ] Video is 2–5 min, Unlisted/public, and the link plays in incognito.
- [ ] All Devpost text fields filled from `docs/SUBMISSION.md`.
- [ ] Screenshots uploaded.
- [ ] Hit **Submit** (you can keep editing until the deadline).

That's it. 🎉
