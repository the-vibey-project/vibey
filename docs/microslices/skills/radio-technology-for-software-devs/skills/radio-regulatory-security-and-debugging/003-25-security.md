---
id: skill-25-security-4e22411d6b
purpose: 25 security
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-regulatory-security-and-debugging/SKILL.md
requires: ["skill-24-what-moved-verified-august-2026-4179363e5a"]
links: ["skill-26-debugging-rf-from-software-d46e5f9449"]
---

## §25. Security

**⚠️ Radio is broadcast. Assume everything is being received by someone else.**
```
⚠️ EAVESDROPPING   passive, undetectable, and cheap with an RTL-SDR
⚠️ REPLAY          capture and retransmit. ⚠️ Defeats any system without a
   rolling code, nonce or timestamp — this is how many garage doors,
   car fobs and cheap sensors fall
JAMMING            trivial and hard to defend against; spread spectrum helps
SPOOFING           especially GNSS (§22)
⚠️ SIDE CHANNELS   RF emissions leak information (TEMPEST); ⚠️ and RSSI-based
   proximity is trivially defeated by an amplifier — relay attacks against
   keyless entry are the standard example
```
**⚠️ Practical requirements**: **encrypt at the application layer and do not trust link
encryption alone**; ⚠️ **use authenticated encryption with nonces or counters — encryption
without replay protection is not enough**; **provision unique per-device keys, never a
shared global key**; **sign firmware updates**; ⚠️ **and for proximity claims use a
protocol with cryptographic distance bounding (UWB) rather than signal strength.**
**⚠️ BLE pairing modes matter**: **Just Works provides no MITM protection.** **Use
passkey or numeric comparison where the threat model warrants it.**

---
