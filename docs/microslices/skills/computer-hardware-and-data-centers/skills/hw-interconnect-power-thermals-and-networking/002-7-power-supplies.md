---
id: skill-7-power-supplies-a2ed6be438
purpose: 7 power supplies
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-interconnect-power-thermals-and-networking/SKILL.md
requires: ["skill-6-interconnect-348ceebf77"]
links: ["skill-8-thermals-c3bcc151e5"]
---

## §7. ⚠️ Power Supplies

```
⚠️ WHAT IT DOES  AC mains → regulated DC rails (12V dominant;
   3.3V and 5V now minor)
⚠️ EFFICIENCY  ⚠️ 80 PLUS tiers. ⚠️ Efficiency PEAKS around
   40-60% load, so a wildly oversized PSU runs LESS efficiently
   at idle — the "buy double what you need" instinct is wrong
⚠️ ⚠️ TRANSIENT RESPONSE IS THE SPEC THAT ACTUALLY MATTERS AND
   ISN'T ON THE BOX. ⚠️ Modern GPUs draw microsecond power spikes
   FAR above their rated average. ⚠️ A PSU with adequate continuous
   rating but poor transient handling will trip OCP and shut the
   system down under load — and it looks like an unstable GPU
⚠️ ⚠️ SINGLE vs MULTI-RAIL · ⚠️ HOLD-UP TIME (ride-through on brief
   mains dips) · ripple · protections (OCP/OVP/OTP/SCP)
⚠️ CONNECTORS  ⚠️ 12VHPWR/12V-2x6 has a documented history of
   melting when not FULLY SEATED — ⚠️ the failure mode is contact
   resistance at partial insertion, and it is an installation
   discipline issue as much as a design one
⚠️ ⚠️ DO NOT MIX CABLES BETWEEN PSUs. Modular connectors are
   NOT standardized pinouts, and mismatched cables destroy hardware
⚠️ UPS  ⚠️ line-interactive vs double-conversion; ⚠️ simulated vs
   pure sine wave matters for active PFC supplies
```

---
