---
id: skill-12-coding-and-retransmission-1bc572f0c9
purpose: 12 coding and retransmission
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-spread-spectrum-ofdm-access-and-sdr/SKILL.md
requires: ["skill-11-ofdm-fbc6424340"]
links: ["skill-13-multiple-access-cff0c792f0"]
---

## §12. Coding and Retransmission

**⚠️ Every real radio link is running errors and correcting them beneath you.**
```
FEC    ⚠️ forward error correction — add redundancy so errors are fixed
       without retransmission. Convolutional/Viterbi, Reed-Solomon,
       ⚠️ Turbo and LDPC (near-Shannon; LDPC in Wi-Fi, 5G), Polar (5G control)
CRC    ⚠️ DETECTS errors; does not correct them
INTERLEAVING  ⚠️ scatter bits in time so a BURST error becomes many
       single-bit errors that FEC can handle. Essential against fading (§6)
ARQ    retransmission. ⚠️ HARQ combines retransmissions with the failed
       copy rather than discarding it — used throughout LTE/5G
```
**⚠️ Coding gain is real and large**: **a good FEC can buy 5–10 dB, which by §3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs` is
several times the range.** ⚠️ **It costs data rate and latency, which is why low-latency
modes use weaker coding.**

---
