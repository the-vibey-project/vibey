---
id: skill-25-firmware-security-de5b152236
purpose: 25 firmware security
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-firmware-boot-root-of-trust-embedded-practice-and-security/SKILL.md
requires: ["skill-24-embedded-firmware-practice-8933cbe46f"]
links: []
---

## §25. ⚠️ Firmware Security

```
⚠️ ⚠️ WHY IT MATTERS DISPROPORTIONATELY  ⚠️ firmware runs before
   and beneath the OS, persists across reinstalls and disk
   replacement, and is largely invisible to antivirus
⚠️ THE ATTACK CLASSES
   ⚠️ BOOTKITS  ⚠️ persist in the boot chain (§26.1)
   ⚠️ SMM attacks  ⚠️ SMM is more privileged than the kernel
      and hypervisor
   ⚠️ ⚠️ DMA attacks  ⚠️ a peripheral reading host memory
      directly — IOMMU is the mitigation (see a peripherals
      reference §24)
   ⚠️ SPI flash modification — ⚠️ physical or logical, if write
      protection is misconfigured
   ⚠️ ⚠️ SUPPLY CHAIN  implanted or modified firmware before
      delivery
   ⚠️ Unsigned or weakly-signed update paths
   ⚠️ ⚠️ CONFIGURATION IMAGE PARSING — ⚠️ the LogoFAIL class
      showed that image parsers in firmware, processing an
      attacker-supplied boot logo, were exploitable. ⚠️ Firmware
      contains far more attack surface than people assume
⚠️ THE DEFENCES  ⚠️ hardware root of trust (§22) · signed
   updates with ROLLBACK PROTECTION · ⚠️ SPI write protection ·
   reduced attack surface · memory-safe languages in firmware ·
   ⚠️ measured boot and attestation · runtime firmware
   integrity monitoring
⚠️ ⚠️ THE STRUCTURAL PROBLEM  ⚠️ firmware is written by
   organizations that do not maintain it for the device's life,
   patched slowly or never, and the user usually cannot tell
   what version they run or whether it is vulnerable
```
