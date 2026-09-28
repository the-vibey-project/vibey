---
id: skill-dora-metrics-the-evidence-base-ee785c9856
purpose: dora metrics the evidence base
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-the-four-defining-shifts-2015-2025-pipeline-ae02ac914a"]
links: ["skill-platform-selection-1a8ec9df4f"]
---

## DORA Metrics: The Evidence Base

### The Five-Metric Model (2025)

**Throughput group:**
- Change lead time
- Deployment frequency
- **Failed deployment recovery time** (renamed MTTR — grouped with throughput because fast recovery enables flow)

**Instability group:**
- Change fail rate
- **Rework rate** (new 5th metric) — ratio of unplanned deployments triggered by a production incident

**Reliability:** SLO/SLI-based, sits alongside.

*The relabeling of "stability" to "instability" and the addition of rework rate addresses a decade-long anomaly: change failure rate never loaded statistically with the other metrics.*

### AI Is an Amplifier, Not a Fix

2025 State of AI-assisted Software Development (survey of ~5,000 professionals, June–July 2025):
- 90% report using AI at work; 80%+ believe it increased productivity
- **Trust paradox:** only ~24% report "a great deal" or "a lot" of trust in AI-generated code; 30% trust it "a little" or "not at all"
- AI in 2025 showed a **positive relationship with throughput** (a reversal from 2024) but **continued to correlate with worse delivery stability** — AI increases change volume and batch size, exposing weak testing, review, and feedback loops

2024 data (baseline): "As AI adoption increased, it was accompanied by an estimated decrease in delivery throughput by 1.5%, and an estimated reduction in delivery stability by 7.2%" per 25% increase in AI adoption.

**The through-line:** AI raises the stakes on getting the CI/CD basics right rather than changing them.

### DORA's Seven AI Capabilities
(December 2025 AI Capabilities Model — six of seven are classic CI/CD fundamentals)
1. Clear and communicated AI stance
2. Healthy data ecosystems
3. AI-accessible internal data
4. **Strong version control practices**
5. **Working in small batches**
6. User-centric focus
7. **Quality internal platforms**

### Platform Engineering Warning
Per the 2024 DORA Report: internal developer platforms increased individual developer productivity 8% and team productivity 10% — but teams *required* to use platforms exclusively saw a **decrease in change throughput (8%) and stability (14%)**. Platforms must be paved roads (opt-in golden paths), not mandates.

---
