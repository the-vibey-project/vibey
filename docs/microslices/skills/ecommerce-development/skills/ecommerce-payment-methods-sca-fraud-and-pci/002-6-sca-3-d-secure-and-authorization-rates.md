---
id: skill-6-sca-3-d-secure-and-authorization-rates-aec0629dff
purpose: 6 sca 3 d secure and authorization rates
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payment-methods-sca-fraud-and-pci/SKILL.md
requires: ["skill-5-payment-methods-and-rails-0e05aab9fc"]
links: ["skill-7-fraud-and-disputes-8301679835"]
---

## §6. SCA, 3-D Secure, and Authorization Rates

### 6.1 Strong Customer Authentication

**[DURABLE] SCA requires two of three factors** — knowledge, possession, inherence — for
in-scope electronic payments in the EU/UK. **3-D Secure 2.x is the dominant technical
mechanism for satisfying it on card-not-present transactions**, and it passes rich device
and transaction data to the issuer to enable frictionless authentication where risk is low.

**The exemptions matter commercially** — low value, transaction risk analysis (TRA),
recurring/MIT, merchant-initiated transactions, and trusted beneficiaries. **Requesting the
right exemption is the difference between a frictionless approval and an abandoned
checkout**, and modern PSP APIs handle much of this automatically when you use their
higher-level payment objects.

**[VERSIONED] PSD3/PSR refines the SCA framework rather than replacing 3DS2 — the protocol
itself is not changing.** Expect expanded SCA triggers (new token creation, spending-limit
changes) once the new rules apply, and note that **delegating SCA to a third party is
being treated as formal outsourcing**, pulling in EBA outsourcing guidelines and DORA
obligations — written agreements, SLAs, exit plans, audit rights.

### 6.2 Authorization rates

**[DURABLE] A 1% improvement in authorization rate is usually worth more than any
conversion optimization you'll do on the front end**, and almost nobody measures it.

Levers: **network tokens** (§5.1), **account updater** for expired/reissued cards, correct
**MCC** coding, **AVS/CVV** data quality, **smart retries** on soft declines (with respect
for network retry rules — excessive retries incur fees and can flag you), **local
acquiring** in major markets (a locally-acquired transaction approves materially better
than a cross-border one), and **passing full 3DS data** even when not required.

**Soft vs. hard declines**: soft (insufficient funds, do-not-honor, issuer unavailable) may
succeed on retry; **hard (stolen card, invalid account, revoked authorization) must never
be retried** — retrying hard declines is a compliance problem, not just futile.

---
