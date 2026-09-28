---
id: skill-part-2-atlassian-cc9b251323
purpose: part 2 atlassian
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/github-atlassian/SKILL.md
requires: ["skill-part-1-github-1f7789b953"]
links: ["skill-part-3-github-atlassian-integration-efa2182f68"]
---

## Part 2 — Atlassian

### 2.1 Server EOL and Data Center Countdown

| Milestone | Date |
|---|---|
| Server end of support | February 15, 2024 — **DONE** |
| No new DC sales | March 30, 2026 |
| DC license/tier/app purchases stop | March 30, 2028 |
| DC full EOL (read-only) | March 28, 2029 |

Migration path: Cloud Migration Assistant; "Atlassian Ascend"/FastShift programs for 1,000+ user orgs.
A Bitbucket Hybrid License (DC + Cloud) arrives mid-2026.

### 2.2 Jira Software

**Two project types:**
- **Team-managed (formerly next-gen):** simple, autonomous
- **Company-managed (classic):** deep scheme model (workflow, permission, notification, issue type, field, screen schemes + project roles) — required for workflow gates, cross-project portfolio

**Hierarchy:** Initiatives (in Plans) → Epics → Stories/Tasks → Sub-tasks

**Workflows:** statuses/transitions with conditions, validators, post-functions — the feature that makes Jira worth it over GitHub Issues.

**JQL tips:** write index-friendly queries; avoid full-text scans at scale; use functions (`currentUser()`, `membersOf()`, `startOfWeek()`).

**Jira Automation:** no-code triggers/conditions/actions/branches at project and org level.

**Jira Plans (Advanced Roadmaps):** cross-team/program planning and dependency tracking.

### 2.3 Jira Service Management (JSM) — Now "Service Collection"

**JSM + Assets + Rovo + Customer Service Management** are now sold as the Service Collection.

**Premium tier (~$47–53/agent/mo) gates the features that matter:**
- CMDB/Assets
- Change management with CI/CD deployment gating
- Major incident management
- Atlassian Intelligence
- Virtual Service Agent

**Billed per agent** — requesters are free.

**Opsgenie status:** new sales ended June 4, 2025; full shutdown April 5, 2027; capabilities folded into JSM.

**JSM vs ServiceNow vs Zendesk:**
- JSM wins: Atlassian-ecosystem integration, per-agent price
- ServiceNow wins: heavyweight enterprise ITSM breadth
- Zendesk wins: pure customer-facing support UX

### 2.4 Rovo — Atlassian's AI Layer

**"Rovo for all" (from April 9, 2025):** Rovo Search/Chat/Agents/Studio included in paid Jira/Confluence/JSM Cloud plans — no separate SKU for core features.

**Credit allowances (pooled at org level, monthly, no rollover):**

| Plan | Credits/user/mo |
|---|---|
| Standard | 25 |
| Premium | 70 |
| Enterprise | 150 |

- Jira, Confluence, and Service Collection/JSM
- A single Rovo Chat/Agent question = 10 credits; Deep Research = 100 credits
- Atlassian Intelligence (in-product drafting/summaries) is the foundation; Rovo is the cross-product layer
- **Rovo Dev** (for engineers — CLI, PR analysis) is a separate $20/dev/mo product with 2,000 credits
- Rovo is **Cloud-only**
- Rovo credit overages are not yet billed but Atlassian has signaled future consumption-based charging (≥90 days notice)

### 2.5 Bitbucket — URGENT Deprecation

**App-password hard deadline:**
- No new creation: September 9, 2025 — **PASSED**
- Controlled brownouts begin: June 9, 2026
- Permanent removal: July 28, 2026

**Action required immediately:** migrate all Bitbucket CI integrations to API tokens with scopes (or OIDC for cloud auth).

**Bitbucket Pipelines OIDC:** `oidc: true` flag; `$BITBUCKET_STEP_OIDC_TOKEN` for keyless cloud auth.

**Code Insights/Annotations API:** pushes CI quality/coverage/security results back onto PRs.

**Bitbucket Pipelines vs GitHub Actions:**
- Actions wins on: ecosystem (20,000+ marketplace), reusable workflows, matrix builds, macOS/Windows runners, free minutes (2,000/mo vs Bitbucket's 50 free; Standard 2,500, Premium 3,500)
- Pipelines wins on: simplicity and zero-config Jira deployment tracking

**Main reason to keep Bitbucket:** native Jira integration — same-vendor, deeper integration than GitHub's, strongest reason Atlassian-centric orgs stay

### 2.6 Confluence

**Key capabilities:**
- Spaces with a permission model (space admin; page view/add/edit/delete/export)
- Page hierarchy and restrictions
- Fabric editor with macros (code, ToC, panels, status, live Jira issue lists, children display, excerpt/excerpt-include)
- **Whiteboards** (GA February 29, 2024): Cloud-only
- **Databases** (broad rollout July 10, 2024): structured data as fields + entries, sync from Jira/Confluence/CSV — Cloud-only
- CQL search and Confluence Analytics (Cloud)
- Page properties + reports for lightweight tracking

**Confluence vs Notion vs SharePoint:**
- Confluence wins: Atlassian-integrated teams (live Jira embeds, JSM knowledge base, space permissions)
- Notion wins: flexible databases/UX for smaller teams
- SharePoint wins: Microsoft 365-centric document governance

### 2.7 Forge vs Connect

**Forge has replaced Connect** as the app platform.

| | Connect | Forge |
|---|---|---|
| Model | External iframe (third-party servers) | Serverless on Atlassian infrastructure |
| Storage | External DB | Key-value + Forge SQL |
| Compliance | Requires vendor trust | Preferred model (Atlassian-hosted) |
| Status | **End of support Q4 2026** | Active, all new investment |

**Connect deprecation timeline:**
- No new Connect listings: September 17, 2025 — **PASSED**
- No Connect updates: March 31, 2026
- End of support: Q4 2026

**Action required:** audit Connect app dependencies; confirm vendors have Forge versions before Q4 2026.

### 2.8 Atlassian Guard (Security Layer)

- **Guard Standard** (SSO/SCIM/API-token control/audit log) — included free in Cloud Enterprise
- **Guard Premium** (data classification, content scanning/DLP, anomalous-activity threat detection, extended audit) — currently supports Jira and Confluence

---
