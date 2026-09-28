---
id: skill-saq-selection-logic-77fc1baf16
purpose: saq selection logic
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/pci-dss-v4/SKILL.md
requires: ["skill-the-12-requirements-6-goals-d9c3f07f60"]
links: ["skill-key-new-requirements-in-pci-dss-v4-0-a080aded5a"]
---

## SAQ Selection Logic

The Self-Assessment Questionnaire type depends on how your system handles card data.

### SAQ A — Fully Outsourced Card Acceptance
**Who qualifies:**
- Card-not-present (e-commerce or mail/telephone order) merchants
- ALL cardholder data functions are outsourced to a PCI DSS compliant third party
- Merchant website does not receive, transmit, or store any cardholder data
- Payment page is a redirect or iframe hosted entirely by the third party
- Merchant has no electronic storage of CHD

**Examples:** Using Stripe Checkout hosted page, PayPal redirect, Square hosted payment page

**Requirements covered:** ~22 requirements (subset of all 12)

**Key controls for SAQ-A:**
- Maintain an information security policy (Req 12)
- Security awareness training (Req 12.6)
- Incident response plan (Req 12.10)
- Confirm service providers are PCI compliant (Req 12.8)
- Protect against phishing on merchant systems (Req 5.4)

**SAQ-A does NOT require:** Network security controls assessment, full vulnerability scanning, penetration testing, internal system hardening reviews

### SAQ A-EP — E-commerce, Partial Outsource (Script on Merchant Page)
**Who qualifies:**
- E-commerce merchants only
- Payment page is hosted on merchant's systems but all payment processing is outsourced
- Merchant's website receives payment data but immediately passes to payment processor
- OR merchant's website has scripts that affect payment data capture (e.g., JavaScript payment form elements not fully hosted by processor)

**Examples:** Custom checkout form that posts to payment processor; JavaScript SDK embedded in merchant page that collects card fields

**Key distinction from SAQ-A:** The merchant controls the web page/server where payment data is initially captured, even if processing happens elsewhere.

**Requirements covered:** ~191 requirements — significantly more than SAQ-A

**Key additional controls vs SAQ-A:**
- Network security controls (Req 1): Firewall protecting the web server
- System hardening (Req 2): Secure configuration of web servers
- Vulnerability scanning: Quarterly ASV scans required
- Penetration testing: Annual internal and external pen test
- Web application firewall (WAF): Required (Req 6.4.2)
- Payment page script integrity (Req 6.4.3, 11.6.1) — see v4.0 new requirements


### SAQ B-IP — IP-Connected Payment Terminals
**Who qualifies:**
- Merchants using standalone IP-connected POI terminals (not e-commerce)
- Terminals are PTS-approved and do not store electronic cardholder data
- Terminal connects to payment processor via IP network (not dial-up)
- No card data captured by other merchant systems

**Examples:** Retail counter terminals, restaurants using wireless IP terminals (Verifone, Ingenico, PAX) connected via WiFi or Ethernet directly to payment network

**Key requirements vs SAQ-A:**
- Network security controls protecting terminal network segment
- Terminal inventory management
- Physical security of terminals (tamper protection, anti-skimming)
- Quarterly ASV scans of IP-connected terminal environment

**SAQ B-IP does NOT require:** Full e-commerce controls, WAF, payment page script controls

### SAQ Decision Tree

```
Does the merchant store, process, or transmit cardholder data electronically?
  └── No → likely out of scope (confirm with acquiring bank)
  └── Yes →
       Is all card acceptance fully outsourced (redirect/iframe, no merchant code touches CHD)?
         └── Yes, e-commerce only → SAQ-A
         └── Yes, but merchant controls page with embedded payment scripts → SAQ-A-EP
         └── No, merchant uses IP-connected standalone terminals (not e-commerce) → SAQ-B-IP
         └── No, merchant processes cards in a more complex environment → SAQ-C, SAQ-D, or ROC
```

---
