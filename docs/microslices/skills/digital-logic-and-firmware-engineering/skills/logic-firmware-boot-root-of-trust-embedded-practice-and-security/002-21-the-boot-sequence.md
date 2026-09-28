---
id: skill-21-the-boot-sequence-883be5cb1d
purpose: 21 the boot sequence
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-firmware-boot-root-of-trust-embedded-practice-and-security/SKILL.md
requires: ["skill-20-the-firmware-landscape-f947e2419d"]
links: ["skill-22-root-of-trust-and-verified-boot-1e35a0ada5"]
---

## §21. ⚠️ The Boot Sequence

> **⚠️ The chain that gets a machine from applied power to an operating system, and knowing
> its stages is what makes boot failures diagnosable.**
```
⚠️ THE STAGES, in order
   ⚠️ 1. POWER SEQUENCING and RESET  ⚠️ rails come up in a
      required order; reset released when stable
   ⚠️ 2. ⚠️ THE FIRST INSTRUCTION comes from a fixed RESET VECTOR
      in ROM — ⚠️ and at this point there is NO RAM initialized
   ⚠️ 3. ⚠️ EARLY INIT  ⚠️ often running out of CACHE-AS-RAM,
      because DRAM does not work until it is trained
   ⚠️ 4. ⚠️ MEMORY TRAINING  ⚠️ the memory controller calibrates
      timings against the actual DIMMs. ⚠️ This is why first
      boot after a RAM change is slow, and why results are
      cached
   ⚠️ 5. Chipset and silicon init · 6. device enumeration
   ⚠️ 7. Boot device selection · 8. bootloader · 9. kernel
⚠️ ⚠️ UEFI vs LEGACY BIOS
   ⚠️ Legacy: 16-bit real mode, MBR, 512-byte boot sector,
      interrupt-based services. ⚠️ Effectively gone
   ⚠️ UEFI: ⚠️ a small OS in its own right — 64-bit, GPT
      partitions, ⚠️ an EFI SYSTEM PARTITION holding actual
      executable files, driver model, protocols, boot manager
      with variables, ⚠️ and a shell
⚠️ THE UEFI PHASES  ⚠️ SEC → PEI (pre-EFI init, memory) →
   ⚠️ DXE (driver execution — where most functionality lives) →
   BDS (boot device select) → TSL → RUNTIME
⚠️ ⚠️ RUNTIME SERVICES PERSIST AFTER THE OS BOOTS — ⚠️ variable
   access and firmware update paths remain callable, which is
   both useful and an attack surface (§25)
⚠️ EMBEDDED EQUIVALENTS  ⚠️ ROM bootloader → first-stage (SPL,
   often size-constrained) → U-Boot or similar → kernel
```

---
