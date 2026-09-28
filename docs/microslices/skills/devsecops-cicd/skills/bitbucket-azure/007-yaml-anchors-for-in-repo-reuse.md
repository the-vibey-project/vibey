---
id: skill-yaml-anchors-for-in-repo-reuse-8cab47e16f
purpose: yaml anchors for in repo reuse
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-deployment-environments-and-variables-d0485c9322"]
links: ["skill-runners-hosted-vs-self-hosted-e79a3588ad"]
---

## YAML Anchors for In-Repo Reuse

YAML anchors are the mechanism for deduplication within a single `bitbucket-pipelines.yml`:

```yaml
definitions:
  steps:
    - step: &build-step
        name: Build
        script:
          - npm ci
          - npm run build
        caches: [node]
        artifacts: [dist/**]

    - step: &test-step
        name: Test
        script: [npm test]
        caches: [node]

pipelines:
  branches:
    main:
      - step: *build-step
      - step: *test-step
      - step:
          name: Deploy
          script: [./deploy.sh]

    develop:
      - step: *build-step
      - step: *test-step
```

For reuse across repos, use the shared pipeline config mechanism (Premium feature):
```yaml
# In consuming repo's bitbucket-pipelines.yml
import:
  repository: myorg/shared-pipelines
  ref: main
  path: security-scan-pipeline

pipelines:
  branches:
    main:
      - import: security-scan-pipeline
```

---
