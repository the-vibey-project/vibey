---
id: skill-security-the-highest-leverage-action-d281b75233
purpose: security the highest leverage action
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-branching-strategy-a377b868dd"]
links: ["skill-gitops-and-progressive-delivery-kubernetes-standard-bbc74c9386"]
---

## Security: The Highest-Leverage Action

### OIDC / Workload Identity Federation — Do This First

Replace long-lived cloud service-principal secrets with short-lived OIDC tokens per run.

**Platform-by-platform:**
- **GitHub Actions → Azure/AWS/GCP:** `permissions: id-token: write` + `azure/login`; bind federated credentials to GitHub Environments (`environment:<env>` subject), not branches
- **Azure DevOps:** GA via the Convert tool; federation subject constrains identity to a specific service connection — a stricter guarantee than a secret; run the bulk PowerShell for mass migration
- **GitLab:** ID tokens (`id_tokens:` block)
- **Bitbucket:** `oidc: true` flag, `$BITBUCKET_STEP_OIDC_TOKEN`

**Hard deadline:** Bitbucket app passwords — brownouts June 9, 2026; permanent removal July 28, 2026.

### Supply-Chain Security: SLSA + Sigstore + SBOMs

**SLSA (OpenSSF, v1.0 April 2023):**
- L1: provenance exists
- L2: hosted build + signed provenance
- L3: hardened, isolated, ephemeral build environment
- GitHub's `actions/attest-build-provenance` + `slsa-github-generator` achieve L2–L3 "in an afternoon"

**Sigstore stack:**
- **Cosign:** signs container images/artifacts
- **Fulcio:** issues short-lived certs tied to OIDC identity (keyless signing — no long-lived keys)
- **Rekor:** append-only public transparency log

**SBOM generators:**
- **Syft (Anchore):** best dedicated SBOM generator; SPDX + CycloneDX, broad ecosystem coverage
- **Trivy (Aqua):** Swiss Army knife — vuln scanning + IaC misconfig + secret detection + license checks + SBOM in one binary (note: reported compromised in a supply-chain attack in early 2026 — pin versions and verify provenance of your scanners)
- **Grype (Anchore):** pairs with Syft for SBOM-first vuln scanning with EPSS/KEV-based risk prioritization

**Critical principle:** prioritize findings by exploitability (EPSS, CISA KEV), not raw CVSS count — alerting on every CVE destroys developer trust.

**Verify provenance at deploy time** — generating SBOMs without verification is theater.

---
