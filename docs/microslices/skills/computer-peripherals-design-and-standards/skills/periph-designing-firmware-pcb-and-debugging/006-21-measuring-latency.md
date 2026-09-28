---
id: skill-21-measuring-latency-64bb759a23
purpose: 21 measuring latency
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-designing-firmware-pcb-and-debugging/SKILL.md
requires: ["skill-20-drivers-and-os-integration-e4838fa83e"]
links: []
---

## §21. ⚠️ Measuring Latency

> **⚠️ §1 → `periph-stack-usb-thunderbolt-and-wireless`'s third organizing idea, made concrete.**
```
⚠️ THE FULL CHAIN, and every link adds
   ⚠️ Physical actuation and switch travel
   ⚠️ DEBOUNCE window (§9)
   ⚠️ Matrix scan interval
   ⚠️ ⚠️ USB POLLING INTERVAL — ⚠️ 1000 Hz = 1 ms, 125 Hz = 8 ms
   ⚠️ OS input stack and application
   ⚠️ Render and present queue
   ⚠️ ⚠️ DISPLAY SCANOUT AND PIXEL RESPONSE — ⚠️ at 60 Hz this
      alone averages ~8 ms of the total
⚠️ ⚠️ THE ARITHMETIC PEOPLE SKIP: going from 1000 Hz to 8000 Hz
   polling saves at most ~0.9 ms. ⚠️ Going from a 60 Hz to a
   240 Hz display saves several times that. ⚠️ Optimize the
   largest term
⚠️ HOW TO ACTUALLY MEASURE  ⚠️ high-speed camera on the input and
   the screen together (the ground truth) · ⚠️ instrumented
   hardware that shorts a switch and watches the display ·
   ⚠️ latency test tools in-OS. ⚠️ Software timestamps alone
   cannot see the ends of the chain
⚠️ VARIANCE MATTERS MORE THAN MEAN  ⚠️ consistent 5 ms feels
   better than 2 ms averaging with occasional 20 ms spikes
```

---

# PART IV — CROSS-CUTTING
