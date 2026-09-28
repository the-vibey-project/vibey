---
id: skill-serverless-architecture-6e3a8ced63
purpose: serverless architecture
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-microservices-architecture-62fbe9e8e4"]
links: ["skill-event-driven-architecture-eda-6a62bd0f75"]
---

## Serverless Architecture

**Azure Functions plans:**
| Plan | Notes |
|---|---|
| **Flex Consumption** (Recommended, GA Dec 2024) | VNet integration at no extra cost, instance memory selection (512/2048/4096 MB), per-instance concurrency scaling, "Always Ready" to eliminate cold starts, configurable max instances (min 40, max 1,000, default 100), Hyper-V isolation |
| Consumption | Legacy |
| Premium | Higher cost, pre-warmed |
| Dedicated | Always-on App Service Plan |

**Critical Flex Consumption constraints:**
- Subnet names cannot contain underscores
- Use at least a /27 subnet (smaller can fail gateway creation silently)
- Reserve ~40 IPs per app
- **Cannot share a subnet between an ACA environment and a Flex Consumption app**
- All Flex apps share a default **250-core regional subscription quota** — a single app scaled to 1,000 × 512 MB instances can consume the entire quota

**Retirements to schedule:**
- Legacy Linux Consumption plan retires **September 30, 2028** → migrate to Flex Consumption
- In-process .NET model retires **November 2026**

**Durable Functions patterns:**
- Orchestrator/activity/entity; chaining; fan-out/fan-in; eternal orchestrations (`ContinueAsNew`)
- **Human-approval**: `WaitForExternalEvent` + a durable timer for timeout/escalation
- **Critical rule: orchestrators must be deterministic** — never call `DateTime.Now`/`Date.now()`, random, or direct I/O inside an orchestrator; use `context.CurrentUtcDateTime` and delegate I/O to activities

**Decision trigger:** Spiky/bursty or event-driven workloads where idle cost matters; choose Flex Consumption unless you need a feature only on another plan.
