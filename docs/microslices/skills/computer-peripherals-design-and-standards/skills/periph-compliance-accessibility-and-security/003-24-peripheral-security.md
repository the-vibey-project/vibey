---
id: skill-24-peripheral-security-056e6d1850
purpose: 24 peripheral security
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-compliance-accessibility-and-security/SKILL.md
requires: ["skill-23-accessibility-3b77d53865"]
links: []
---

## §24. ⚠️ Peripheral Security

```
⚠️ ⚠️ BADUSB  ⚠️ a device can CLAIM TO BE ANYTHING. ⚠️ A USB stick
   whose firmware declares itself a keyboard can type commands
   at machine speed. ⚠️ THE TRUST MODEL IS THE FLAW: USB has no
   device authentication, and the host believes the descriptor
⚠️ ⚠️ DMA ATTACKS  ⚠️ Thunderbolt and PCIe devices can read host
   memory directly (§7). ⚠️ IOMMU/VT-d and "Thunderbolt security
   levels" exist for this; ⚠️ pre-boot and sleep states have
   been the weak points
⚠️ MALICIOUS CHARGERS AND CABLES  ⚠️ cables with embedded
   implants are commercially available. ⚠️ USB data blockers
   ("USB condoms") and charge-only cables are the mitigation
⚠️ WIRELESS  ⚠️ unencrypted 2.4 GHz keyboard traffic has been
   sniffable and INJECTABLE in documented cases; ⚠️ Bluetooth
   pairing weaknesses recur
⚠️ FIRMWARE  ⚠️ unsigned firmware update paths on peripherals are
   a persistent supply-chain exposure
⚠️ MITIGATIONS  ⚠️ USB device authorization / port control policy ·
   ⚠️ USBGuard on Linux · disable unused ports in firmware ·
   IOMMU enabled · signed firmware · ⚠️ and the plain advice not
   to plug in unknown devices, which remains effective
⚠️ ⚠️ USB4 and USB-C do NOT fix the trust model. ⚠️ They add
   capability, not authentication
```
