---
id: skill-secrets-management-no-hardcoded-credentials-121c3aa354
purpose: secrets management no hardcoded credentials
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-dast-owasp-zap-for-deployed-environments-367c40e4c3"]
links: ["skill-branch-protection-rules-a96e1c9d00"]
---

## Secrets Management — No Hardcoded Credentials

**In GitHub Actions workflows:**
- Use `${{ secrets.* }}` for sensitive values
- Use OIDC federation for Azure, AWS, GCP (no stored cloud credentials)
- Use `${{ vars.* }}` for non-sensitive configuration

**Repository secrets vs environment secrets:**
- Repository secrets are available to all workflows — use for non-environment-specific values
- Environment secrets (under `environment: production`) are only injected when the job runs against that environment — use for production credentials

```yaml
# OIDC pattern — only tenant/subscription IDs stored as secrets, no passwords
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}      # App registration client ID
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}      # Tenant ID
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
    # No AZURE_CLIENT_SECRET — uses OIDC token exchange
```

---
