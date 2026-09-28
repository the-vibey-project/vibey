---
id: skill-4-compliance-reality-us-eu-as-of-2026-af5c1666a1
purpose: 4 compliance reality us eu as of 2026
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-stripe/SKILL.md
requires: ["skill-3-integration-patterns-easiest-most-control-d7482527af"]
links: ["skill-5-money-movement-products-pricing-us-as-of-sept-2026-9a5b731519"]
---

## 4. Compliance reality (US/EU, as of 2026)

- **PCI DSS v4.0.1** has been the only active version since **31 Mar 2025**. For e-commerce the load-bearing rules are **6.4.3** (payment-page scripts authorized/inventoried/integrity-checked) and **11.6.1** (weekly tamper detection) — both anti-Magecart. ⚠️ **The SAQ A trap**: in Jan 2025 the PCI SSC removed those from SAQ A but replaced them with an eligibility test — **can you confirm your whole e-commerce site is not susceptible to malicious scripts?** With a redirect/iFrame Checkout flow plus written PSP confirmation you can; otherwise you fall to SAQ A-EP's much larger requirement set. Practical implementation regardless: CSP + SRI, and minimum third-party JS on checkout.
- **SCA/3DS2**: EU/UK two-factor requirement; use PaymentIntents/Checkout and exemptions (MIT, TRA, low-value) flow automatically. PSD3/PSR refines rather than replaces 3DS2 — watch for expanded SCA triggers (new tokens, limit changes) once in force.
- **Authorization rate ≈ hidden revenue**: levers are network tokens, account updater, correct MCC, local acquiring, and full 3DS data. A +1% auth-rate lift typically beats any frontend conversion work — nearly nobody measures it.
- **Fraud/chargebacks**: merchant eats CNP fraud via chargebacks; **friendly fraud** is often the largest bucket; network **ratio monitoring** (not totals) is what gets you terminated — prevention (clear descriptor, easy cancellation, Order Insight-style deflection) beats representment, and **you pay the dispute fee ($15) even when you win**. False positives quietly strangle revenue; measure both sides.

---
