---
id: skill-zero-trust-philosophy-history-and-what-it-is-not-153984fad2
purpose: zero trust philosophy history and what it is not
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-aaa-authentication-authorization-and-accounting-7fe93cb775"]
links: ["skill-defense-in-depth-e93f580d0c"]
---

## Zero Trust: philosophy, history, and what it is not

### Intellectual history

**Jericho Forum** (2003): argued that network perimeters were dissolving. The concept of "de-perimeterization" — systems must be able to stand alone because the perimeter cannot be trusted.

**Operation Aurora** (2009): Chinese APT attack on Google, Adobe, and others. Google's response was to launch **BeyondCorp** — the first major enterprise implementation of perimeter-less security. Three principles: connecting from a particular network must not determine accessible services; access is granted based on user and device context; all access must be authenticated, authorized, and encrypted.

**John Kindervag at Forrester** (2010): published "No More Chewy Centers: Introducing the Zero Trust Model." Three original concepts: access all resources securely regardless of location; adopt least-privilege with strict enforcement; inspect and log all traffic.

**NIST SP 800-207** (August 2020): catalyzed by the 2015 OPM breach exposing 22.1 million records. Formalized seven tenets (summarized):
1. All resources require authenticated access
2. All communication is secured regardless of location
3. Access is per-session, dynamically determined
4. The enterprise monitors all assets
5. Authentication and authorization are dynamic and strictly enforced
6. Maximum information collected about asset state

**Biden Executive Order on Cybersecurity** (2021) and **OMB Mandate M-22-09** (2022): required federal agencies to adopt Zero Trust by 2024.

### What Zero Trust is not

Zero Trust is an architecture and philosophy — never trust, always verify, assume breach — not a product to purchase. No single vendor delivers Zero Trust. It is the simultaneous application of several Saltzer-Schroeder principles: least privilege (minimum necessary access), complete mediation (verify every request), fail-safe defaults (deny unless explicitly permitted), open design (cryptographic identity, not network location).
