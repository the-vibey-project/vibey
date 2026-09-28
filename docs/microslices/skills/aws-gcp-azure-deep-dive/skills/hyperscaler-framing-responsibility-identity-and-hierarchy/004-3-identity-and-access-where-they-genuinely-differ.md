---
id: skill-3-identity-and-access-where-they-genuinely-differ-a654d76446
purpose: 3 identity and access where they genuinely differ
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-framing-responsibility-identity-and-hierarchy/SKILL.md
requires: ["skill-2-shared-responsibility-f384841a8e"]
links: ["skill-4-resource-hierarchy-and-organization-c86da8c67a"]
---

## §3. ⚠️ Identity and Access — Where They Genuinely Differ

**⚠️ This is the section that matters most, and it's the one most comparisons skip.**
**IAM is where the three clouds are least alike, hardest to translate between, and where
mistakes are most consequential.**

### 3.1 AWS
```
Principals   users, roles, and ⚠️ ROLES ARE THE IMPORTANT ONE — an identity that
             is ASSUMED temporarily via STS, producing short-lived credentials
Policies     ⚠️ JSON documents. Identity-based (attached to principal) and
             RESOURCE-based (attached to the resource — S3 bucket policies, KMS
             key policies). ⚠️ BOTH must allow; either can deny
Boundaries   permissions boundaries, SCPs (Service Control Policies) at org level,
             session policies — ⚠️ these INTERSECT, they don't add
Evaluation   ⚠️ explicit DENY always wins → then explicit ALLOW → else implicit deny
```
> **⚠️ GOTCHA — AWS policy evaluation is genuinely hard to reason about, and this is not
> a skill issue.** ⚠️ **An effective permission is the INTERSECTION of the identity
> policy, any resource policy, the permissions boundary, the SCP, and the session policy
> — and any single explicit Deny anywhere overrides every Allow.** **People routinely
> grant a permission and find it doesn't work, or believe they've revoked one and find it
> still does.**
> **⚠️ Use the IAM policy simulator and Access Analyzer rather than reasoning by hand.**

### 3.2 Azure
```
Identity     ⚠️ Microsoft Entra ID (formerly Azure AD) — SEPARATE from the Azure
             resource plane, and this separation is the thing to internalize
Two systems  ⚠️ Entra ROLES govern the directory (users, groups, apps).
             AZURE RBAC governs resources (subscriptions, RGs, resources).
             ⚠️ They are DIFFERENT SYSTEMS with different role definitions
RBAC model   role definitions + scope + principal = role assignment.
             ⚠️ Scopes INHERIT downward: mgmt group → subscription → RG → resource
Deny         ⚠️ Azure RBAC is ADDITIVE — assignments accumulate. Deny assignments
             exist but are limited. Azure Policy is the usual guardrail
Managed identities  ⚠️ system-assigned vs user-assigned. The right way to avoid secrets
```
> **⚠️ GOTCHA — the Entra-vs-Azure-RBAC split confuses almost everyone at first.**
> ⚠️ **Being Global Administrator in Entra does NOT by itself give you access to Azure
> resources**, and **an Azure Owner is not necessarily able to manage the directory.**
> **There is an elevation path, deliberately.** **Treat them as two separate authorization
> systems that happen to share a principal store.**

### 3.3 GCP
```
Hierarchy    ⚠️ Organization → Folders → Projects → Resources. Policy INHERITS
             downward and the PROJECT is the primary unit of isolation
Members      users, groups, service accounts, ⚠️ and service accounts are BOTH an
             identity AND a resource you grant access TO — which is unusual and
             a common source of confusion
Roles        basic (⚠️ Owner/Editor/Viewer — too broad, avoid), predefined, custom
Binding      policy = set of bindings (role → members) attached at a hierarchy node
Deny         ⚠️ IAM Deny policies exist and are relatively recent; the model is
             otherwise additive-with-inheritance
```
> **⚠️ GOTCHA — GCP inheritance is additive and cannot be reduced by a lower level in the
> base model.** ⚠️ **Granting a role at the organization or folder level grants it on
> everything beneath, and a project-level policy cannot take it away.** **Which is why
> broad grants high in the hierarchy are the classic GCP privilege mistake.**

### 3.4 ⚠️ The comparison that matters
| | AWS | Azure | GCP |
|---|---|---|---|
| Primary isolation unit | ⚠️ **Account** | ⚠️ **Subscription** | ⚠️ **Project** |
| Policy language | JSON policies | Role definitions | Role bindings |
| Inheritance | ⚠️ Via SCPs, intersecting | ⚠️ Scope hierarchy, additive | ⚠️ Hierarchy, additive |
| Resource-attached policy | ⚠️ **Yes — significant** | Limited | Limited |
| Temporary credentials | ⚠️ **STS/AssumeRole, central** | Managed identities | Service account impersonation |
| Deny semantics | ⚠️ **Explicit deny always wins** | Mostly additive | Mostly additive |

**⚠️ Universal principles regardless of platform** (see an IT governance reference §7–§9):
**no long-lived static credentials — use workload identity federation, roles, or managed
identities**; **least privilege, granted at the narrowest scope**; **separate accounts /
subscriptions / projects per environment**; ⚠️ **MFA and phishing-resistant methods on
every human with production access**; **and periodic access review, because the grants
accumulate and never expire on their own.**

---
