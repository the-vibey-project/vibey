---
id: skill-monolithic-architecture-33981d97e4
purpose: monolithic architecture
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-compute-decision-ladder-2026-default-fe76b03cac"]
links: ["skill-microservices-architecture-62fbe9e8e4"]
---

## Monolithic Architecture

**When to use:** Startup stage, small teams, domain not yet well understood.

**Azure mapping:**
- **App Service (Web Apps)**: default modular-monolith host
- **Azure Spring Apps**: Spring Boot
- **Blue-green/zero-downtime**: App Service **deployment slots** — deploy to staging, warm it, swap (near-instant, reversible)
- **Strangler migration**: Front Door or App Gateway as façade

**Production gotchas:**
- Slot swaps carry app settings unless marked "slot setting" — classic cause of staging config leaking to production
- Cold slots cause first-request latency post-swap; use `applicationInitialization` warm-up paths
- **Anti-pattern:** decomposing before you have module boundaries — creates a distributed big ball of mud

**Decision trigger:** Stay monolithic until you have measurable deployment contention between teams or a clearly independent scaling/availability requirement for a subsystem.
