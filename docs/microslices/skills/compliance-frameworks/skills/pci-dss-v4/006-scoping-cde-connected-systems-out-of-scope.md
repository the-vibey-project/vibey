---
id: skill-scoping-cde-connected-systems-out-of-scope-d5a4044985
purpose: scoping cde connected systems out of scope
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/pci-dss-v4/SKILL.md
requires: ["skill-key-new-requirements-in-pci-dss-v4-0-a080aded5a"]
links: ["skill-key-technical-requirements-9878ff16ea"]
---

## Scoping: CDE, Connected Systems, Out-of-Scope

### Cardholder Data Environment (CDE)
All system components that store, process, or transmit cardholder data (CHD) or sensitive authentication data (SAD), plus the security controls that protect those systems.

**CHD includes:** Primary Account Number (PAN), cardholder name, expiration date, service code
**SAD includes:** Full magnetic stripe data, CVV/CVC, PIN blocks — SAD must NEVER be stored post-authorization

### Connected-to or Supporting
Systems that are not in the CDE but that:
- Connect to CDE systems
- Could impact the security of the CDE (e.g., AD domain controllers, patch management servers, monitoring systems, DNS)
These are IN SCOPE and must meet applicable requirements.

### Out-of-Scope Systems
Systems with no connectivity to the CDE and no ability to impact CDE security. Requires:
- Network segmentation (firewall/VLAN isolation from CDE)
- Validation that segmentation is effective (penetration testing at least annually)

### Scope Reduction Strategies

**Tokenization:**
- Replace PAN with a token after initial authorization
- Token has no exploitable value; only the tokenization system (vault) stores PAN
- Systems receiving only tokens are out of scope
- Providers: Braintree, Stripe, Bluesnap, First Data/Fiserv

**Point-to-Point Encryption (P2PE):**
- PCI-validated P2PE solution encrypts CHD at point of interaction (swipe/dip/tap)
- Encrypted data passes through merchant systems but cannot be decrypted there
- Dramatically reduces scope for card-present environments
- Merchant must use a PCI SSC-listed P2PE solution to claim scope reduction

---
