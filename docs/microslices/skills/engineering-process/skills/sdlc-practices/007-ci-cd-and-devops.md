---
id: skill-ci-cd-and-devops-83df6db94b
purpose: ci cd and devops
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-testing-strategy-9d73af50bf"]
links: ["skill-code-quality-and-tech-debt-54b22f1b74"]
---

## CI/CD and DevOps

### CI/CD Principles
- **CI**: integrate to shared mainline ≥ daily; automated build + test; keep the build green (Andon-cord discipline — stop the line on red).
- Pipeline ordering (fail-fast): lint → unit → build → integration → security → deploy.
- Hermetic, reproducible builds (Docker multi-stage).
- **CD (Delivery)**: every commit is releasable.
- **CD (Deployment)**: every commit is released automatically.

### Deployment Strategies
- **Feature flags**: decouple deploy from release.
- **Rolling**: gradual replacement.
- **Blue-green**: instant switch between two environments.
- **Canary**: metric-gated gradual rollout.
- **A/B testing**: traffic split for experiments.
- **Dark launching**: new code runs but results are not surfaced.
- **GitOps** (Argo CD, Flux): Git as the source of truth for declarative desired state.

### DORA Metrics (5 metrics as of 2025)
1. **Deployment frequency**: how often code is deployed to production.
2. **Lead time for changes**: time from commit to production.
3. **Change failure rate**: percentage of deployments causing production failures.
4. **Failed deployment recovery time** (formerly MTTR, redefined): time to recover from a change-caused failure.
5. **Rework rate** (added 2024): ratio of unplanned deployments caused by a production incident to total deployments.

**2025 evolution**: DORA replaced low/medium/high/elite tiers with **seven team archetypes**:
- Harmonious High-Achievers (20%)
- Pragmatic Performers (20%)
- Constrained by Process (17%)
- Stable and Methodical (15%)
- Legacy Bottleneck (11%)
- Foundational Challenges (10%)
- High Impact/Low Cadence (7%)

Top two archetypes (~40%) share: strong platform engineering, small batches, and clear AI stance.

### DevSecOps and Supply Chain Security
Supply-chain attacks roughly doubled in 2025 (Sonatype: 454,600+ new malicious packages, 99% in npm).

**Regulatory mandates**: US EO 14028, EU Cyber Resilience Act — both mandate SBOMs and provenance.

**Key standards and tools**:
- **SLSA** (Supply-chain Levels for Software Artifacts): provenance/build integrity, levels 1–3+. Level 2 + Sigstore signing is achievable on GitHub Actions/GitLab CI in 1–2 days.
- **Sigstore**: keyless signing via Cosign/Fulcio + Rekor transparency log.
- **in-toto attestations**.
- **NIST SSDF (SP 800-218)**, **OWASP SAMM**, **BSIMM** — measure program maturity.

---
