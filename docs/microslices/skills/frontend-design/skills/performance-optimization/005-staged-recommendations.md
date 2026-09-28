---
id: skill-staged-recommendations-027f25a117
purpose: staged recommendations
source: src/vibey_tools/skills/plugins/frontend-design/skills/performance-optimization/SKILL.md
requires: ["skill-azure-cloud-performance-ad6961f569"]
links: ["skill-caveats-bf18f292bf"]
---

## Staged Recommendations

**Stage 1 — Measure (week 1):**
Wire up RUM (`onINP` from web-vitals), py-spy/Scalene on hottest Python services, Application Insights with adaptive sampling (start 100% to baseline, then drop to 10–25%). Capture before-numbers: P50/P95/P99 latency, RPS, First Load JS per route, LCP/INP/CLS at 75th percentile, DB connection counts, Function cold-start frequency. Optimize nothing yet.

**Stage 2 — Highest ROI per effort (weeks 2–4):**
- Python: upgrade interpreter to 3.12/3.13; vectorize the worst Pandas loops; move blocking calls off the event loop. Act on any function >5% of total CPU in the profiler.
- Next.js: push `"use client"` to leaves; parallelize server fetches; add Suspense streaming with matched skeletons; set `priority` on LCP images; use `next/font`. Act on any route with First Load JS >300KB or INP >200ms.
- Azure: move latency-sensitive Functions off Consumption to Flex/Premium; add a singleton Redis multiplexer + pipelining; fix Prisma/SQLAlchemy pooling (singleton + external pooler) if you see connection exhaustion.

**Stage 3 — Architecture (weeks 4+):**
Adopt PPR/Cache Components for mixed static+dynamic pages (target TTFB <100ms); KEDA scale-to-zero on ACA for bursty/background workloads; choose the right messaging service per pattern; right-size VMs; apply Reserved Instances for steady baseline + Spot for fault-tolerant batch. Pilot free-threaded Python 3.14t for CPU-bound parallel workloads.

**Thresholds that change the plan:**
- INP stays >200ms after JS work → bottleneck is third-party scripts or hydration; facade/defer them
- Turbopack increases First Load JS in A/B → keep Webpack for prod
- B-series VMs throttle (credits hitting zero) → switch to D-series
- ACA average utilization exceeds ~40%/month → move to dedicated/AKS reserved
- Adaptive sampling breaks trace correlation → standardize sampling rates across services

---
