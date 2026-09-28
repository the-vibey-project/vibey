---
id: skill-dependency-management-dependabot-snyk-renovate-7a4b1f604f
purpose: dependency management dependabot snyk renovate
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-security-policy-as-code-with-opa-rego-d02d9ec443"]
links: ["skill-pipeline-security-anti-patterns-to-avoid-f4e59c21dc"]
---

## Dependency Management: Dependabot + Snyk + Renovate

**Renovate bot** (more configurable than Dependabot) for automated dependency updates:
```json
// renovate.json
{
  "extends": ["config:base", ":dependencyDashboard"],
  "packageRules": [
    {
      "matchUpdateTypes": ["patch"],
      "automerge": true    // Auto-merge patch updates
    },
    {
      "matchPackagePatterns": ["^Azure\\.", "^Microsoft\\."],
      "groupName": "Azure SDK packages"
    }
  ],
  "prConcurrentLimit": 5
}
```

---
