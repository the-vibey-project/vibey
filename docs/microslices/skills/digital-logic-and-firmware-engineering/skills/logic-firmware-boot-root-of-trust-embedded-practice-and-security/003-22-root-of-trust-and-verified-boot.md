---
id: skill-22-root-of-trust-and-verified-boot-1e35a0ada5
purpose: 22 root of trust and verified boot
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-firmware-boot-root-of-trust-embedded-practice-and-security/SKILL.md
requires: ["skill-21-the-boot-sequence-883be5cb1d"]
links: ["skill-23-acpi-and-platform-interfaces-9c9d2cc3c8"]
---

## §22. ⚠️ Root of Trust and Verified Boot

```
⚠️ ⚠️ THE CORE IDEA: TRUST MUST START SOMEWHERE IMMUTABLE. ⚠️ A
   hardware root of trust — mask ROM or fused keys that cannot
   be modified — verifies the next stage, which verifies the
   next, and so on
⚠️ ⚠️ TWO DIFFERENT THINGS OFTEN CONFLATED
   ⚠️ SECURE / VERIFIED BOOT  ⚠️ ENFORCES — refuses to run
      unsigned code
   ⚠️ MEASURED BOOT  ⚠️ RECORDS — hashes each stage into TPM PCRs
      and lets a remote party ATTEST what ran. ⚠️ It does not
      block anything
   ⚠️ They are complementary, not alternatives
⚠️ THE TPM  ⚠️ PCRs (⚠️ extend-only, so history cannot be
   rewritten) · sealing (⚠️ releasing a key only if PCRs match,
   which is how BitLocker binds to platform state) ·
   attestation · endorsement key
⚠️ ⚠️ UEFI SECURE BOOT's KEY HIERARCHY (§26.1)
   ⚠️ PK (Platform Key — the OEM's root, one key)
   ⚠️ KEK (Key Exchange Key — authorizes updates to the lists)
   ⚠️ DB (allowed signatures) and ⚠️ DBX (revoked)
⚠️ SHIM  ⚠️ how Linux boots under Secure Boot — a small
   Microsoft-signed loader that then validates the distribution's
   own key, with MOK for user-enrolled keys
⚠️ ROLLBACK PROTECTION  ⚠️ signature validity is not enough —
   ⚠️ an attacker can install a genuinely signed OLD version
   with a known vulnerability. ⚠️ Monotonic counters or fuses
   are the defence, and this is frequently omitted
⚠️ ⚠️ THE HONEST LIMIT: verified boot proves what LOADED, not
   that it is CORRECT. ⚠️ A signed vulnerable bootloader passes
   verification perfectly (§26.1's BlackLotus)
```

---
