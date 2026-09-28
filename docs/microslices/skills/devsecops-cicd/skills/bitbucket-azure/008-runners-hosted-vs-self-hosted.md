---
id: skill-runners-hosted-vs-self-hosted-e79a3588ad
purpose: runners hosted vs self hosted
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-yaml-anchors-for-in-repo-reuse-8cab47e16f"]
links: ["skill-pricing-may-2026-atlassian-list-c3a16ac651"]
---

## Runners: Hosted vs Self-Hosted

### Hosted Runners (Atlassian-managed)

**Linux only** — x86_64 by default, ARM available via `runtime.cloud.arch: arm`. No hosted Windows, no hosted macOS.

Step sizes and memory:
| Size | Memory | vCPU | Minute multiplier |
|---|---|---|---|
| 1x (default) | 4 GB | 2 | 1x |
| 2x | 8 GB | 4 | 2x |
| 4x | 16 GB | 8 | 4x |
| 8x | 32 GB | 16 | 8x |
| 16x–32x | 64–128 GB | 32–64 | 16x–32x |

**Size multipliers consume minutes at the multiplier rate** — a 4x step costs 4 minutes per 1 minute of wall-clock time. This is the single most common source of cost surprise.

```yaml
- step:
    name: Heavy Build
    size: 4x    # Costs 4x minutes — check before committing to this size
    script:
      - mvn clean package
```

**Docker service memory** is capped at 1 GB independent of step `size:`. Modern images exceed this. Always set explicitly for image-heavy pipelines:

```yaml
definitions:
  services:
    docker:
      memory: 3072    # 3 GB — must set separately from step size
```

### Self-Hosted Runners

Required for Windows, macOS, or builds needing private network access (private AKS clusters, App Service with IP restrictions).

```yaml
- step:
    name: Windows Build
    runs-on:
      - self.hosted    # Routes to self-hosted runners
      - windows        # Label filtering
    script:
      - dotnet build
      - dotnet test
```

**Pricing (March 2026 model):** Up to 100 free self-hosted runners per workspace. Premium Runners add-on billed by maximum concurrent build slots used per month. V3/V4 runners deprecated mid-2026 — migrate to V5.

---
