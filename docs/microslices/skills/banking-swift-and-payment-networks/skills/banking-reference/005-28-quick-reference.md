---
id: skill-28-quick-reference-6a27dffd1f
purpose: 28 quick reference
source: src/vibey_tools/skills/plugins/banking-swift-and-payment-networks/skills/banking-reference/SKILL.md
requires: ["skill-27-sources-2cd2839ae9"]
links: ["skill-29-method-2cdcbd1d32"]
---

## §28. Quick Reference

### 28.1 Picker
| Question | Where |
|---|---|
| Why did my international payment take days? | ⚠️ **Correspondent hops, cut-offs, screening — not SWIFT** (§6 → `banking-correspondent-swift-iso20022-and-governance`) |
| What does SWIFT actually do? | ⚠️ **Messaging. Not settlement** (§7 → `banking-correspondent-swift-iso20022-and-governance`) |
| Is this payment final? | ⚠️ **A legal question, not a screen** (§5 → `banking-payments-banks-reserves-and-settlement`) |
| Why is remittance so expensive? | ⚠️ **On-ramp, off-ramp, FX spread** (§23 → `banking-compliance-security-and-remittance-costs`) |
| Does "bank partners with Ripple" mean XRP? | ⚠️ **Usually no. Check the transaction path** (§12 → `banking-ripple-xrp-ledger-and-honest-assessment`, §24.2) |
| Stablecoin or tokenized deposit? | ⚠️ **Issuer claim vs bank liability** (§18 → `banking-instant-payments-stablecoins-cbdcs-and-tokenization`, §20 → `banking-instant-payments-stablecoins-cbdcs-and-tokenization`) |
| Are we ISO 20022 compliant? | ⚠️ **Ask if you're NATIVE or translating** (§24.1) |
| What breaks in November 2026? | ⚠️ **Unstructured addresses, MT101 relay** (§24.1) |
| Why so many false compliance alerts? | ⚠️ **Unstructured name matching** (§8 → `banking-correspondent-swift-iso20022-and-governance`, §21 → `banking-compliance-security-and-remittance-costs`) |
| Why did the bank exit that country? | ⚠️ **De-risking. Penalty exceeded profit** (§6 → `banking-correspondent-swift-iso20022-and-governance`, §21 → `banking-compliance-security-and-remittance-costs`) |
| Was SWIFT hacked? | ⚠️ **In the famous case, no — the endpoint was** (§22 → `banking-compliance-security-and-remittance-costs`) |

### 28.2 Evaluating a payments claim
- [ ] ⚠️ **Is this about MESSAGING or SETTLEMENT?** (§1 → `banking-payments-banks-reserves-and-settlement`, §7 → `banking-correspondent-swift-iso20022-and-governance`)
- [ ] ⚠️ **What provides FINALITY, and under whose law?** (§5 → `banking-payments-banks-reserves-and-settlement`)
- [ ] Does it remove pre-funding, or just re-describe it? (§6 → `banking-correspondent-swift-iso20022-and-governance`)
- [ ] ⚠️ **For crypto claims: is the TOKEN in the transaction path?** (§12 → `banking-ripple-xrp-ledger-and-honest-assessment`)
- [ ] Pilot, MOU, or production volume? (§16 → `banking-ripple-xrp-ledger-and-honest-assessment`)
- [ ] ⚠️ **Who published the figure, and what do they hold?** (§16 → `banking-ripple-xrp-ledger-and-honest-assessment`, §24.2)
- [ ] Does it handle the on-ramp and off-ramp, or assume them? (§23 → `banking-compliance-security-and-remittance-costs`)
- [ ] ⚠️ **How does compliance screening work in it?** (§21 → `banking-compliance-security-and-remittance-costs`)
- [ ] What happens when a party fails mid-transaction? (§5 → `banking-payments-banks-reserves-and-settlement`)
- [ ] ⚠️ **Is the comparison against gpi and instant rails, or against 2015?** (§9 → `banking-correspondent-swift-iso20022-and-governance`, §17 → `banking-instant-payments-stablecoins-cbdcs-and-tokenization`)

---
