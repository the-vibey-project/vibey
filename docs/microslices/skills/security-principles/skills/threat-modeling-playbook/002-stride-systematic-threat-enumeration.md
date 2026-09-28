---
id: skill-stride-systematic-threat-enumeration-3d1ffad6be
purpose: stride systematic threat enumeration
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-what-threat-modeling-is-and-why-it-exists-cb4cb99582"]
links: ["skill-pasta-risk-centric-threat-modeling-cec8d3db65"]
---

## STRIDE: systematic threat enumeration

**STRIDE** was developed in 1999 by Loren Kohnfelder and Praerit Garg at Microsoft. It maps six threat categories to the security property each violates.

| Threat | Violated Property | Core Question |
|--------|------------------|---------------|
| **S**poofing | Authentication | Can someone pretend to be something they are not? |
| **T**ampering | Integrity | Can someone modify data or code without authorization? |
| **R**epudiation | Non-repudiation | Can someone deny performing an action they actually performed? |
| **I**nformation Disclosure | Confidentiality | Can someone access information they should not? |
| **D**enial of Service | Availability | Can someone prevent legitimate use of the system? |
| **E**levation of Privilege | Authorization | Can someone gain capabilities they should not have? |

### How to apply STRIDE

**Step 1: Draw a Data Flow Diagram (DFD)**

A DFD has four element types:
- **External entities** (rectangles): actors outside the system boundary — users, external services, third-party APIs
- **Processes** (circles/ovals): code that transforms data — services, functions, components
- **Data stores** (parallel lines): where data rests — databases, queues, caches, files
- **Data flows** (arrows): how data moves between elements — API calls, database queries, network packets

**Step 2: Draw trust boundaries**

Trust boundaries are where the level of trust changes. Mark them with a dashed line. Common trust boundaries:
- The network perimeter (inside vs. outside the VPN/firewall)
- Between user-controlled code and server-side code
- Between services with different permission levels
- Between admin and non-admin contexts
- Between public API and internal API

**Step 3: Apply STRIDE to each element**

Not all STRIDE categories apply to all elements:

| Element Type | Applicable STRIDE |
|-------------|-------------------|
| External entity | Spoofing, Repudiation |
| Process | All six |
| Data store | Tampering, Information Disclosure, Denial of Service |
| Data flow | Tampering, Information Disclosure, Denial of Service |

**Step 4: Risk-filter the threats**

Apply simple risk scoring: Likelihood (High/Medium/Low) × Impact (High/Medium/Low). Focus on High×High and High×Medium. This addresses STRIDE's main limitation — "threat explosion" — which generates enormous numbers of threats, many low-priority.

### STRIDE in practice: worked example

**System**: A payment service that accepts card data from a mobile app, validates it, and calls an external payment processor.

Data flows:
1. Mobile app → Payment API (HTTPS)
2. Payment API → Card Validator (internal gRPC)
3. Payment API → Payment Processor (external HTTPS)
4. Payment API → Audit Log (write-only database)

Trust boundaries: mobile app / internet / internal services / external processor

STRIDE analysis on "Mobile app → Payment API":
- **Spoofing**: Can a malicious app impersonate a legitimate one? → Mitigation: certificate pinning, app attestation
- **Tampering**: Can amounts or card data be modified in transit? → Already mitigated by HTTPS with certificate validation
- **Repudiation**: Can a fraudulent user deny making a payment request? → Mitigation: request signing with user credential, audit log write
- **Information Disclosure**: Can card data be exposed in transit? → Already mitigated by TLS; also consider: are we logging card numbers in error logs?
- **Denial of Service**: Can the API be flooded? → Mitigation: rate limiting per user, per IP, per device fingerprint
- **Elevation of Privilege**: Can a regular user trigger admin-only flows? → Mitigation: scope validation on every endpoint
