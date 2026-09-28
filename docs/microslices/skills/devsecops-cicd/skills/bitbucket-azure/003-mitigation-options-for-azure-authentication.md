---
id: skill-mitigation-options-for-azure-authentication-38f22c0d8d
purpose: mitigation options for azure authentication
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-the-critical-azure-oidc-gap-e299adaabb"]
links: ["skill-pipeline-model-and-core-mechanics-efd6c170fc"]
---

## Mitigation Options for Azure Authentication

### Option A: Per-Environment Service Principal Secrets (Most Common)

Provision one service principal per environment, scoped tightly to a resource group:

```bash
az ad sp create-for-rbac \
  --name bitbucket-prod \
  --role Contributor \
  --scopes /subscriptions/<sub>/resourceGroups/rg-prod
```

Store `AZURE_APP_ID`, `AZURE_PASSWORD`, `AZURE_TENANT_ID` as **deployment variables** (not repository variables) so they are only injected when `deployment: <env>` is on the step:

```yaml
- step:
    name: Deploy to Prod
    deployment: production    # Scopes these variables to this step only
    script:
      - pipe: microsoft/azure-arm-deploy:1.0.0
        variables:
          AZURE_APP_ID: $AZURE_APP_ID
          AZURE_PASSWORD: $AZURE_PASSWORD
          AZURE_TENANT_ID: $AZURE_TENANT_ID
          AZURE_RESOURCE_GROUP: rg-prod
          AZURE_TEMPLATE_LOCATION: infra/main.bicep
```

**Auto-rotate secrets** via a scheduled custom pipeline:
```yaml
custom:
  rotate-azure-credentials:
    - variables:
        - name: TARGET_ENV
          default: prod
          allowed-values: [dev, staging, prod]
    - step:
        script:
          - az login --service-principal -u $AZURE_APP_ID -p $AZURE_PASSWORD --tenant $AZURE_TENANT_ID
          - NEW_SECRET=$(az ad app credential reset --id $AZURE_APP_ID --query password -o tsv)
          - curl -X PUT "https://api.bitbucket.org/2.0/repositories/$BITBUCKET_WORKSPACE/$BITBUCKET_REPO_SLUG/deployments_config/environments/$ENV_UUID/variables/$VAR_UUID" \
              -H "Authorization: Bearer $BITBUCKET_ACCESS_TOKEN" \
              -d "{\"value\": \"$NEW_SECRET\", \"secured\": true}"
```

### Option B: Token Broker Azure Function (Recommended for Zero Long-Lived Secrets)

Build an Azure Function that:
1. Validates the incoming `BITBUCKET_STEP_OIDC_TOKEN` against Bitbucket's JWKS endpoint
2. Verifies expected claims: `workspaceUuid`, `repositoryUuid`, `deploymentEnvironmentUuid`
3. On success, mints a short-lived (1-hour) client secret on a per-environment App Registration
4. Returns temporary credentials to the pipeline

```yaml
- step:
    oidc: true    # Enables BITBUCKET_STEP_OIDC_TOKEN in this step
    deployment: production
    script:
      # Exchange Bitbucket OIDC token for short-lived Azure credentials
      - |
        CREDS=$(curl -s -X POST "https://token-broker.azurewebsites.net/api/exchange" \
          -H "Content-Type: application/json" \
          -d "{\"oidcToken\": \"$BITBUCKET_STEP_OIDC_TOKEN\", \"environment\": \"production\"}")
        export AZURE_APP_ID=$(echo $CREDS | jq -r '.clientId')
        export AZURE_PASSWORD=$(echo $CREDS | jq -r '.clientSecret')
        export AZURE_TENANT_ID=$(echo $CREDS | jq -r '.tenantId')
      - az login --service-principal -u $AZURE_APP_ID -p $AZURE_PASSWORD --tenant $AZURE_TENANT_ID
```

The token broker validates Bitbucket OIDC (which works fine for non-Azure targets) and then uses a "Management App" with `Application.ReadWrite.OwnedBy` to mint short-lived credentials. Treat the Function as security-critical: rate-limit by repository UUID, log every exchange to a Sentinel workspace.

### Option C: Azure Pipelines as Orchestrator

Keep Bitbucket as code host but run deployment legs on Azure Pipelines with its native workload-identity service connection:

- Bitbucket Cloud is a first-class repository type in Azure Pipelines (YAML pipelines + PR triggers supported)
- Azure Pipelines builds the **latest commit on the PR source branch** (not merge commit — Bitbucket Cloud doesn't expose merge-commit info via API)
- Keep CI (build, test, lint) on Bitbucket Pipelines; run deployment legs on Azure Pipelines

### Option D: HashiCorp Vault as Intermediary

Bitbucket OIDC works fine with Vault (unlike Azure). Use Vault's `azure` secrets engine:

```yaml
- step:
    oidc: true
    script:
      - vault login -method=jwt jwt=$BITBUCKET_STEP_OIDC_TOKEN role=bitbucket-deployer
      - AZURE_CREDS=$(vault read azure/creds/deployer -format=json)
      - export AZURE_APP_ID=$(echo $AZURE_CREDS | jq -r '.data.client_id')
      - export AZURE_PASSWORD=$(echo $AZURE_CREDS | jq -r '.data.client_secret')
```

---
