---
id: skill-5-spf-dkim-dmarc-d6bab0af3e
purpose: 5 spf dkim dmarc
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-email-smtp-authentication-and-deliverability/SKILL.md
requires: ["skill-4-message-format-978595998d"]
links: ["skill-6-deliverability-9647d54f44"]
---

## §5. ⚠️ SPF, DKIM, DMARC

> **⚠️ The three-layer patch over §2's missing authentication, and understanding what each
> actually checks is what makes email security legible.**
```
⚠️ ⚠️ SPF  ⚠️ a DNS record listing which IPs may send for a
   domain. ⚠️ CHECKS THE ENVELOPE SENDER (MAIL FROM), NOT the
   visible From: header
   ⚠️ THEREFORE SPF ALONE DOES NOT STOP SPOOFING of what the
   user sees. ⚠️ It also BREAKS ON FORWARDING, because the
   forwarder's IP is not in the original domain's record
⚠️ ⚠️ DKIM  ⚠️ a cryptographic SIGNATURE over selected headers
   and the body, with the public key in DNS.
   ⚠️ SURVIVES FORWARDING (as long as nothing modifies the
   signed parts) · ⚠️ BREAKS when a mailing list appends a
   footer or rewrites a subject
⚠️ ⚠️ DMARC  ⚠️ THE ONE THAT MATTERS. ⚠️ Requires SPF or DKIM to
   pass AND to be ALIGNED with the visible From: domain, and
   publishes a POLICY: none, quarantine, or reject
   ⚠️ Plus aggregate and forensic REPORTING, which is how you
   discover who is sending as you
⚠️ ⚠️ THE ALIGNMENT REQUIREMENT IS THE WHOLE POINT — it closes
   the envelope-versus-header gap of §2
⚠️ ARC  ⚠️ preserves authentication results across intermediaries
   (mailing lists, forwarders) so DMARC does not destroy them
⚠️ BIMI  displays a verified logo; ⚠️ requires DMARC enforcement
   and usually a paid mark certificate — ⚠️ arguably a
   compliance incentive dressed as a feature
⚠️ ⚠️ THE ROLLOUT TRAP  ⚠️ going straight to p=reject without
   reading reports first WILL silently drop legitimate mail from
   systems you forgot about — the ticketing system, the payroll
   provider, the marketing tool
```

---
