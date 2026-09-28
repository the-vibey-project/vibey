---
id: skill-16-train-protection-atp-etcs-ptc-cbtc-d9af39c4cc
purpose: 16 train protection atp etcs ptc cbtc
source: src/vibey_tools/skills/plugins/locomotion-and-train-technologies/skills/rail-signalling-interlocking-train-protection-and-safety/SKILL.md
requires: ["skill-15-interlocking-c82835b84d"]
links: ["skill-17-safety-and-failure-modes-6f1adbc2d3"]
---

## §16. Train Protection: ATP, ETCS, PTC, CBTC

```
⚠️ THE PROBLEM  signals only work if the driver sees and obeys them.
   ⚠️ SPADs (Signal Passed At Danger) have caused many major accidents
⚠️ AWS / warning systems  audible warning; driver must acknowledge.
   ⚠️ Warns but does not enforce — and acknowledgement can become reflex
⚠️ ATP (Automatic Train Protection)  ⚠️ ENFORCES. Supervises speed and
   applies brakes if the driver does not
⚠️ ETCS LEVELS
   ⚠️ L1  intermittent, balise-based, works alongside lineside signals
   ⚠️ L2  continuous radio (GSM-R → FRMCS), ⚠️ movement authority in
      the cab, LINESIDE SIGNALS CAN BE REMOVED. The current standard
   ⚠️ L3  moving block — ⚠️ no fixed block sections; requires reliable
      train integrity monitoring, which is the hard part for freight
⚠️ PTC (US)  Positive Train Control — enforces stops, speed limits,
   work zones and switch position
⚠️ CBTC  metro-focused, radio-based, ⚠️ moving block, the basis of
   driverless operation
⚠️ GoA (Grades of Automation) 1–4  ⚠️ GoA4 is unattended
```
**⚠️ The capacity argument for ETCS L2 is genuine** — ⚠️ **SNCF reports an expected 25%
capacity increase on one line, from 13 to 16 trains per hour per direction** — **because
continuous supervision allows shorter, better-optimized headways than fixed multi-aspect
signals** (§20 → `rail-rolling-stock-braking-capacity-and-service-types`).
**⚠️ Why moving block is hard for freight** (§26.1 → `rail-reference`): ⚠️ **the system must know where the
REAR of the train is, and a freight train that has parted must be detected.** **On a metro
with fixed-formation units this is trivial; on a 100-wagon freight it is not.**

---
