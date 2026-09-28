---
id: skill-18-the-canon-829f69bb7e
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-8d8b8883e3"]
links: ["skill-19-quick-reference-47a309d270"]
---

## §18. The Canon

### 18.1 Primary documentation — read these directly
- **Stripe Docs** — genuinely the best payments documentation in existence, and useful even
  if you use another provider. Specifically: the **idempotency**, **advanced error
  handling**, and **webhook** pages, and **stripe.com/blog/idempotency** (a foundational
  essay on designing robust APIs).
- **PCI Security Standards Council** — the **Document Library** (PCI DSS v4.0.1, the SAQs),
  the **blog** (where the SAQ A changes and FAQs were announced), and the **E-commerce
  Guidance** from the task force.
- **PayPal Developer**, **Adyen Docs** (excellent on local payment methods and auth-rate
  optimization), **Braintree**, **Shopify Dev** (Admin and Storefront APIs, Functions).
- **EMVCo** for 3-D Secure specifications; **EBA** guidelines and **RTS on SCA**;
  the **Official Journal** for PSD3/PSR once published.
- **Agentic Commerce Protocol** (`agenticcommerce.dev`, and the spec repo),
  **AP2** via the FIDO Alliance, **UCP**.
- **ISO 20022** documentation and your specific scheme's migration guidance (§5.3 → `ecommerce-payment-methods-sca-fraud-and-pci`).

### 18.2 Books and long-form
| Author | Work | Why |
|---|---|---|
| **Pethuru Raj / various** | — | *(payments has no single canonical textbook — this is a docs-first field)* |
| **Baymard Institute** | Checkout and e-commerce UX research | **The empirical reference for §13.2 → `ecommerce-billing-tax-platforms-and-checkout`.** Their cart-abandonment and checkout-usability studies are the actual data behind most conversion advice |
| **Sam Newman** | *Building Microservices* | §1.3 → `ecommerce-payments-architecture-and-integration`'s sagas, outbox, and consistency patterns |
| **Martin Kleppmann** | ***Designing Data-Intensive Applications*** | The distributed-systems reasoning under §3 → `ecommerce-payments-architecture-and-integration` |
| **Martin Fowler** | *Patterns of Enterprise Application Architecture*; the **Money pattern** and **Ledger/Event Sourcing** material on martinfowler.com | §2.2 → `ecommerce-payments-architecture-and-integration` and §3.3 → `ecommerce-payments-architecture-and-integration` |
| **Gregor Hohpe & Bobby Woolf** | *Enterprise Integration Patterns* | Still the reference for webhook/messaging design |
| **"Payments Systems in the U.S."** (Carol Coye Benson et al.) | — | The clearest plain-English explanation of how the rails actually work |

### 18.3 Sites and people
**Baymard Institute** (checkout research), **Patrick McKenzie / patio11** (`kalzumeus.com`
and Bits about Money — **the best writing anywhere on how payments actually work
commercially**), **Stripe's engineering blog**, **Adyen's technical blog**,
**a16z fintech** and **Fintech Brainfood** (Simon Taylor) for market structure,
**The Paypers** and **PYMNTS** for industry news, **Merchant Risk Council** for fraud and
disputes, **Nilson Report** for card industry data, and **DefiLlama-style** trackers on the
crypto side. **OWASP** for the application-security layer of checkout.

---
