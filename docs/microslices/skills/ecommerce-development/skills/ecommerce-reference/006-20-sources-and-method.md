---
id: skill-20-sources-and-method-d80cf0ca69
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-reference/SKILL.md
requires: ["skill-19-quick-reference-47a309d270"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §1 → `ecommerce-payments-architecture-and-integration` (architecture),
§2 → `ecommerce-payments-architecture-and-integration` (payment lifecycle), §3 → `ecommerce-payments-architecture-and-integration` (integration engineering), §7.1 → `ecommerce-payment-methods-sca-fraud-and-pci`, §9 → `ecommerce-billing-tax-platforms-and-checkout`, §13.2 → `ecommerce-billing-tax-platforms-and-checkout`, §15 — rests on
distributed-systems fundamentals, provider documentation that has been stable for years,
and failure patterns reported consistently across practitioners. Every **time-sensitive**
claim (PCI deadlines, PSD3/PSR timing, agentic protocol state, API behaviour) was verified
against a primary or near-primary source in **August 2026** and is flagged in §17 with a
decay-risk rating. Where sources conflict — notably PSD3/PSR application dates — **the
conflict is reported rather than resolved**.

**Search log** (August 2026): PCI DSS 4.0.1 e-commerce requirements and the SAQ A changes ·
agentic commerce protocols (ACP, AP2, UCP, x402, MPP) and adoption · PSD3/PSR timeline,
SCA, and Verification of Payee · payment integration engineering (idempotency, webhooks,
reliability).

**Primary and near-primary sources consulted (selected):**
- **PCI Security Standards Council blog** — "Important Updates Announced for Merchants
  Validating to SAQ A" (Jan 2025), the **28 Feb 2025 FAQ** on the new eligibility criterion,
  and the Coffee with the Council episode on post-31-March-2025 e-commerce guidance;
  plus **TrustedSec**, **Akamai**, **SecurityMetrics**, and **Feroot** on the practical
  implications and the SAQ A eligibility trap
- **Stripe documentation** — idempotent requests, advanced error handling, server-side
  integration, and the agentic commerce materials; **agenticcommerce.dev** and the **ACP
  spec repository** for the revision history
- **Forrester** ("Agentic Payments In B2C Commerce: Where We Are Now") on Instant Checkout
  adoption; multiple independent reports on its **5 March 2026** retirement and the **AP2
  → FIDO Alliance donation (28 April 2026)**
- **Morrison Foerster**, **Arthur Cox**, **Norton Rose Fulbright**, **Herbert Smith
  Freehills Kramer**, **PwC Legal**, and **Worldline** on PSD3/PSR scope and timing;
  **openbankingtracker** and **GR4VY** on the developer-facing implications and the
  VoP/Instant Payments Regulation distinction
- Practitioner write-ups on webhook and idempotency failure modes, including documented
  cases of triple event delivery and the resulting double-provisioning

**Confidence statement.** **High confidence** in §2 → `ecommerce-payments-architecture-and-integration`, §3 → `ecommerce-payments-architecture-and-integration`, §5.1 → `ecommerce-payment-methods-sca-fraud-and-pci`–5.2, §7 → `ecommerce-payment-methods-sca-fraud-and-pci`, §9 → `ecommerce-billing-tax-platforms-and-checkout`, §13 → `ecommerce-billing-tax-platforms-and-checkout` and §19's
integration guidance — these rest on provider documentation, distributed-systems
fundamentals, and failure modes reported consistently by many independent practitioners.
**High confidence** in the PCI DSS dates and the substance of the SAQ A change, which come
from the PCI SSC's own announcements and FAQ. **Low-to-moderate confidence on PSD3/PSR
application dates specifically** (§17): six credible law-firm and industry sources give
materially different figures — 18, 21, and 27 months post-entry-into-force, and "realistic"
dates from late 2027 through Q2/Q3 2028 — because the texts were still in legal-linguistic
review and Official Journal publication timing was unsettled at the time of writing.
**I have reported the spread; verify against the published text before making a compliance
plan.** **Moderate confidence on §14 → `ecommerce-billing-tax-platforms-and-checkout`'s agentic landscape**: it is the fastest-moving
material here, much of it comes from vendor announcements and trade coverage with obvious
promotional incentives, and I have deliberately foregrounded the disconfirming evidence
(the Instant Checkout retirement, Forrester's adoption data) because the promotional
material substantially outweighs it in volume. **The §5.3 → `ecommerce-payment-methods-sca-fraud-and-pci` note on ISO 20022 is deliberately
undated** — migration deadlines differ by scheme and I did not verify them; check your
specific rail. Nothing here is legal, tax, or financial advice; §8 → `ecommerce-payment-methods-sca-fraud-and-pci` and §11 → `ecommerce-billing-tax-platforms-and-checkout` identify the
questions to put to your counsel and acquirer, not the answers.
