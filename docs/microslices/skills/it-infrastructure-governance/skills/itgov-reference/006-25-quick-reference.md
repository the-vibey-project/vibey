---
id: skill-25-quick-reference-762432b464
purpose: 25 quick reference
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-reference/SKILL.md
requires: ["skill-24-books-21e4cdfe78"]
links: ["skill-26-method-2ea6355ed0"]
---

## §25. Quick Reference

### 25.1 Picker
| Question | Where |
|---|---|
| Where should access decisions be enforced? | ⚠️ **Identity layer, not network** (§6 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| Is our MFA good enough? | ⚠️ **Is it phishing-resistant? If not, no** (§6 → `itgov-directory-authentication-authorization-and-privileged-access`, §21.1) |
| Why do we have 900 roles? | ⚠️ **Role explosion — split business roles from entitlements** (§7 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| How do we cut standing privilege? | ⚠️ **JIT elevation + PAM vaulting** (§8 → `itgov-directory-authentication-authorization-and-privileged-access`) |
| Where does privilege creep come from? | ⚠️ **The mover case** (§9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`) |
| Our access reviews are meaningless | ⚠️ **Risk-scope, owner-review, plain language** (§10 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`) |
| Is this backup adequate? | ⚠️ **3-2-1-1-0, and restore-test it** (§13 → `itgov-endpoints-continuity-itsm-and-vendor-risk`) |
| Who owns this service account? | ⚠️ **If nobody, that's the finding** (§8 → `itgov-directory-authentication-authorization-and-privileged-access`, §21.2) |
| How many machine identities do we have? | ⚠️ **Inventory first — most orgs cannot answer** (§21.2) |
| Which framework should we adopt? | ⚠️ **CIS Controls IG1 to start** (§17 → `itgov-endpoints-continuity-itsm-and-vendor-risk`) |
| Small team, can't separate duties | ⚠️ **Compensating detective controls, honestly documented** (§11 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`) |

### 25.2 Access governance health check
- [ ] Can you enumerate every account, human and non-human? (§16 → `itgov-endpoints-continuity-itsm-and-vendor-risk`, §21.2)
- [ ] ⚠️ **Does every privileged account have a named human owner?** (§8 → `itgov-directory-authentication-authorization-and-privileged-access`, §21.2)
- [ ] Is standing privileged access eliminated or minimized? (§8 → `itgov-directory-authentication-authorization-and-privileged-access`)
- [ ] ⚠️ **Do role changes trigger revocation review, not just grants?** (§9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`)
- [ ] Are leavers deprovisioned from non-SSO systems too? (§9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`)
- [ ] Do contractor accounts have expiry dates set at creation? (§9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`)
- [ ] Are reviews risk-scoped and in plain language? (§10 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`)
- [ ] ⚠️ **Are privileged accounts on phishing-resistant MFA?** (§6 → `itgov-directory-authentication-authorization-and-privileged-access`, §21.1)
- [ ] Is legacy authentication disabled? (§5 → `itgov-directory-authentication-authorization-and-privileged-access`)
- [ ] Are break-glass accounts tested and monitored? (§6 → `itgov-directory-authentication-authorization-and-privileged-access`)
- [ ] ⚠️ **Have you restore-tested a full system this year?** (§13 → `itgov-endpoints-continuity-itsm-and-vendor-risk`)
- [ ] Are logs forwarded off-host and tamper-resistant? (§14 → `itgov-endpoints-continuity-itsm-and-vendor-risk`)
- [ ] Are third-party OAuth grants and API tokens reviewed? (§19 → `itgov-endpoints-continuity-itsm-and-vendor-risk`, §21.2)

---
