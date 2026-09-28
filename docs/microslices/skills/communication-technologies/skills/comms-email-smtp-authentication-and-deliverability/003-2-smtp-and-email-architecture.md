---
id: skill-2-smtp-and-email-architecture-2dfbd07720
purpose: 2 smtp and email architecture
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-email-smtp-authentication-and-deliverability/SKILL.md
requires: ["skill-1-the-federated-proprietary-divide-55c5339e82"]
links: ["skill-3-retrieval-protocols-6a55ccaa33"]
---

## §2. SMTP and Email Architecture

```
⚠️ THE COMPONENTS  ⚠️ MUA (your client) → MSA (submission) →
   MTA (transfer, possibly several) → MDA (delivery) → mailbox
⚠️ SMTP  ⚠️ from 1982, text-based, store-and-forward.
   ⚠️ Ports: 25 (MTA-to-MTA), 587 (⚠️ submission, authenticated),
   465 (implicit TLS)
⚠️ ⚠️ THE ENVELOPE IS NOT THE HEADER. ⚠️ MAIL FROM and RCPT TO
   are the SMTP envelope; the From: and To: you SEE are message
   headers. ⚠️ THEY NEED NOT MATCH — and that gap is the
   entire basis of email spoofing (§5)
⚠️ MX RECORDS in DNS route mail for a domain
⚠️ STARTTLS  ⚠️ opportunistic encryption — ⚠️ and "opportunistic"
   means STRIPPABLE by an active attacker unless MTA-STS or
   DANE is in place, which most domains lack
⚠️ ⚠️ SMTP HAD NO AUTHENTICATION AT ALL BY DESIGN. ⚠️ Everything
   in §5 is bolted on decades later, which is why it is a
   layered mess of DNS records rather than a protocol feature
⚠️ BOUNCES  ⚠️ hard vs soft · ⚠️ BACKSCATTER (bounces sent to a
   forged sender) is a consequence of accepting-then-bouncing
```

---
