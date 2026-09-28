---
id: skill-5-payment-methods-and-rails-0e05aab9fc
purpose: 5 payment methods and rails
source: src/vibey_tools/skills/plugins/ecommerce-development/skills/ecommerce-payment-methods-sca-fraud-and-pci/SKILL.md
requires: []
links: ["skill-6-sca-3-d-secure-and-authorization-rates-aec0629dff"]
---

## §5. Payment Methods and Rails

### 5.1 Cards

The default, and the most expensive. **Interchange + scheme fees + acquirer margin** is
what you're actually paying; "2.9% + 30¢" is a blended retail price over that. Know
**card-present vs. card-not-present** (CNP costs more and carries the fraud liability),
**debit vs. credit vs. prepaid**, and **commercial cards** (higher interchange, and Level
2/Level 3 data can reduce it for B2B).

**Network tokens** (replacing the PAN with a network-issued token) improve authorization
rates and survive card reissuance — **worth enabling; most PSPs support it**.

### 5.2 Beyond cards

**[DURABLE] Payment method mix is a localization problem, and getting it wrong silently
caps your conversion in a market.** Cards dominate the US; much of Europe runs on bank
transfers and local schemes (iDEAL in NL, Bancontact in BE, BLIK in PL); Germany
historically favours invoice and direct debit; Brazil runs on PIX; India on UPI; much of
Southeast Asia and Africa on wallets and mobile money.

- **Wallets** — Apple Pay, Google Pay, PayPal, Link. **Meaningful conversion lift on
  mobile** because they eliminate form entry, and they carry tokenized credentials.
- **Bank transfers / A2A** — ACH (US, cheap, slow, **reversible for up to 60 days on
  consumer accounts** — a real fraud exposure), SEPA Direct Debit (EU, with an 8-week
  no-questions refund right), open banking payment initiation.
- **Instant payments** — FedNow and RTP in the US, SEPA Instant in the EU, PIX, UPI,
  Faster Payments. **Generally irrevocable**, which changes the fraud model entirely:
  the risk moves from chargebacks to authorized push payment (APP) fraud (§7.1).
- **BNPL** — Klarna, Afterpay, Affirm. Higher conversion and AOV, higher fees, and the
  provider typically takes the credit risk.
- **Direct carrier billing**, **cash vouchers** (OXXO, Boleto), **crypto/stablecoin** (§14.3 → `ecommerce-billing-tax-platforms-and-checkout`).

### 5.3 The bank rails underneath

**[DURABLE] Worth understanding even if you never touch them directly**, because they
determine settlement timing and irrevocability.

**SWIFT** is the interbank *messaging* network — it moves instructions, not money; the
money moves through correspondent banking relationships and nostro/vostro accounts. This
is why international wires take days and why fees appear from intermediaries you never
chose. **ISO 20022** is the structured, data-rich message standard that has been replacing
the older MT formats across major payment systems, enabling far richer remittance data and
better sanctions screening and reconciliation. **[VERSIONED] Migration timelines differ by
scheme and market — verify the current state for any rail you depend on**, as several major
coexistence periods have recently ended or are ending.

**Card networks** (Visa, Mastercard, Amex, Discover, plus domestic schemes like Cartes
Bancaires and UnionPay) are a four-party model: cardholder, issuer, acquirer, merchant, with
the network in the middle setting rules and interchange.

---
