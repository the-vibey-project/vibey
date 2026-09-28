---
id: skill-25-what-s-live-checked-august-2026-95cd586982
purpose: 25 what s live checked august 2026
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-reference/SKILL.md
requires: []
links: ["skill-26-misconceptions-065e09cd61"]
---

## §25. What's Live — checked August 2026

### 25.1 ⚠️ USB bandwidth, and the labelling reform
**⚠️ §2 → `periph-stack-usb-thunderbolt-and-wireless`'s naming disaster finally being addressed — and §3 → `periph-stack-usb-thunderbolt-and-wireless`'s power ceiling now in shipping
products.**

- **⚠️ THE SPEC.** ⚠️ **USB4 Version 2.0 was published by the USB Promoter Group to enable
  80 Gbps over the existing USB-C cable and connector, based on a new physical layer
  architecture, doubling the previous maximum aggregate bandwidth.** ⚠️ **USB-IF's own
  announcement notes it can optionally run ASYMMETRICALLY — up to 120 Gbps in one direction
  while retaining 40 Gbps in the other — specifically for driving very high-performance
  displays.**
- **⚠️ WHAT ELSE THE VERSION 2.0 UPDATE CARRIES**: ⚠️ **PCIe tunnelling advancing to Gen4,
  doubling per-lane throughput for external SSDs and eGPU enclosures relative to Gen3
  tunnelling in USB4 v1; and DisplayPort tunnelling advancing to DisplayPort 2.1 with
  UHBR20 signaling** (§25.2). ⚠️ **Backward compatibility with USB4 v1, Thunderbolt 3 and
  Thunderbolt 4 is retained, with those devices falling back to older signaling.**
- **⚠️ THE LABELLING REFORM.** ⚠️ **The USB-IF has shifted from version-based branding to
  explicit capability identifiers: "USB 40Gbps", "USB 80Gbps" and "240W" markings on
  certified cables and packaging.** ⚠️ **The USB-IF states plainly that specification names
  and technical terminology are NOT intended for describing capabilities to end
  consumers.**
- **⚠️ POWER.** ⚠️ **Power Delivery can negotiate up to 240 W on capable ports under PD 3.1,
  using voltages up to 48 V.**

> **⚠️ GOTCHA — the cable is now a first-class variable, and length is the physical
> limit.** ⚠️ **Passive USB4 40 Gbps cables are commonly limited to around 0.8 m; reporting
> indicates many certified passive USB-C cables up to one metre support 80 Gbps, with
> anything longer typically requiring ACTIVE RETIMERS.**
> ⚠️ **Those active cables contain embedded signal processing and SOMETIMES OPERATE
> DIRECTIONALLY — which introduces real design considerations for hubs and monitors, and
> means an active cable is not simply a longer passive one.**
> **⚠️ The counterfeit problem is the practical hazard.** ⚠️ **Guidance is to look for
> laser-etched USB-IF logos, a scannable code linking to the certification database, and
> explicit text markings — and to treat "USB4-compatible" phrasing and printed-not-etched
> logos as red flags.**

**⚠️ My honest assessment of the reform**: ⚠️ **the shift to speed-and-wattage labels is the
right fix and directly addresses §2 → `periph-stack-usb-thunderbolt-and-wireless`'s problem, but as one outlet notes, adoption depends on
consistent enforcement by manufacturers and retailers — and the older Gen-x-by-y
terminology remains in circulation alongside it.** ⚠️ **Practical advice unchanged: check
the PORT spec, the CABLE spec and the DEVICE spec separately, because the slowest link
governs and a fast cable cannot upgrade a slow port.**

### 25.2 ⚠️ Display interfaces: the bandwidth tiers matter more than the version badge
**⚠️ §11 → `periph-buses-pcie-hid-keyboards-mice-and-displays`'s interface question, and the trap is buying on the version number.**

- **⚠️ DISPLAYPORT 2.1's TIERS.** ⚠️ **UHBR10, UHBR13.5 and UHBR20, with UHBR20 giving four
  lanes at 20 Gbps for 80 Gbps total link bandwidth.** ⚠️ **DisplayPort 2.1 uses 128b/132b
  encoding rather than the older 8b/10b, substantially reducing overhead so more of the raw
  rate is usable.**
- **⚠️ THE BADGE DOES NOT TELL YOU THE TIER — this is the central practical point.**
  ⚠️ **A device can carry a DisplayPort 2.1 badge while implementing only UHBR13.5.**
  ⚠️ **One guide's framing is right: the 2026 DP 2.1 ecosystem "rewards precise matching
  over blanket assumptions about the DP 2.1 badge."**
- **⚠️ CABLES ARE CERTIFIED SEPARATELY AND BY TIER.** ⚠️ **VESA-certified DP80 cables must
  support UHBR20 across four lanes for 80 Gbps; DP54 supports UHBR13.5 for 54 Gbps over a
  two-metre passive cable.** ⚠️ **Passive DP80 is reliable to roughly one metre — reporting
  notes in-box cables with UHBR20 monitors are often only 1 m — and VESA introduced
  DP80LL "low loss" ACTIVE cables to give up to three metres at UHBR20, roughly triple the
  passive length.**
- **⚠️ HDMI 2.2** was introduced at CES 2025 with an "Ultra96" certified cable programme and
  QR-code verification. ⚠️ **Note the adoption lag: reporting observes it took about two
  years from HDMI 2.1 to the first supported TVs and around four years to widespread
  adoption — so a new HDMI version number is a multi-year signal, not a this-year one.**

> **⚠️ GOTCHA — DSC is not the compromise people assume, and the honest comparison is
> narrower than the marketing.** ⚠️ **DSC is a hardware, visually lossless algorithm applying
> roughly 3:1 compression with latency in MICROSECONDS — categorically different from
> streaming video compression.**
> ⚠️ **UHBR20 is described as currently the only interface able to drive 4K 240 Hz 10-bit
> HDR uncompressed, while UHBR13.5 reaches 4K 240 Hz WITH DSC and handles roughly 187 Hz at
> 10-bit HDR uncompressed.** ⚠️ **The reported practical differences from going uncompressed
> are avoiding occasional alt-tab black screens and handshake quirks — not image quality.**
> **⚠️ And the ceiling still applies: even UHBR20 reportedly requires DSC for the most
> extreme modes.**
> ⚠️ **So the reasonable position is that DSC is fine for almost everyone, and UHBR20 is
> worth paying for only if you have confirmed the whole chain — GPU, monitor input AND
> certified cable — supports it and you specifically want an uncompressed path.**

**⚠️ Sourcing note: VESA and the USB-IF primary announcements anchor the specifications, and
TFTCentral is the most technically careful independent source on DisplayPort certification
in practice.** ⚠️ **Several other sources here are monitor and cable vendors, whose framing
favours buying the higher tier — I have marked the practical claims as reported and stated
the more conservative reading.**

---
