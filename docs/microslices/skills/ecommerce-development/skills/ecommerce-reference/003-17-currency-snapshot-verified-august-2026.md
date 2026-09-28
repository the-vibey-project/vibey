---
id: skill-17-currency-snapshot-verified-august-2026-8d8b8883e3
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-reference/SKILL.md
requires: ["skill-16-contested-questions-e3d9ce0f7a"]
links: ["skill-18-the-canon-829f69bb7e"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **PCI DSS v4.0.1** | ⚠️ **All 51 future-dated requirements became mandatory 31 March 2025.** No remaining transition phase; **v4.0.1 is the only active version**. Key e-commerce ones: **6.4.3** (payment page scripts authorized, integrity-checked, inventoried) and **11.6.1** (change/tamper detection, evaluated **at least weekly**) | Low |
| **The SAQ A change** | ⚠️ **January 2025: PCI SSC removed 6.4.3, 11.6.1, and 12.3.1 from SAQ A** — and added an **eligibility criterion** that the merchant confirm **"their site is not susceptible to attacks from scripts that could affect the merchant's e-commerce system(s)."** **Scope widened from the payment page to the entire website.** Merchants using redirects, previously out of scope, must now verify all scripts. **Cannot confirm it → not SAQ A eligible → SAQ A-EP.** October 2024 SAQ A retired 31 Mar 2025; January 2025 (r1) took effect same day. **28 Feb 2025 FAQ** gives two routes: implement the controls anyway, or get **written confirmation from a compliant third-party provider** | Medium |
| **PSD3 / PSR** | Provisional political agreement **27 November 2025**; final compromise texts agreed **~22–23 April 2026**. ⚠️ **Application dates are reported inconsistently** — sources cite PSR applying **18, 21, or 27 months** after entry into force, with "realistic compliance" placed variously at **late 2027, Q1 2028, or Q2/Q3 2028**; **Verification of Payee provisions generally later (~27 months)**. **Verify against the Official Journal text** | **High** |
| **What PSD3/PSR changes** | Merges PSD2 and EMD2; **PSR is directly applicable** (removes cross-member-state variation). **Fraud liability shifts** — PSPs liable where prevention is inadequate; **APP fraud treated as unauthorized** with reimbursement; **impersonation/spoofing refund right**; mandatory **transaction monitoring**; PSPs may share IBAN fraud data. **⚠️ Delegating SCA to a third party is formal outsourcing** → EBA outsourcing guidelines + DORA | Medium |
| **3-D Secure** | **The protocol itself is not changing** under PSD3/PSR. Expect **expanded SCA triggers** (new token creation, spending-limit changes) | Medium |
| **Verification of Payee** | ⚠️ **Already mandatory since 9 October 2025** for euro-area PSPs under the separate **Instant Payments Regulation** (non-euro-area by **July 2027**). **PSD3/PSR did not create it** — it extends it to all credit transfers, any currency. Common point of confusion | Low |
| **European Accessibility Act** | **Enforceable since 28 June 2025** for in-scope services including e-commerce | Low |
| **Agentic: ACP** | **OpenAI + Stripe, 29 Sept 2025**, Apache 2.0, jointly governed with a stated path to broader community governance. **Spec revisions: 2025-09-29, 2025-12-12, 2026-01-16, 2026-01-30, 2026-04-17** — five in seven months | **High** |
| **Agentic: the plot twist** | ⚠️ **OpenAI Instant Checkout was retired 5 March 2026** after ~30 Shopify merchants integrated; OpenAI pivoted to **retailer-operated ChatGPT Apps**. **Forrester: US consumer adoption was low and stagnant from debut to discontinuation** | **High** |
| **Agentic: UCP** | **Google + Shopify**, unveiled at **NRF January 2026**; April 2026 release expanded partners past twenty. Covers **discovery through post-purchase** | **High** |
| **Agentic: AP2** | **Donated to the FIDO Alliance 28 April 2026** alongside **v0.2**; 60 organizations contributed; Verifiable Intent co-developed with Mastercard. Focus: **authorization, authenticity, accountability** via signed mandates | **High** |
| **Agentic: others** | **x402** (Coinbase) V2 Dec 2025; **Stripe integrated x402 on Base Feb 2026** (preview, USDC on Base/Solana/Tempo). **MPP** (Stripe + Tempo) launched **18 March 2026** with a spending-limit "sessions" model. **Visa Trusted Agent Protocol** and **Mastercard Agent Pay** extend network tokenization | **High** |
| **Stripe API** | Versions pinned per account/request; dated version strings (e.g. `2026-07-29.dahlia`). **Checkout Sessions is the currently recommended path.** Webhook retries **up to ~72 hours**; **idempotency results cached 24 hours** | Medium |
| **Scale anchor** | An industry summary reported **Stripe processed ~$1.9 trillion in total payment volume in 2025** | Annual |

**Goes stale fastest:** the agentic protocol landscape (everything in it); PSD3/PSR dates;
PSP API versions. **Essentially never stale:** §2 → `ecommerce-payments-architecture-and-integration` (the payment lifecycle), §3 → `ecommerce-payments-architecture-and-integration`
(idempotency, webhooks, reconciliation), §2.2 → `ecommerce-payments-architecture-and-integration` (money handling), §7.1 → `ecommerce-payment-methods-sca-fraud-and-pci`, §13.2 → `ecommerce-billing-tax-platforms-and-checkout`, §15.

---
