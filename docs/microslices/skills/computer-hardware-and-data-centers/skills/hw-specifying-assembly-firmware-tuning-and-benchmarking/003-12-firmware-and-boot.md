---
id: skill-12-firmware-and-boot-8e5651ffe5
purpose: 12 firmware and boot
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-specifying-assembly-firmware-tuning-and-benchmarking/SKILL.md
requires: ["skill-11-assembly-3a83a71026"]
links: ["skill-13-tuning-and-overclocking-honestly-24770cb634"]
---

## §12. Firmware and Boot

**⚠️ UEFI replaced BIOS** — ⚠️ **GPT partitioning, larger disks, faster boot, and Secure
Boot.**
**⚠️ POST and the boot chain**: ⚠️ **firmware → bootloader → kernel → init, and knowing this
sequence is what lets you diagnose where a boot failure occurs.**
**⚠️ Settings that actually matter**: ⚠️ **XMP/EXPO to run memory at its rated speed
(⚠️ memory ships at JEDEC defaults and does NOT run at advertised speed until you enable
it — an extremely common oversight), resizable BAR, virtualization extensions, fan curves,
and boot order.**
**⚠️ Firmware updates** fix real bugs including microcode and stability issues — ⚠️ **and a
failed flash can brick a board, so use the vendor's recovery mechanism where available and
don't update without reason.**
**⚠️ Secure Boot and TPM** underpin measured boot and disk encryption (see a cryptography
reference §15).

---
