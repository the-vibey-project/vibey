---
id: skill-3-modulation-and-multiple-access-0fc55eaf3d
purpose: 3 modulation and multiple access
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-propagation-link-budget-modulation-antennas-and-spectrum/SKILL.md
requires: ["skill-2-propagation-and-the-link-budget-7a4c4eab1c"]
links: ["skill-4-antennas-e643a11461"]
---

## §3. Modulation and Multiple Access

```
⚠️ MODULATION  ⚠️ ASK/FSK/PSK → QAM. ⚠️ Higher-order QAM packs
   more bits per symbol and DEMANDS higher SNR — ⚠️ this is the
   rate/range trade, made concrete
⚠️ SPREAD SPECTRUM  ⚠️ FHSS (⚠️ Bluetooth — hop away from
   interference) · DSSS · ⚠️ CSS (LoRa's chirp spread spectrum,
   which is why it decodes BELOW the noise floor, §12)
⚠️ ⚠️ OFDM  ⚠️ split the channel into many narrow orthogonal
   subcarriers. ⚠️ A narrow subcarrier sees a FLAT channel, which
   makes equalization tractable and multipath survivable —
   ⚠️ this is the enabling idea behind modern Wi-Fi, LTE and
   5G alike
⚠️ ⚠️ OFDMA  ⚠️ allocate DIFFERENT subcarriers to different users
   in the same transmission. ⚠️ The key Wi-Fi 6 change, and it
   helps DENSITY and small packets rather than peak speed
⚠️ MULTIPLE ACCESS  ⚠️ CSMA/CA with backoff (Wi-Fi — ⚠️ note it
   CANNOT detect collisions like Ethernet, only avoid them,
   hence RTS/CTS and the HIDDEN NODE problem) · TDMA · FDMA ·
   CDMA · polling
⚠️ MIMO  ⚠️ spatial multiplexing (⚠️ independent streams, needs
   RICH MULTIPATH to work — ⚠️ counter-intuitively, a clean
   line-of-sight channel gives WORSE MIMO gain) · beamforming ·
   diversity · MU-MIMO
⚠️ ERROR CONTROL  FEC, interleaving, ARQ and hybrid ARQ
```

---
