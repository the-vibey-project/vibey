---
id: skill-19-domain-security-c29727734e
purpose: 19 domain security
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-whois-disputes-domain-security-and-aftermarket/SKILL.md
requires: ["skill-18-disputes-5a469f33dc"]
links: ["skill-20-the-aftermarket-07a4850ce8"]
---

## §19. ⚠️ Domain Security

```
⚠️ ⚠️ THE DOMAIN IS THE ROOT OF YOUR ONLINE IDENTITY. ⚠️ Whoever
   controls it can obtain certificates for it (§1), receive
   your email, pass password resets, and impersonate you
   completely. ⚠️ It deserves protection commensurate with that
⚠️ THE ATTACK PATHS, in rough order of prevalence
   ⚠️ 1. ⚠️ REGISTRAR ACCOUNT COMPROMISE  ⚠️ phishing, credential
      reuse, or social engineering the support desk
   ⚠️ 2. ⚠️ EXPIRY  ⚠️ the most common self-inflicted loss.
      ⚠️ Auto-renew plus a valid payment card plus a monitored
      contact address
   ⚠️ 3. ⚠️ DNS PROVIDER compromise or dangling delegation
   ⚠️ 4. ⚠️ SUBDOMAIN TAKEOVER  ⚠️ a CNAME points at a cloud
      resource you decommissioned; someone else claims that
      resource and now controls your subdomain. ⚠️ Extremely
      common, easy to scan for, and often uncleaned
   ⚠️ 5. Email compromise of the registrant contact
   ⚠️ 6. Registry-level attack (rare, catastrophic)
⚠️ ⚠️ THE DEFENCES, and they are cheap
   ⚠️ REGISTRAR LOCK and ⚠️ REGISTRY LOCK (⚠️ the latter requires
      out-of-band human verification to change anything — the
      single strongest control available and worth the fee for
      any significant domain)
   ⚠️ ⚠️ MFA on the registrar account, on a monitored address
   ⚠️ ⚠️ CAA RECORDS (§4) limiting who may issue certificates
   ⚠️ CERTIFICATE TRANSPARENCY MONITORING — ⚠️ you find out
      someone issued a cert for your name
   ⚠️ DNSSEC (§8) · expiry monitoring separate from the registrar
   ⚠️ ⚠️ AUDIT DANGLING DNS RECORDS regularly
```

---
