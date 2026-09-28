---
id: skill-supply-chain-security-sbom-sigstore-provenance-cfd3213d9f
purpose: supply chain security sbom sigstore provenance
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-ai-model-supply-chain-llm03-2025-0f0cf804e1"]
links: ["skill-vibe-coding-ai-generated-code-risks-29ad309f77"]
---

## Supply-Chain Security (SBOM/Sigstore/Provenance)

- Generate SBOMs: **Syft** (broad coverage) or **cyclonedx-py** (build-tool integrated, most accurate at capture time)
- Sign artifacts: **cosign** (keyless via Sigstore/Fulcio/Rekor + OIDC)
- Target **SLSA Level 2→3** provenance (SLSA GitHub Generator gives L3 on GitHub Actions)
- **in-toto attestations**
- Verify at deploy time via admission policy (Kubernetes admission controller)
- Sonatype: 454,600+ new malicious packages reported in 2025
- **SBOM alone is insufficient** — pair with provenance + signature verification (SolarWinds/GhostAction lesson)

### CI/CD Security Gates
SAST (Bandit/Semgrep/CodeQL) + SCA (pip-audit/npm audit/Snyk/Trivy/OSV-Scanner) + secret scanning (Gitleaks/detect-secrets/TruffleHog) + DAST (OWASP ZAP) as **blocking** pipeline gates.

**Note on SAST limitations:** a 2026 benchmark found 78% of confirmed vulnerabilities detected by only 1 of 5 SAST tools — SAST is structurally insufficient for semantic flaws.

---
