---
id: skill-the-saltzer-schroeder-eight-principles-d6169a079e
purpose: the saltzer schroeder eight principles
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-the-insight-that-matters-most-37b5834963"]
links: ["skill-the-cia-triad-what-security-protects-2f84706f8a"]
---

## The Saltzer-Schroeder eight principles

### 1. Least Privilege
Every user, program, and system component should operate with the minimum permissions necessary to accomplish its task.

**Why it exists**: excessive permissions mean any compromise of that account or component immediately grants the attacker excessive power.

**Real-world violations**:
- **Target 2013**: An HVAC vendor's billing credentials provided a path to point-of-sale systems at 1,797 stores because the vendor portal sat on the same network. Access far exceeded what HVAC maintenance required. Estimated cost: $162 million.
- **SolarWinds 2020**: The Orion platform required unrestricted global administrator access to function, creating the perfect vector for distributing SUNBURST malware to 18,000 customers including the Pentagon and FBI.

**The data**: Forrester estimates 80% of security breaches involve privileged credentials. Non-human identities (service accounts, API tokens) now outnumber human identities 80:1, expanding the privileged attack surface dramatically.

**Practical implementation**: just-in-time access (elevate only for specific tasks, auto-revoke after), zero standing privileges for humans, credential vaulting, session monitoring.

### 2. Fail-Safe Defaults
Access should be denied unless explicitly granted. Systems should default to a safe state when they fail.

**Why it exists**: it is far easier to enumerate what should be permitted than to enumerate all possible harmful actions.

**The physical tension**: Fail-safe locks (fail-open) unlock during power loss — safe for people exiting, dangerous for the space. Fail-secure locks (fail-closed) stay locked during power loss — safe for the space, potentially dangerous for trapped occupants. In digital systems, a firewall that fails open exposes the entire network; one that fails closed blocks all legitimate traffic. The correct choice depends on which failure mode is more catastrophic for the specific context.

**Implementation**: default-deny firewall rules, default-deny Kubernetes NetworkPolicy, deny-all IAM policies with explicit allow statements.

### 3. Open Design (Kerckhoffs's Principle)
Security must not depend on attacker ignorance of the design. The only secret element should be the key.

**History**: Auguste Kerckhoffs articulated this in 1883: a cryptosystem should be secure even if everything about the system except the key is public knowledge. Claude Shannon restated it as "the enemy knows the system."

**Why it matters**: source code leaks, hardware gets reverse-engineered, decompilers expose implementation details, employees leave, and disgruntled insiders exist. Security through obscurity fails the moment the secret is exposed — and eventually all secrets are exposed.

**Violations**: proprietary algorithms, relying on internal network architecture remaining hidden, trusting that attackers do not know your system architecture.

### 4. Separation of Privilege
No single entity should hold all-powerful access. Critical operations should require multiple conditions or actors.

**Why it exists**: compromise of any single entity should not grant total control.

**Shostack's observation**: "the most ignored principle" — over thirty years after its articulation, every major operating system still ships with an all-powerful root account.

**Implementation**: multi-person authorization for production deployments, split knowledge for cryptographic keys, separation of duties between developers and production access, break-glass accounts with multi-party authorization.

### 5. Complete Mediation
Check every access to every object every time. Do not cache permission checks.

**Why it exists**: caching permissions creates TOCTOU (Time-of-Check to Time-of-Use) vulnerabilities. Permission state can change between when it was checked and when it is used.

**Practical failure mode**: a system checks that a user is authorized when they log in, but that user's permissions are later revoked. If the system cached the initial check, the revoked user retains access until cache expiration.

**Implementation**: re-check authorization on every sensitive request, use short-lived tokens rather than long-lived sessions, revocation must propagate immediately.

### 6. Economy of Mechanism
Keep security mechanisms simple. Complex systems hide flaws.

**Why it exists**: security flaws in complex code go unnoticed because normal use does not exercise improper access paths. Complexity is the enemy of security.

**Practical implication**: prefer simple, well-audited libraries over complex in-house implementations. "Don't roll your own crypto" is a direct application of this principle — and of Kerckhoffs's.

**Schneier's Law**: "Anyone can create an algorithm that he himself can't break. What is hard is creating an algorithm that no one else can break, even after years of analysis."

### 7. Least Common Mechanism
Minimize shared mechanisms between users. Shared mechanisms are potential channels for information flow between users.

**Why it exists**: shared state is a side-channel. If two users share a caching mechanism, cache timing can leak information from one user's activity to another's.

**Modern relevance**: side-channel attacks (Spectre, Meltdown) exploit shared CPU caches and speculative execution. Container security (containers share the host kernel) applies this principle — shared kernel means container escapes are a critical threat class.

### 8. Psychological Acceptability
Security mechanisms people cannot use, they will circumvent. Usability is a security property, not a concession.

**Why it exists**: an unusable security control achieves nothing. Users route around it.

**Classic failure**: complex password requirements produce sticky notes on monitors and incremental predictable patterns (Password1! → Password2!). NIST SP 800-63B revised guidance to reflect this: focus on length over complexity, do not mandate rotation unless compromise suspected.

**The FireEye/Target case**: FireEye alerts about the malware were never investigated. The alert mechanism was technically functional but psychologically overwhelming — alert fatigue caused the SOC team to ignore real alerts. A technically correct control failed due to psychological acceptability failure.
