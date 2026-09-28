---
id: skill-7-electric-traction-d953b97410
purpose: 7 electric traction
source: src/vibey_tools/skills/plugins/locomotion-and-train-technologies/skills/rail-steam-diesel-electric-and-alternative-traction/SKILL.md
requires: ["skill-6-diesel-traction-7a194fa82f"]
links: ["skill-8-power-electronics-and-regeneration-29c356578d"]
---

## §7. Electric Traction

```
⚠️ SUPPLY SYSTEMS — the fragmentation is historical and expensive
  ⚠️ 25 kV 50/60 Hz AC  ⚠️ the modern standard. High voltage = low
     current = lighter catenary and fewer substations
  15 kV 16.7 Hz AC   ⚠️ Germany, Austria, Switzerland, Sweden, Norway —
     a legacy of early AC traction motor limitations
  3 kV DC   Italy, Spain, Belgium, Poland ⚠️ — heavy currents, closely
     spaced substations
  1.5 kV DC  Netherlands, France (south), Japan ⚠️ — worse still
  ⚠️ 750 V DC third rail  ⚠️ metros and southern England. Cheap, low
     clearance, ⚠️ severe current limits and a live conductor at ground level
⚠️ MULTI-SYSTEM locomotives exist because of this patchwork, and they
   are heavier, costlier and more complex for no operational benefit
```
**⚠️ Current collection**: ⚠️ **the pantograph must maintain contact with a wire that is
deliberately ZIG-ZAGGED (stagger) so the contact strip wears evenly rather than grooving.**
**⚠️ At high speed the wire's mechanical wave propagation speed becomes a limit — the
pantograph must not outrun the wave it creates**, **which sets tension and design
requirements** (§23 → `rail-rolling-stock-braking-capacity-and-service-types`).
**⚠️ Neutral sections** separate phases and supply zones; ⚠️ **the train must coast through
them with power off, and running through one under power causes a flashover.**
**⚠️ Return current flows through the RAILS** — ⚠️ **which is exactly the same path used by
track-circuit signalling (§14 → `rail-signalling-interlocking-train-protection-and-safety`), and the interaction between traction return and signalling
is a classic source of subtle, dangerous faults.**

---
