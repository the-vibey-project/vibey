---
id: skill-pipeline-security-anti-patterns-to-avoid-f4e59c21dc
purpose: pipeline security anti patterns to avoid
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-dependency-management-dependabot-snyk-renovate-7a4b1f604f"]
links: []
---

## Pipeline Security Anti-Patterns to Avoid

1. **`soft_fail: true` on security scans** — defeats the purpose of gates. Only acceptable during initial rollout.

2. **Scanning only the PR diff** — use `fetch-depth: 0` for secrets scanning; scan the full image for container vulnerabilities, not just changed files.

3. **Skipping SARIF upload on failure** — always `if: always()` on SARIF uploads so findings appear in GitHub Security tab even when the job fails.

4. **Single SARIF for multiple scans** — upload separate SARIF files from each tool so findings are attributed correctly.

5. **Environment secrets as repository secrets** — production credentials should be environment-scoped, not available to all workflows.

6. **No exception process** — blanket `soft_fail: true` or skipping all checks is worse than no scanning. Build a documented, time-bound exception process with a required security review.

7. **Building untrusted pull requests with access to secrets** — use `pull_request_target` only when necessary and keep secrets out of untrusted PR contexts.
