---
id: skill-4-thunderbolt-and-alternate-modes-cd7a050602
purpose: 4 thunderbolt and alternate modes
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-stack-usb-thunderbolt-and-wireless/SKILL.md
requires: ["skill-3-usb-c-and-power-delivery-5719929265"]
links: ["skill-5-wireless-peripherals-fe83353333"]
---

## §4. Thunderbolt and Alternate Modes

**⚠️ ALT MODE** reconfigures USB-C's high-speed pins to carry a different protocol
entirely — ⚠️ **most importantly DisplayPort, which is how USB-C carries video** (§11 → `periph-buses-pcie-hid-keyboards-mice-and-displays`).
**⚠️ Thunderbolt** tunnels PCIe and DisplayPort over the same connector.
⚠️ **Thunderbolt 3 was contributed to USB4, which is why USB4 and Thunderbolt look so
similar; ⚠️ Thunderbolt 4 aligns closely with USB4 while MANDATING a feature set that USB4
leaves optional, and Thunderbolt 5 reaches 80 Gbps.**
> **⚠️ GOTCHA — the crucial difference is MANDATORY versus OPTIONAL.** ⚠️ **USB4 allows
> manufacturers to omit PCIe tunnelling and dual-display support to cut cost; Thunderbolt
> requires them.** **⚠️ So "USB4" tells you less about what a port can do than "Thunderbolt
> 4" does — a rare case where the proprietary standard is the clearer promise.**

**⚠️ PCIe tunnelling** is what makes eGPUs and external NVMe enclosures work, ⚠️ **and it
also creates a DMA security exposure that IOMMU protection exists to contain** (§24 → `periph-compliance-accessibility-and-security`).
**⚠️ Compatibility rules of thumb**: ⚠️ **Thunderbolt 4 and 5 hosts handle USB4 devices;
USB4 hosts support Thunderbolt 3 and 4 devices; Thunderbolt 3 hosts typically handle USB
devices only up to 10 Gbps.**

---
