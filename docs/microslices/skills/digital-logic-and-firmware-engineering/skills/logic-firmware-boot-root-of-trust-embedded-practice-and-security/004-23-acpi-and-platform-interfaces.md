---
id: skill-23-acpi-and-platform-interfaces-9c9d2cc3c8
purpose: 23 acpi and platform interfaces
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-firmware-boot-root-of-trust-embedded-practice-and-security/SKILL.md
requires: ["skill-22-root-of-trust-and-verified-boot-1e35a0ada5"]
links: ["skill-24-embedded-firmware-practice-8933cbe46f"]
---

## §23. ACPI and Platform Interfaces

**⚠️ ACPI is how firmware describes the platform to the OS** — ⚠️ **tables (DSDT, SSDT,
MADT, FADT and many more) plus AML, a bytecode the OS interprets.**
**⚠️ Power states** are the visible part: ⚠️ **S-states (system sleep), C-states (CPU idle),
P-states (performance/frequency), D-states (device) — and getting these right is most of
what "sleep doesn't work" bugs are about.**
**⚠️ Device tree** is the alternative model used on ARM and RISC-V embedded systems —
⚠️ **a static description passed to the kernel rather than an interpreted bytecode, and
much easier to reason about.**
**⚠️ SMBIOS/DMI** for inventory data, ⚠️ **and SMM (System Management Mode) as the
x86 mechanism that is both genuinely useful and a serious security concern** (§25).
**⚠️ The practical point**: ⚠️ **an enormous share of "Linux doesn't support this laptop"
problems are ACPI table bugs that Windows tolerates because the vendor tested against
Windows only.**

---
