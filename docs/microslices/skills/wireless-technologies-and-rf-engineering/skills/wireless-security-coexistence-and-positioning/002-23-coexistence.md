---
id: skill-23-coexistence-0935160e1d
purpose: 23 coexistence
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-security-coexistence-and-positioning/SKILL.md
requires: ["skill-22-wireless-security-339d0f6975"]
links: ["skill-24-positioning-and-sensing-12ef0f723b"]
---

## §23. ⚠️ Coexistence

> **⚠️ §1 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`'s second organizing idea. You share the band, and the interferers are often your
> own.**
```
⚠️ SAME-BAND NEIGHBOURS  ⚠️ 2.4 GHz holds Wi-Fi, Bluetooth,
   Zigbee, Thread, proprietary remotes, wireless mice, video
   senders — ⚠️ and MICROWAVE OVENS, which are genuinely
   disruptive and periodic
⚠️ ⚠️ IN-DEVICE COEXISTENCE IS THE HARDER PROBLEM  ⚠️ Wi-Fi and
   Bluetooth radios centimetres apart on the same board, often
   sharing an antenna. ⚠️ PTA (packet traffic arbitration) and
   time-division coexistence schemes exist for exactly this,
   and combo chips handle it internally
⚠️ ⚠️ USB 3 RADIATES BROADBAND NOISE AROUND 2.4 GHz. ⚠️ This is a
   documented, real effect that desensitizes nearby receivers —
   ⚠️ move the dongle or use a short extension cable. It is the
   most common "my wireless mouse is broken" cause
⚠️ OTHER SELF-INTERFERENCE  ⚠️ switching regulator harmonics ·
   display and camera clocks · unshielded high-speed buses
⚠️ MITIGATIONS  ⚠️ frequency planning · adaptive frequency
   hopping (⚠️ Bluetooth's AFH actively avoids busy channels) ·
   antenna separation and isolation · filtering · shielding ·
   time-division scheduling · ⚠️ and simply choosing a
   different band
⚠️ ⚠️ REGULATORY COEXISTENCE IS ALSO CONTESTED  ⚠️ 6 GHz
   allocation, and the interests of incumbent licensed users
   versus unlicensed expansion, are an active policy fight —
   which is worth knowing because it determines what spectrum
   your product may use in a few years
```

---
