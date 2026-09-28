---
id: skill-part-4-cross-cutting-concerns-a623125fdd
purpose: part 4 cross cutting concerns
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/github-atlassian/SKILL.md
requires: ["skill-part-3-github-atlassian-integration-efa2182f68"]
links: ["skill-staged-implementation-roadmap-e9b8287e07"]
---

## Part 4 — Cross-Cutting Concerns

### Org Design
- Mono-repo vs poly-repo drives GitHub org/team structure and Jira project layout (one project per team is the common default)
- Standardize naming across both: branch names, PR titles, Jira summaries
- Standardize identity: one IdP (Entra ID/Okta) → GitHub teams via EMU SCIM → Jira groups/roles via Guard SCIM

### End-to-End Agile Delivery Flow
Jira issue → issue-keyed branch → PR (linked) → CI (Actions/Pipelines) → human + Copilot code review → merge queue → Jira transition → release → deployment tracked in Jira

- **Dual-track agile:** Confluence (discovery) + Jira sprints (delivery)
- **DoD enforcement:** Jira automation + GitHub required checks

### DORA Metrics Cross-Platform
- **Deployment frequency:** GitHub releases/deployments
- **Lead time:** Jira create → PR merge → deploy
- **Change failure rate:** bug/incident tickets
- **MTTR:** incident resolution
- **Tooling:** LinearB, Sleuth, Faros AI, Jellyfish, Haystack

### Security and Compliance Integration
- GHAS findings → Jira security issues (via Actions)
- Both audit logs → SIEM
- JSM change requests linked to GitHub PRs/deployments
- Secret-scanning alerts → JSM incidents
- Both platforms carry SOC 2 / ISO 27001; Atlassian Cloud adds FedRAMP

### Licensing and Cost Optimization
| Product | Standard | Premium |
|---|---|---|
| Jira | ~$7.91/user/mo | ~$14.54/user/mo |
| Confluence | ~$5.42/user/mo | ~$10.44/user/mo |
| JSM | ~$20/agent/mo | ~$47–53/agent/mo |
| GitHub Team | $4/user/mo | — |
| GitHub Enterprise | ~$21/user/mo | — |
| GHAS Secret Protection | $19/committer/mo | — |
| GHAS Code Security | $30/committer/mo | — |
| Copilot Business | $19/user/mo | — |
| Copilot Enterprise | $39/user/mo (+ GHEC) | — |

**Optimization levers:**
- Prune inactive users (metered billing means unused seats still cost)
- Scope GHAS to specific repos, not org-wide
- Reconcile licenses against IdP group sync
- Consolidate on Enterprise where volume discounts apply
- Set Copilot spend alerts given usage-based billing

---
