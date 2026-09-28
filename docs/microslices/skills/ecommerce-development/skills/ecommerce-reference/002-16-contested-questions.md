---
id: skill-16-contested-questions-e3d9ce0f7a
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-reference/SKILL.md
requires: ["skill-15-anti-patterns-989a3eeeb0"]
links: ["skill-17-currency-snapshot-verified-august-2026-8d8b8883e3"]
---

## §16. Contested Questions

**16.1 Platform vs. headless vs. custom.** §12 → `ecommerce-billing-tax-platforms-and-checkout`. The genuine test is whether the templating
layer is actually constraining you, and whether you have a team to own the integration
layer permanently.

**16.2 One PSP or several.** *Single*: simpler, better rates through volume, one
reconciliation. *Multiple (via orchestration)*: redundancy if a provider has an incident or
freezes your account, better auth rates via routing, and negotiating leverage. **The
break-even is lower than most teams assume once payment volume is material** — but the
operational cost of two reconciliations is real.

**16.3 Merchant of record vs. doing it yourself.** §4.1 → `ecommerce-payments-architecture-and-integration`, §11 → `ecommerce-billing-tax-platforms-and-checkout`. Higher rate versus owning
global tax registration and remittance. **For a small team selling digital goods
internationally, MoR is frequently the correct answer** and is dismissed too quickly on
headline rate alone.

**16.4 How aggressive to be on fraud.** §7.1 → `ecommerce-payment-methods-sca-fraud-and-pci`. There is no neutral setting; you are choosing
where to sit on a curve with two costs.

**16.5 Is agentic commerce real yet?** §14.3 → `ecommerce-billing-tax-platforms-and-checkout` — and the evidence genuinely cuts both ways.
The infrastructure is being built at enormous scale; the flagship consumer implementation
was withdrawn six months after launch with low, stagnant adoption.

**16.6 Reserve inventory when?** Cart, checkout start, or order. Customer experience versus
overselling risk versus hoarding. **Genre-dependent**: limited-drop retail and grocery want
opposite answers.

**16.7 Build a ledger, or trust the PSP's reporting?** *PSP*: less to build; they're the
system of record for money that moved. *Own ledger*: multi-PSP, multi-currency, marketplace
splits, and auditability all need it. **The threshold at which you need your own is lower
than it feels — and retrofitting is brutal (§3.3 → `ecommerce-payments-architecture-and-integration`).**

---
