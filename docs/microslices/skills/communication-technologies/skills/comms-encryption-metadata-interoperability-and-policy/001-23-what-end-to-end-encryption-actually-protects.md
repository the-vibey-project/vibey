---
id: skill-23-what-end-to-end-encryption-actually-protects-3fe4b41571
purpose: 23 what end to end encryption actually protects
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-encryption-metadata-interoperability-and-policy/SKILL.md
requires: []
links: ["skill-24-metadata-f2fb7a6a60"]
---

## §23. ⚠️ What End-to-End Encryption Actually Protects

```
⚠️ ⚠️ FOUR DIFFERENT CLAIMS, routinely conflated
   ⚠️ 1. TRANSPORT ENCRYPTION (TLS)  ⚠️ protects the wire.
      ⚠️ THE PROVIDER READS EVERYTHING
   ⚠️ 2. ENCRYPTION AT REST  ⚠️ protects stolen disks.
      ⚠️ The provider holds the keys
   ⚠️ 3. ⚠️ END-TO-END ENCRYPTION  ⚠️ only the endpoints can
      read it. ⚠️ The provider cannot
   ⚠️ 4. ⚠️ E2EE WITH VERIFIED KEYS  ⚠️ plus assurance you are
      talking to who you think
⚠️ ⚠️ WHAT E2EE DOES NOT PROTECT — and this list is the point
   ⚠️ METADATA (§24) — usually the most valuable part
   ⚠️ ⚠️ THE ENDPOINTS. ⚠️ A compromised phone defeats it
      completely, which is what commercial spyware targets —
      ⚠️ and it is why endpoint compromise is the actual
      state-actor answer to encryption, not cryptanalysis
   ⚠️ ⚠️ BACKUPS. ⚠️ Cloud backups are frequently NOT E2EE by
      default, so an encrypted conversation sits in plaintext
      in someone's backup (§18)
   ⚠️ ⚠️ THE OTHER PARTY. ⚠️ They can screenshot, forward, or
      simply be untrustworthy. ⚠️ Encryption is not confidence
   ⚠️ ⚠️ KEY DISTRIBUTION. ⚠️ If the provider supplies the
      public keys, they could in principle substitute one —
      which is what key transparency and verification address,
      and what almost nobody checks
   ⚠️ CLIENT-SIDE SCANNING, which inspects BEFORE encryption
      and is therefore not defeated by it at all (§26, §28.2)
⚠️ ⚠️ THE PRACTICAL TEST FOR ANY CLAIM: ⚠️ CAN THE PROVIDER
   SHOW YOU YOUR OLD MESSAGES ON A NEW DEVICE WITH ONLY A
   PASSWORD? ⚠️ If yes, it is not end-to-end encrypted, or the
   backup isn't
```

---
