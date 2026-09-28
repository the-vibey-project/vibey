---
id: skill-11-tax-and-cross-border-c9972da7e1
purpose: 11 tax and cross border
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-billing-tax-platforms-and-checkout/SKILL.md
requires: ["skill-10-marketplaces-and-multi-party-payments-da2bffdb03"]
links: ["skill-12-the-platform-layer-ad4c530a06"]
---

## §11. Tax and Cross-Border

**[DURABLE] Sales tax is far harder than engineers expect, and it is a genuine liability
rather than a rounding concern.**

**US sales tax** post-*Wayfair* is **economic nexus**: you may owe in a state where you have
no physical presence, based on revenue or transaction thresholds that **vary by state**.
Roughly 11,000+ taxing jurisdictions, product-level taxability rules (is a digital download
taxable? is a candy bar food?), and origin- vs. destination-based sourcing.
**EU VAT**: destination-based for B2C digital services, with **OSS/IOSS** simplifying
registration; **reverse charge** for B2B with a valid VAT number (**validate it — VIES**).
Plus GST regimes in dozens of other countries with their own thresholds.

**[DURABLE] Use a tax engine** — Avalara, Vertex, Stripe Tax, TaxJar, Anrok. Hardcoded tax
rates are a liability, not a shortcut. **Or use a merchant of record (§4.1 → `ecommerce-payments-architecture-and-integration`) and make it
their problem** — which for small teams selling digital goods internationally is often the
correct engineering decision dressed as a commercial one.

**Cross-border also means**: customs and duties (**DDP vs. DDU** — surprise duty bills at
delivery are a top cause of refused deliveries and chargebacks), **restricted and sanctioned
parties screening**, local consumer-protection and returns law (the EU's 14-day withdrawal
right), data residency, and **currency**: present prices in local currency, decide who bears
FX risk, and note that **dynamic currency conversion is generally bad for the customer and
a conversion killer**.

**[VERSIONED] The European Accessibility Act's requirements for e-commerce services became
enforceable on 28 June 2025** — for services in scope, accessibility is now a legal
obligation in the EU, not a nice-to-have. Verify scope and exemptions for your business.

---
