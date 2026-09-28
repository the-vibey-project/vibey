---
id: skill-13-pki-and-certificates-98f42e4dfc
purpose: 13 pki and certificates
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-passwords-tls-pki-messaging-and-disk-encryption/SKILL.md
requires: ["skill-12-tls-c7dfa7b3e8"]
links: ["skill-14-end-to-end-encrypted-messaging-1f39b77ae2"]
---

## §13. PKI and Certificates

**⚠️ The trust model is the weak point, and it is worth stating plainly.**
```
⚠️ HOW IT WORKS  a CA vouches that a public key belongs to a name;
   your OS/browser ships a ROOT STORE of trusted CAs; chains
   validate up to a root
⚠️ THE STRUCTURAL PROBLEM  ⚠️ ANY trusted CA can issue for ANY
   domain. ⚠️ Trust is the UNION of hundreds of organizations
   across many jurisdictions, and it is only as strong as the
   weakest one. ⚠️ Real CAs have been compromised or have
   misissued, more than once
⚠️ MITIGATIONS
   ⚠️ CERTIFICATE TRANSPARENCY  ⚠️ public append-only logs of issued
      certificates, so misissuance is DETECTABLE. ⚠️ The most
      effective structural fix deployed
   ⚠️ CAA records  restrict which CAs may issue for your domain
   ⚠️ Pinning  ⚠️ powerful and dangerous — HPKP was deprecated
      because it enabled permanent self-inflicted denial of service
⚠️ REVOCATION IS THE UNSOLVED PROBLEM  ⚠️ CRLs are large, OCSP is
   a privacy leak and a latency cost, and ⚠️ browsers commonly
   FAIL OPEN when the check is unavailable — meaning revocation
   often doesn't work. ⚠️ This is precisely why §23.2 is happening
```
**⚠️ Private PKI** for internal services is a different problem — ⚠️ **you control the root,
so you control policy, and CA/Browser Forum rules do not apply.**

---
