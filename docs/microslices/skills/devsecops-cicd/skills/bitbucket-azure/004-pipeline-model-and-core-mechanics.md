---
id: skill-pipeline-model-and-core-mechanics-efd6c170fc
purpose: pipeline model and core mechanics
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-mitigation-options-for-azure-authentication-38f22c0d8d"]
links: ["skill-azure-pipes-reference-dfda999f50"]
---

## Pipeline Model and Core Mechanics

### Single-File Structure

Everything in `bitbucket-pipelines.yml` at the repo root. Unlike GitHub Actions (multiple `.github/workflows/*.yml` files), Bitbucket uses a single file. YAML anchors and the new shared-config import mechanism mitigate duplication.

```yaml
image: atlassian/default-image:4    # Default Docker image for all steps

definitions:
  caches:
    custom-cache: ./build-cache     # Custom path-based cache
  services:
    docker:
      memory: 3072                  # Increase beyond default 1 GB for image builds
    postgres:
      image: postgres:16
      variables:
        POSTGRES_PASSWORD: testpw

pipelines:
  default:                          # Runs on push to any branch not matched below
    - step:
        script:
          - echo "build and test"

  branches:
    main:
      - stage:
          name: Build & Test
          steps:
            - step:
                name: Build
                script:
                  - npm ci
                  - npm run build
                artifacts:
                  - dist/**          # Available to subsequent steps
            - parallel:
                fail-fast: true
                steps:
                  - step:
                      name: Unit Tests
                      script: [npm test]
                  - step:
                      name: Integration Tests
                      script: [npm run test:integration]
                      services: [postgres]
      - step:
          name: Deploy to Production
          deployment: production     # Environment-scoped variables + Deployments dashboard
          trigger: manual           # Any write-access user can trigger
          script:
            - pipe: atlassian/azure-aks-helm-deploy:1.0.0
              variables:
                AZURE_APP_ID: $AZURE_APP_ID
                AZURE_PASSWORD: $AZURE_PASSWORD
                AZURE_TENANT_ID: $AZURE_TENANT_ID
                CLUSTER_NAME: aks-prod
                RESOURCE_GROUP: rg-prod
                RELEASE_NAME: myapp
                CHART: ./charts/myapp
                VALUES_FILE: helm/values-prod.yaml

  pull-requests:
    '**':
      - step:
          script:
            - npm test
            - npm run lint

  tags:
    'v*.*.*':
      - step:
          deployment: production
          script:
            - echo "Deploying tag $BITBUCKET_TAG"
```

### Triggers Block (November 2025+)

The new `triggers:` block enables event-driven chaining:

```yaml
pipelines:
  custom:
    deploy-after-scan:
      triggers:
        - type: pipeline-completed
          pipeline: security-scan
          condition:
            status: successful
      steps:
        - step:
            script:
              - echo "Security scan passed, deploying"
```

Supported event types: `repository-push`, `pullrequest-push`, `pipeline-completed`, `deployment-completed`, `pullrequest-created/updated/fulfilled/rejected/reviewer-status-updated`.

---
