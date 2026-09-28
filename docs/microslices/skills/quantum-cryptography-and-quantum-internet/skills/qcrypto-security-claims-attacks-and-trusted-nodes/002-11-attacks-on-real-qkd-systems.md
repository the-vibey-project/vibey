---
id: skill-11-attacks-on-real-qkd-systems-644c7ac985
purpose: 11 attacks on real qkd systems
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-security-claims-attacks-and-trusted-nodes/SKILL.md
requires: ["skill-10-what-unconditional-security-actually-claims-5c9fe833b3"]
links: ["skill-12-closing-the-device-gap-60a5d6a970"]
---

## §11. ⚠️ Attacks on Real QKD Systems

**⚠️ Every publicly demonstrated break of a QKD system attacked the HARDWARE, not the
protocol. The gap between the security proof's idealized devices and real components is
where the vulnerabilities live.**
```
⚠️ DETECTOR BLINDING  ⚠️ the most damaging class. Bright illumination
   drives avalanche photodiodes out of Geiger mode into linear
   mode, where they respond to CLASSICAL light. ⚠️ The attacker
   then controls exactly which detector fires, learns the whole
   key, and the error rate stays low. ⚠️ Demonstrated against
   commercial systems
⚠️ TIME-SHIFT and EFFICIENCY MISMATCH  detectors whose efficiency
   differs over time lets an attacker bias which one fires
⚠️ PHOTON NUMBER SPLITTING  multi-photon pulses (§6) — decoy
   states are the fix
⚠️ TROJAN HORSE  ⚠️ inject light INTO Alice's device and read the
   reflection to learn her basis settings. ⚠️ Requires optical
   isolators and monitoring to defend
⚠️ LASER SEEDING / injection locking  manipulating the source
⚠️ LASER DAMAGE  ⚠️ permanently altering a component's behaviour
   with high power, then exploiting the modified device
⚠️ SIDE CHANNELS  timing, wavelength, spatial mode leakage
```
**⚠️ The honest reading**: ⚠️ **this is not a scandal — it is normal security engineering,
and the classical world has the same problem (see a cryptography reference on side
channels).** ⚠️ **But it directly undercuts the marketing claim, because "secure by the
laws of physics" is a statement about the protocol and the attacks are on the apparatus.**
**⚠️ It also means QKD needs the same thing everything else needs: certification, testing,
patching and a security update process — for hardware.**

---
