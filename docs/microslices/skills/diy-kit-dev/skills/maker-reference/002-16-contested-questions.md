---
id: skill-16-contested-questions-9215fffa11
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-reference/SKILL.md
requires: ["skill-15-anti-patterns-122967ed57"]
links: ["skill-17-currency-snapshot-verified-august-2026-dd7aa6a206"]
---

## §16. Contested Questions

**16.1 Arduino or ESP32 for a beginner?** *Arduino Uno*: 5V-tolerant and hard to destroy,
every tutorial targets it, no Wi-Fi to complicate things. *ESP32*: vastly more capable for
the same money, Wi-Fi built in, and you won't outgrow it in a month. **[CONTESTED. The
defensible split: Uno if you're learning electronics; ESP32 if you're a software engineer
who wants a connected thing working this weekend.]**

**16.2 Does the Qualcomm acquisition matter?** §3.1 → `maker-boards-and-platforms`. **Genuinely unresolved.** Nothing has
broken; the commitments are stated; the community is skeptical and the skepticism isn't
unreasonable given the T&C episode. **The practical hedge is platform diversity, not
panic.**

**16.3 MicroPython or C/C++?** *Python*: faster iteration, REPL, lower barrier, and
adequate for most sensor-and-network work. *C/C++*: performance, memory, real-time, full
library access, and where production ends up. **Most projects never need C. Some can't
work without it.**

**16.4 Raspberry Pi or the alternatives?** §2.3 → `maker-boards-and-platforms`. Better specs per dollar elsewhere;
**Pi's advantage is ecosystem, documentation, and long-term availability**, and for
beginners that dominates.

**16.5 Should hobbyists design PCBs?** *For*: cheap, reliable, compact, and KiCad is free
and good. *Against*: real learning curve, and three revisions of shipping delay.
**⚠️ Worth it once you're building more than one of something, or once wiring reliability
is the limiting factor.**

**16.6 Is the maker movement in decline?** ⚠️ **Genuinely contested.** *For decline*: the
2010s peak has passed, Maker Media's difficulties, cheap finished products undercutting
DIY. *Against*: 3D printing is far cheaper and better, board capability has exploded,
Home Assistant and ESPHome created a huge new practical use case, and the barrier to a
custom PCB has collapsed. **The character changed more than the size.**

---
