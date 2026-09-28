---
id: skill-8-message-formats-mt-to-iso-20022-2d848dc91f
purpose: 8 message formats mt to iso 20022
source: src/vibey_tools/skills/plugins/banking-swift-and-payment-networks/skills/banking-correspondent-swift-iso20022-and-governance/SKILL.md
requires: ["skill-7-what-swift-actually-is-705edb21f4"]
links: ["skill-9-gpi-and-tracking-6899cfdf15"]
---

## §8. ⚠️ Message Formats: MT to ISO 20022

```
⚠️ ⚠️ MT (the legacy format)  ⚠️ numbered message types with
   positional, tag-based fields. ⚠️ Compact, decades old, and
   SEVERELY LIMITED — short free-text fields, no structure for
   addresses or parties, and character-set restrictions
   ⚠️ MT103  customer credit transfer — ⚠️ the workhorse
   ⚠️ MT202  bank-to-bank transfer · MT202COV (cover payment)
   ⚠️ MT940/942  statements · MT101 payment initiation
⚠️ ⚠️ ISO 20022 / MX  ⚠️ XML, richly structured, extensible,
   with a shared data DICTIONARY across business domains
   ⚠️ pacs.008  customer credit transfer (replaces MT103)
   ⚠️ pacs.009  financial institution transfer (replaces MT202)
   ⚠️ pain.001  payment initiation · camt.*  cash management
   ⚠️ THE NAMING  business area . message . variant . version
⚠️ ⚠️ WHY IT ACTUALLY MATTERS — and it is not "XML is nicer"
   ⚠️ STRUCTURED PARTY AND ADDRESS DATA transforms sanctions
      screening and AML (§21) — ⚠️ unstructured free-text names
      are why false-positive rates are so high
   ⚠️ Richer remittance information enables automatic
      reconciliation, which is a real corporate cost saving
   ⚠️ End-to-end data survives the hops of §6 instead of being
      truncated
⚠️ ⚠️ THE TRUNCATION PROBLEM was the core argument for migration:
   ⚠️ data lost at one hop cannot be recovered downstream, so
   the whole chain must speak the richer format for anyone to
   benefit (§24.1)
```

---
