---
id: skill-pipeline-architecture-principles-0492ed9816
purpose: pipeline architecture principles
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-gitops-and-progressive-delivery-kubernetes-standard-bbc74c9386"]
links: ["skill-monorepo-ci-cd-at-scale-15bf54a5c2"]
---

## Pipeline Architecture Principles

### Core Rules
1. **Fail fast:** order cheap → expensive (lint → unit → build → integration → security scan → deploy staging → smoke → prod)
2. **Build once, promote the artifact:** same immutable image (tagged by git SHA, never `latest`) flows dev→staging→prod; rebuilding per environment is an anti-pattern
3. **Hermetic/deterministic builds:** same input → same artifact; Docker multi-stage builds, distroless/Chainguard/Alpine minimal bases

### Containerization
- **BuildKit/buildx:** multi-platform (arm64/amd64), cache mounts, registry cache
- **Kaniko:** rootless in-cluster builds
- **Caching:** layer caching, dependency caching (npm/pip/cargo/Maven), build-system caches (Gradle, Bazel remote cache, Nx Cloud, Turborepo)

---
