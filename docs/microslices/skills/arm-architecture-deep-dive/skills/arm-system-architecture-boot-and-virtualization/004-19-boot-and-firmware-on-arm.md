---
id: skill-19-boot-and-firmware-on-arm-5425cd273b
purpose: 19 boot and firmware on arm
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-system-architecture-boot-and-virtualization/SKILL.md
requires: ["skill-18-interconnect-57bd56eacf"]
links: ["skill-20-virtualization-cb041ab467"]
---

## §19. ⚠️ Boot and Firmware on ARM

> **⚠️ Genuinely different from the x86 world, and a common source of confusion. See a
> digital-logic reference §21 for the general boot model.**
```
⚠️ ⚠️ THERE IS NO ARCHITECTURAL EQUIVALENT OF THE PC BIOS.
   ⚠️ x86 has decades of de-facto platform standardization; ARM
   platforms historically each booted their own way, which is
   why "just install Linux on it" is easy on a PC and hard on
   an ARM board
⚠️ THE STANDARD BOOT CHAIN  ⚠️ BL1 (ROM) → BL2 → ⚠️ BL31 (EL3
   RUNTIME — the secure monitor, stays resident) → BL32
   (optional TEE) → ⚠️ BL33 (the normal-world bootloader:
   U-Boot, EDK2/UEFI)
⚠️ ⚠️ TRUSTED FIRMWARE-A (TF-A) is the open reference
   implementation of the secure world and monitor, and it is
   what most platforms actually run
⚠️ ⚠️ PSCI (Power State Coordination Interface)  ⚠️ the
   standardized SMC-based interface by which the OS asks
   firmware to power cores on and off. ⚠️ This is how CPU
   hotplug and idle work portably
⚠️ ⚠️ THE STANDARDIZATION EFFORT THAT CHANGED THINGS
   ⚠️ SBSA/BSA (hardware requirements) and SBBR/BBR (firmware
   requirements), under SystemReady certification
   ⚠️ ⚠️ THIS IS WHY ARM SERVERS BOOT A GENERIC OS IMAGE THE WAY
   A PC DOES, AND MOST ARM SBCs AND PHONES DO NOT. ⚠️ The
   difference is certification, not architecture
⚠️ DEVICE TREE vs ACPI  ⚠️ embedded platforms use device tree;
   ⚠️ SystemReady servers use ACPI — and the split is a
   long-running ecosystem argument
```

---
