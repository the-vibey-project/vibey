---
id: skill-caveats-bf18f292bf
purpose: caveats
source: src/vibey_tools/skills/plugins/frontend-design/skills/performance-optimization/SKILL.md
requires: ["skill-staged-recommendations-027f25a117"]
links: []
---

## Caveats

- **Benchmarks are workload-specific.** RPS figures (~3x FastAPI vs Flask), vectorization multipliers (100–740x), and cold-start numbers (2–7s) come from specific tests/configs. Always benchmark your own workload.
- **Version flux.** PPR/Cache Components, Turbopack-as-default, and free-threading all landed across Next.js 16 and Python 3.14 (both Oct 2025). Some behaviors described above changed between v14/v15/v16 — always identify which major version you're on before debugging cache behavior.
- **Free-threading is not universally production-ready.** C-extension ecosystem support is still catching up; importing a non-thread-safe extension silently re-enables the GIL. The 3.13 JIT is a 0–5% win today.
- **Some figures are single-source.** Cosmos-for-PG "500% faster" is one user's report. "Scale out fast, scale in slow" 40–50pt gap and ACA 40%-utilization crossover are best-practice/third-party guidance, not official Microsoft thresholds. The flapping-avoidance principle IS official Microsoft guidance.
- **Microsoft publishes no official ms latency figure for WAF** — treat any specific number skeptically.
