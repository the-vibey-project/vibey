---
id: skill-14-block-signalling-41b5431dfe
purpose: 14 block signalling
source: src/vibey_tools/skills/plugins/locomotion-and-train-technologies/skills/rail-signalling-interlocking-train-protection-and-safety/SKILL.md
requires: []
links: ["skill-15-interlocking-c82835b84d"]
---

## §14. ⚠️ Block Signalling

**⚠️ Because trains cannot stop on sight (§1 → `rail-adhesion-resistance-traction-physics-and-geometry`), the line is divided into BLOCKS and only one
train is permitted in a block at a time.**
```
⚠️ TRACK CIRCUIT  ⚠️ the elegant original: a low voltage applied to the
   two rails of a block, with a relay at the far end. ⚠️ A train's axles
   SHORT the circuit, dropping the relay and proving occupancy
   ⚠️ FAIL-SAFE BY DESIGN: a broken rail, a power failure or a
   disconnection all drop the relay and show the block as OCCUPIED
   ⚠️ Vulnerable to poor shunting — rust, sand (§1), lightweight vehicles
AXLE COUNTERS  count axles in and out. ⚠️ Works with any rail condition
   and does NOT detect broken rails — a real trade-off
⚠️ MULTI-ASPECT SIGNALLING  green / double yellow / yellow / red gives
   the driver progressively more braking distance than one block provides
⚠️ ABSOLUTE BLOCK, permissive block, token and staff systems on
   single lines (⚠️ physical possession of a unique token as a
   mechanical guarantee — crude and extremely robust)
```
> **⚠️ GOTCHA — "fail-safe" in railway signalling means something specific and stronger
> than in most engineering.** ⚠️ **It means every credible failure moves the system toward
> the RESTRICTIVE state: signals show danger, relays drop, brakes apply.** **⚠️ This is
> why railway signalling used heavy gravity-drop relays for a century and why the
> discipline was so conservative about electronics — a stuck-up relay contact is a
> fatality.**

---
