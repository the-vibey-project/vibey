---
id: skill-8-pci-dss-and-security-da9e3e817b
purpose: 8 pci dss and security
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payment-methods-sca-fraud-and-pci/SKILL.md
requires: ["skill-7-fraud-and-disputes-8301679835"]
links: []
---

## §8. PCI DSS and Security

### 8.1 Scope is architecture

**[DURABLE] Everything in PCI is downstream of one question: does cardholder data ever
touch your systems?**

```
SAQ A       fully outsourced — hosted payment page or PSP-hosted iframe    ← aim here
SAQ A-EP    your page, but it affects the transaction (e.g. JS-based fields)
SAQ D       you touch, transmit, or store cardholder data                  ← expensive
```
**The strategic advice is simple: use the PSP's hosted fields, iframe, or redirect, store
only PSP tokens and IDs, and never let a PAN reach your server or your logs.** This keeps
you in the lightest tier and out of the most expensive parts of the standard.

### 8.2 The v4.0.1 e-commerce requirements — and the SAQ A trap

**[VERSIONED, and this is the part most merchants have wrong.]**

**PCI DSS v4.0.1's future-dated requirements became mandatory on 31 March 2025** — 51
requirements that had been "best practice" until that date, on top of 13 that applied
immediately. **There is no remaining transition phase, and v4.0.1 is the only active
version.** Two matter most for e-commerce:
- **Requirement 6.4.3** — all payment page scripts must be **authorized, integrity-checked,
  and inventoried**.
- **Requirement 11.6.1** — a **change- and tamper-detection mechanism** alerting on
  unauthorized changes to payment pages and scripts, evaluated **at least weekly**.

Both exist to address **Magecart-style e-skimming**, where malicious JavaScript is injected
into a checkout page to exfiltrate card data.

> **⚠️ GOTCHA — the SAQ A change looked like relief and is arguably the opposite.** In
> January 2025 the PCI SSC **removed 6.4.3, 11.6.1, and 12.3.1 from SAQ A** in response to
> merchant feedback — and **replaced them with an eligibility criterion**: the merchant must
> confirm **"their site is not susceptible to attacks from scripts that could affect the
> merchant's e-commerce system(s)."**
>
> **Read the scope change carefully.** The old requirements applied to the *payment page*.
> The new eligibility criterion applies to **your entire website**. Merchants using
> redirects — previously out of scope for 6.4.3 and 11.6.1 entirely — must now verify that
> **all scripts within their e-commerce system** are secure. **If you cannot make that
> confirmation, you are not eligible for SAQ A at all and must validate against SAQ A-EP**,
> which carries a far larger requirement set.
>
> A February 2025 PCI SSC FAQ clarified two routes to satisfy it: **implement 6.4.3 and
> 11.6.1 yourself anyway**, or **obtain written confirmation from a PCI DSS compliant
> third-party service provider** that its embedded payment solution protects against script
> attacks when implemented per their instructions. Practitioners also recommend
> demonstrating via web application testing or a properly configured WAF.
>
> The October 2024 SAQ A retired **31 March 2025**; the January 2025 (r1) version took
> effect the same day.

### 8.3 The rest of security

**CSP** and **Subresource Integrity (SRI)** are the practical implementations of 6.4.3 —
and are worth doing regardless of which SAQ you file. **Minimize third-party scripts on
checkout** (every analytics tag is a supply-chain risk on your highest-value page).
**Tokenize everything**; store PSP tokens, never PANs. **TLS 1.2+ everywhere.** Rate-limit
payment endpoints against card testing. Secrets in a manager, not env files in git. And
**PCI is contractual, not statutory in most jurisdictions** — but the financial consequences
(card-brand fines levied on your acquirer and passed to you, forensic investigation costs,
and potential loss of processing) are severe and multi-layered.
