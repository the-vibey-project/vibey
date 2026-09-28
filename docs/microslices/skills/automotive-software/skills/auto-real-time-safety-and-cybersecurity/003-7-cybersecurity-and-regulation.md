---
id: skill-7-cybersecurity-and-regulation-e0856c030b
purpose: 7 cybersecurity and regulation
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-real-time-safety-and-cybersecurity/SKILL.md
requires: ["skill-6-functional-safety-iso-26262-6140994c36"]
links: []
---

## §7. Cybersecurity and Regulation

### 7.1 ISO/SAE 21434 — the engineering standard
**Covers the full lifecycle**: cybersecurity governance, **TARA (Threat Analysis and Risk
Assessment)** producing **CAL** ratings, secure development, production, **operations and
incident response**, and decommissioning.
⚠️ **The structural parallel to ISO 26262 is deliberate — TARA is to security what HARA is
to safety.**

### 7.2 ⚠️ UN R155 and R156 — the regulations that gate market access

**[VERSIONED — §17.1 → `auto-reference`.]** **These are not guidance. They are type-approval conditions.**
- **⚠️ R155 requires a certified Cyber Security Management System (CSMS)**; **R156 requires
  a certified Software Update Management System (SUMS).** **Both must be audited and
  certified by a designated technical service** — ⚠️ **without them, the vehicle is not
  granted type approval.**
- ⚠️ **R155 defines what must be achieved; ISO/SAE 21434 defines how**, and the regulation
  explicitly references it as a suitable framework. **But 21434 conformance alone does not
  guarantee R155 approval** — the regulation has its own requirements.
- **⚠️ Annex 5 of R155 enumerates 69 attack vectors that every threat analysis must
  address.** This is a checklist you will be audited against.
- **Certificates are valid for three years** and the OEM must **continuously monitor its
  own fleet and backend** and act on threats.

**⚠️ The consequence for engineering practice**: **security is now a market-access
requirement with an audit trail, applied across the supply chain.** You will be asked for
evidence by your customer because their type approval depends on it (§14 → `auto-process-testing-domains-and-supply-chain`).

### 7.3 Technical measures
**Secure boot** and chain of trust from an **HSM** (hardware security module — a
dedicated core in modern automotive MCUs), **SecOC** for authenticated in-vehicle
messages (§3.1 → `auto-architecture-buses-and-autosar`), **key management and provisioning at production**, **network segmentation
and a gateway** between the external-facing domain and the powertrain/chassis buses,
**intrusion detection (IDPS)**, and **secure diagnostics** — ⚠️ **UDS security access is
notoriously weak in legacy implementations (§8 → `auto-diagnostics-ota-and-adas`) and is a common attack path.**

**⚠️ The attack surface to reason about**: telematics unit and cellular, Bluetooth and
Wi-Fi, infotainment and its media parsers, key fob and passive entry (⚠️ **relay attacks**),
TPMS, charging (⚠️ **the EV charging interface is a new and under-hardened path**), OBD-II
port, and the supply chain itself.
