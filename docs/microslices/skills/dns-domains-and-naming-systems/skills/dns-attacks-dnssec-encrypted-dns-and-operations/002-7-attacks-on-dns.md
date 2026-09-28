---
id: skill-7-attacks-on-dns-fbd7b8c62a
purpose: 7 attacks on dns
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-attacks-dnssec-encrypted-dns-and-operations/SKILL.md
requires: ["skill-6-caching-and-ttl-60cc068ac9"]
links: ["skill-8-dnssec-25e814d0dc"]
---

## §7. ⚠️ Attacks on DNS

```
⚠️ ⚠️ THE ORIGINAL SIN: DNS HAS NO AUTHENTICATION. ⚠️ A response
   is accepted if it matches the query, arrives on the right
   port, and has the right 16-bit transaction ID
⚠️ ⚠️ CACHE POISONING  ⚠️ inject a forged response before the
   real one arrives; the resolver caches your answer and serves
   it to everyone
   ⚠️ ⚠️ THE KAMINSKY ATTACK (2008) made this dramatically
   practical by attacking NONEXISTENT subdomains in a loop,
   removing the need to wait for a cache entry to expire —
   ⚠️ and it triggered a coordinated industry-wide emergency
   patch
   ⚠️ THE MITIGATION  ⚠️ SOURCE PORT RANDOMIZATION plus 0x20
   encoding — ⚠️ which raises the guessing cost enormously
   WITHOUT actually authenticating anything. ⚠️ DNSSEC is the
   real fix (§8)
⚠️ ⚠️ ON-PATH ATTACKS  ⚠️ trivially defeat plaintext DNS.
   ⚠️ This is the case for encrypted transport (§9)
⚠️ ⚠️ DNS AMPLIFICATION  ⚠️ small spoofed query, large response,
   directed at a victim. ⚠️ Open resolvers are the ammunition;
   ⚠️ response rate limiting and BCP 38 source filtering are
   the defences, and BCP 38 remains under-deployed
⚠️ NXDOMAIN and random-subdomain (water torture) attacks
   exhaust authoritative servers
⚠️ ⚠️ REGISTRAR-LEVEL AND REGISTRY-LEVEL ATTACKS  ⚠️ compromise
   the ACCOUNT and you need no protocol attack at all (§19).
   ⚠️ This is the highest-leverage attack and the least technical
```

---
