---
id: skill-21-what-moved-verified-august-2026-8c0fdd1272
purpose: 21 what moved verified august 2026
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-reference/SKILL.md
requires: ["skill-20-anti-patterns-fd49d45826"]
links: ["skill-22-misconceptions-6ceb4cacbe"]
---

## §21. What Moved — verified August 2026

### 21.1 ⚠️ Phishing-resistant authentication is becoming mandatory, on a timeline
**⚠️ The direction was already clear; what's new is enforcement dates and the retirement
of weak methods.**

**In the Microsoft ecosystem specifically** — **which matters because it's the dominant
enterprise identity platform:**
- **⚠️ Entra ID supports five phishing-resistant methods**: **Microsoft Authenticator
  phone sign-in, Windows Hello for Business (TPM-bound), FIDO2 security keys,
  certificate-based authentication (smart card / PIV), and passkeys** — **all of which
  satisfy phishing-resistant MFA when enforced through Conditional Access authentication
  strength.**
- **⚠️ Authentication Strengths is the mechanism.** **Three built-in strengths: MFA,
  Passwordless MFA, and Phishing-resistant MFA**, and ⚠️ **Microsoft publishes a
  Conditional Access template for requiring phishing-resistant MFA on admin roles**,
  which is the highest-value single policy in most tenants.
- **⚠️ SMS and voice authentication are being retired, reported as starting September
  2026.** **If an organization still depends on SMS, that is now a dated dependency with a
  deadline.**
- **⚠️ Several enforcement dates landed or land through 2026**: **from 6 July 2026,
  Conditional Access policies assigned to the "Register security information" action apply
  during Windows Hello for Business and macOS Platform SSO registration**; **enforcement
  reported as completing 13 July 2026**; **and from 7 September 2026 Self-Service Password
  Reset will accept only methods a user has actually registered.**

> **⚠️ GOTCHA — the deployment problem is bootstrapping, not technology, and it's where
> these projects stall.** ⚠️ **Registering a phishing-resistant credential requires
> authenticating with something, and a user who has nothing phishing-resistant yet must
> register using a weaker method** — **which is precisely the window an attacker wants.**
> **The pattern that addresses it: Temporary Access Pass or equivalent, issued through a
> verified channel, plus Conditional Access on the registration action itself** (which is
> what the July 2026 change enables). ⚠️ **And sequence the rollout by role — privileged
> accounts first, with hardware keys — rather than by convenience.**

**⚠️ Caveat on scope**: **the enforcement dates above are Microsoft-specific and drawn from
its own release notes and community reporting.** **Other IdPs are moving the same
direction on their own timelines**, and ⚠️ **the underlying driver is general: relay
phishing kits made non-phishing-resistant MFA insufficient, and insurers and regulators
have noticed.**

### 21.2 ⚠️ Non-human identities are now the majority of the identity estate
**⚠️ This is the biggest structural change to access governance, and it breaks assumptions
built into §9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties` and §10 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`.**

**⚠️ The numbers vary widely and I am going to be explicit about why.** **Reported
non-human-to-human identity ratios range from about 25:1 to 144:1 depending on source and
methodology:**
```
~45:1    commonly cited average enterprise figure (Rubrik Zero Labs)
~80:1    KPMG Cybersecurity Considerations 2026
~100:1   several vendor and survey sources
~144:1   cloud-native / DevOps environments (Entro Labs H1 2025),
         ⚠️ reported as up from 92:1 in H1 2024
```
> **⚠️ GOTCHA — treat every one of these figures with caution.** ⚠️ **Almost all of them
> originate from vendors selling non-human identity management products, and the
> methodologies are not comparable — what counts as an "identity" differs between
> studies.** **KPMG is the most independent source in that list.**
> ⚠️ **What is well-attested is the DIRECTION and the ORDER OF MAGNITUDE: NHIs are now the
> largest identity population in the enterprise by a wide margin, and the ratio is
> growing.** **Do not quote a specific multiple as fact; do act on the direction.**

**⚠️ Why NHIs break conventional IAM, which is the part that actually matters:**
- **⚠️ They cannot use MFA.** **The entire §6 → `itgov-directory-authentication-authorization-and-privileged-access` control stack assumes a human who can be
  challenged.**
- **⚠️ They never log out and are rarely retired.** **A credential issued for a 2019
  integration is still valid.** **One report found a majority of secrets confirmed exposed
  in 2022 were still valid four years later.**
- **⚠️ They frequently have no owner**, which means **§9 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`'s lifecycle and §10 → `itgov-identity-lifecycle-access-review-and-segregation-of-duties`'s
  certification have nobody to route to.**
- **⚠️ They are massively over-privileged** — **identities reportedly use a very small
  fraction of granted permissions on average.**
- **⚠️ Exposure is exploited fast**: **exposed cloud credentials have been reported
  exploited within an average of around 17 minutes, while a substantial share of
  organizations take over 24 hours to rotate them.**

**⚠️ Agentic AI is accelerating this rather than creating it.** **The service account
problem is decades old** (§8 → `itgov-directory-authentication-authorization-and-privileged-access`); **what agents add is volume, autonomy, and access breadth —
an agent that reads, decides and acts needs entitlements a conventional service account
wouldn't.** ⚠️ **Reported survey findings — that around 92% of organizations say current
IAM tooling cannot manage AI agent identities, while a much smaller share have implemented
any governing policy — are vendor-survey figures and should be read as indicative rather
than precise.** **The gap they describe is real.**

**⚠️ Concrete findings worth taking seriously**: **the Salesloft-Drift breach of August
2025 is the reference case for third-party integration token compromise** (§19 → `itgov-endpoints-continuity-itsm-and-vendor-risk`), and
⚠️ **one study of nearly 8,000 live Model Context Protocol servers reportedly found 40%
with no authentication at all** — **which, if approximately right, is a straightforward
consequence of new infrastructure being deployed faster than its security patterns
mature.**

**⚠️ What actually works, and it's an extension of §8 → `itgov-directory-authentication-authorization-and-privileged-access` rather than something new:**
```
1. ⚠️ INVENTORY first — you cannot govern what you can't enumerate. Scan for
   secrets, tokens, service accounts and integration grants across environments
2. ⚠️ ASSIGN A HUMAN OWNER to every non-human identity. This is the single
   highest-value control, because it makes §9 and §10 applicable
3. ⚠️ REPLACE long-lived static secrets with short-lived cryptographic identity —
   workload identity federation, SPIFFE/SPIRE, OIDC-based federation
4. RIGHTSIZE against actual usage; remove unused entitlements aggressively
5. ⚠️ DRIVE lifecycle from authoritative sources, same as humans (§9)
6. Monitor behaviour at runtime — NHIs have far more predictable patterns than
   humans, ⚠️ which makes anomaly detection MORE tractable, not less
```
⚠️ **Point 3 is the structural fix.** **Vaulting and rotating a static secret manages a
problem; eliminating the static secret removes it.**

---
