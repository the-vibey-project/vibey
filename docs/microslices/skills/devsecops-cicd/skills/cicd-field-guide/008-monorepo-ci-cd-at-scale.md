---
id: skill-monorepo-ci-cd-at-scale-15bf54a5c2
purpose: monorepo ci cd at scale
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-pipeline-architecture-principles-0492ed9816"]
links: ["skill-testing-in-ci-cd-43013e4028"]
---

## Monorepo CI/CD at Scale

| Tool | Best For | Key Feature |
|---|---|---|
| **Turborepo** | JS/TS workspaces, "CI is slow" problem | Content-aware hashing, local+remote caching, `--filter='...[origin/main...HEAD]'` |
| **Nx** | JS/TS to polyglot, growing monorepo | Task sandboxing (flags undeclared inputs/outputs — Turborepo lacks this), module-boundary enforcement, distributed task execution |
| **Bazel** | Very large multi-language orgs (Google/Stripe-scale) | Hermetic, remote execution, polyglot — steep learning curve; Stripe: ~45min→~7min |
| **Lerna** | Legacy (now runs on Nx under the hood) | — |

**In CI:** `fetch-depth: 0` for git history; `nrwl/nx-set-shas` for correct base/head; path filtering + dynamic matrices.

---
