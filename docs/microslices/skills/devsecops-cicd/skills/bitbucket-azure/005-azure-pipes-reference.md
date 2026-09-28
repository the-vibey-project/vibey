---
id: skill-azure-pipes-reference-dfda999f50
purpose: azure pipes reference
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-pipeline-model-and-core-mechanics-efd6c170fc"]
links: ["skill-deployment-environments-and-variables-d0485c9322"]
---

## Azure Pipes Reference

Microsoft and Atlassian maintain these pipes for Azure deployments:

| Pipe | Purpose |
|---|---|
| `microsoft/azure-cli-run:1.x` | Run arbitrary `az` commands |
| `microsoft/azure-arm-deploy:1.x` | Deploy ARM/Bicep templates |
| `microsoft/azure-functions-deploy:1.x` | Deploy Azure Functions |
| `atlassian/azure-web-apps-deploy:1.x` | Deploy zip-based App Service code |
| `atlassian/azure-web-apps-containers-deploy:1.x` | Deploy container images to App Service |
| `microsoft/azure-aks-deploy:1.x` | kubectl against AKS |
| `atlassian/azure-aks-helm-deploy:1.x` | Helm against AKS |
| `microsoft/azure-storage-deploy:1.x` | Sync to Azure Storage |
| `microsoft/azure-static-web-apps-deploy:1.x` | Deploy to Azure Static Web Apps |

All pipes expect `AZURE_APP_ID`, `AZURE_PASSWORD`, `AZURE_TENANT_ID` as variables. ACR pushes:

```yaml
script:
  - docker build -t myregistry.azurecr.io/myapp:$BITBUCKET_COMMIT .
  - docker login myregistry.azurecr.io -u $AZURE_APP_ID -p $AZURE_PASSWORD
  - docker push myregistry.azurecr.io/myapp:$BITBUCKET_COMMIT
```

---
