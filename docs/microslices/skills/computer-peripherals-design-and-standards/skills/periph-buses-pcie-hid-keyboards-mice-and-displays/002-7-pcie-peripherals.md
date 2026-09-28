---
id: skill-7-pcie-peripherals-e901df6cf3
purpose: 7 pcie peripherals
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-buses-pcie-hid-keyboards-mice-and-displays/SKILL.md
requires: ["skill-6-embedded-buses-3ba69f5d10"]
links: ["skill-8-hid-fa00d40792"]
---

## §7. PCIe Peripherals

**⚠️ Where bandwidth or latency demands exceed USB**: ⚠️ **GPUs, capture cards, NICs,
NVMe, professional audio interfaces.**
**⚠️ The architecture**: ⚠️ **BARs (base address registers) map device memory into the
host address space, MSI/MSI-X for interrupts, DMA for bulk movement, and configuration
space for enumeration.**
**⚠️ Option ROMs and UEFI drivers** allow a device to participate in boot.
**⚠️ The advantage over USB is DMA** — ⚠️ **the device writes directly to host memory
rather than being polled — which is also exactly why PCIe devices are a security concern
and why the IOMMU exists** (§24 → `periph-compliance-accessibility-and-security`).

---

# PART II — DEVICE CLASSES
