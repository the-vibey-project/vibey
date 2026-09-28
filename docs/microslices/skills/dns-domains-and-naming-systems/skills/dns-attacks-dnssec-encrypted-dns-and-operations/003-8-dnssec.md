---
id: skill-8-dnssec-25e814d0dc
purpose: 8 dnssec
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-attacks-dnssec-encrypted-dns-and-operations/SKILL.md
requires: ["skill-7-attacks-on-dns-fbd7b8c62a"]
links: ["skill-9-encrypted-dns-936017aa21"]
---

## §8. ⚠️ DNSSEC

**⚠️ What it does**: ⚠️ **cryptographically signs DNS data so a resolver can verify
authenticity and integrity, with a chain of trust from the signed root downward.**
```
⚠️ THE MECHANISM  ⚠️ RRSIG signs each RRset · DNSKEY holds the
   zone's public keys · ⚠️ DS in the PARENT is a hash of the
   child's key — ⚠️ THAT is the delegation of trust, mirroring
   §5's delegation of authority
   ⚠️ KSK and ZSK separation lets you roll the zone key without
   touching the parent
⚠️ ⚠️ PROVING NONEXISTENCE IS THE HARD PART. ⚠️ You cannot sign
   an infinite set of names that do not exist
   ⚠️ NSEC proves a gap between two existing names — ⚠️ which
      allows ZONE WALKING, enumerating the whole zone
   ⚠️ NSEC3 hashes the names to prevent that, ⚠️ and is itself
      offline-crackable, hence NSEC3 with zero iterations plus
      white lies as current practice
⚠️ ⚠️ WHAT DNSSEC DOES NOT DO  ⚠️ IT DOES NOT ENCRYPT ANYTHING.
   ⚠️ Queries and answers remain fully visible. ⚠️ DNSSEC is
   INTEGRITY; §9 is CONFIDENTIALITY. They are orthogonal and
   constantly confused
⚠️ ⚠️ ADOPTION IS THE UNCOMFORTABLE PART  ⚠️ validation on the
   resolver side is now widespread, but SIGNING remains a
   minority of domains — and ⚠️ MISCONFIGURED DNSSEC TAKES YOUR
   DOMAIN COMPLETELY OFFLINE for validating resolvers, which is
   a failure mode worse than the attacks it prevents. ⚠️ Expired
   signatures have caused major national outages
⚠️ WHAT IT ENABLES  ⚠️ DANE (certificates in DNS), SSHFP,
   and authenticated §5 delegation
```

---
