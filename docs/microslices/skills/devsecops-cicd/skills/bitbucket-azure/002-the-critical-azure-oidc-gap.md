---
id: skill-the-critical-azure-oidc-gap-e299adaabb
purpose: the critical azure oidc gap
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-tl-dr-decision-guide-02c53ea61c"]
links: ["skill-mitigation-options-for-azure-authentication-38f22c0d8d"]
---

## The Critical Azure OIDC Gap

**Bitbucket Pipelines OIDC tokens CANNOT be used to log into Azure (Entra ID).** This is not a configuration issue — it is an architectural incompatibility confirmed by Atlassian.

Atlassian Team (Theodora Boudale, 27 Feb 2024): *"Bitbucket's OIDC tokens cannot be used for logging in to Azure."*

Feature request BCLOUD-22206 ("Provide native support for authentication using OIDC within the Azure platform") is status **Gathering Interest, Unresolved** as of January 2026. Atlassian has not committed to building this.

**Root cause:** Bitbucket's `sub` claim is not in a stable, predictable subject-identifier format that Entra's federated-credential validator accepts. Entra also rejects Bitbucket's ARI-format audience for public cloud applications:
> "Failed to update federated credential. Expression is not supported for applications in this cloud 'Public' using issuer 'https://api.bitbucket.org/…/pipelines-config/identity/oidc'."

Contrast with GitHub Actions (`azure/login@v1` with federated credentials) and GitLab CI/CD — both federate seamlessly into Entra without stored secrets. Bitbucket cannot.

---
