---
id: skill-26-debugging-rf-from-software-d46e5f9449
purpose: 26 debugging rf from software
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-regulatory-security-and-debugging/SKILL.md
requires: ["skill-25-security-4e22411d6b"]
links: []
---

## §26. ⚠️ Debugging RF From Software

**⚠️ An ordered procedure, because guessing is expensive here:**
```
1. ⚠️ IS IT A LINK BUDGET PROBLEM? Compute it (§3). Compare predicted RSSI
   to measured. A 20 dB discrepancy points at the antenna or the enclosure
2. ⚠️ LOOK AT THE SPECTRUM. An RTL-SDR and a waterfall display will show you
   interference in thirty seconds that you'd never find in logs
3. ⚠️ MOVE IT. If moving the device 10 cm changes everything, it's
   multipath fading (§6), not your code
4. ⚠️ CHECK RSSI **AND** SNR/LQI. Strong RSSI with bad SNR = interference (§7)
5. ⚠️ TURN OFF YOUR OWN SUBSYSTEMS one at a time. Self-interference (§7)
6. ⚠️ SNIFF THE PROTOCOL. A cheap BLE/802.15.4 sniffer shows retries and
   which side is failing
7. ⚠️ TEST WITH A CABLE and attenuators. Removing the air removes variables
8. ⚠️ CHECK ORIENTATION AND POLARIZATION (§5)
9. ⚠️ CHECK REGULATORY BEHAVIOUR — DFS events and duty-cycle blocking look
   exactly like random unexplained outages (§23)
10. ⚠️ LOG RSSI/SNR/retry counts CONTINUOUSLY IN PRODUCTION. RF problems are
    statistical and you cannot debug them from a single incident report
```
**⚠️ The instrumentation that pays for itself**: **an RTL-SDR ($30) for spectrum
visibility, a protocol sniffer for your radio family, a set of RF attenuators for
bench-testing range without walking around a car park, and — if you can — a few hours with
a spectrum analyzer at the deployment site.**
