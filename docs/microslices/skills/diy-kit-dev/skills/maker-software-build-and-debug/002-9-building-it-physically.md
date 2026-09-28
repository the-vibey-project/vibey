---
id: skill-9-building-it-physically-ef13a49de0
purpose: 9 building it physically
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-software-build-and-debug/SKILL.md
requires: ["skill-8-the-software-layer-7bd50055ad"]
links: ["skill-10-debugging-hardware-a011fcbc60"]
---

## §9. Building It Physically

### 9.1 The prototyping ladder
```
Breadboard        → fast, reusable, ⚠️ unreliable connections; NOT for anything permanent
                    or anything above ~1A, and hopeless at high frequency
Perfboard/stripboard → soldered, permanent, cheap, ugly. Fine for one-offs
Protoboard/shield → purpose-made boards for Arduino/Pi form factors
Custom PCB        → §13. Cheaper than people think
```
**⚠️ A large share of "intermittent" bugs are breadboard contact problems**, especially
after the board has been used a few times. **If a circuit works when you press on it,
that's your answer.**

### 9.2 Soldering
**[DURABLE] It's a learnable skill and worth two hours of deliberate practice.**
**Temperature-controlled iron** (~350°C for leaded, ~370°C for lead-free), **flux is not
optional** (⚠️ **most soldering problems are flux problems**), **heat the joint and feed
solder to the joint — not to the iron**, **tin the tip and keep it clean**, and
**⚠️ ventilate — the fumes are flux, and you shouldn't breathe them.**

**Leaded solder is easier to work with and is a lead exposure risk**; lead-free needs more
heat. Either way: **wash your hands, don't eat at the bench.**

**Also useful**: heat-shrink over every splice (⚠️ **never leave bare twisted wire**),
**JST/Dupont/screw terminals** for connections you'll want to undo, **strain relief** on
anything that moves, and **ferrules** on stranded wire going into screw terminals.

### 9.3 Wiring practice
**⚠️ Colour-code consistently** (red = V+, black = ground, and stick to it).
**Label everything.** **Keep signal wires away from motor wires** — motor noise couples
into signal lines and produces exactly the kind of intermittent fault you'll blame on
software. **Twist power pairs.** **Document the pinout as you go** — ⚠️ **you will not
remember which GPIO the relay is on in six months, and tracing it is worse than writing it
down.**

---
