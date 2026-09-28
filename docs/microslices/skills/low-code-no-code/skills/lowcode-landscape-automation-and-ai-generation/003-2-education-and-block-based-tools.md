---
id: skill-2-education-and-block-based-tools-c07a64b434
purpose: 2 education and block based tools
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-landscape-automation-and-ai-generation/SKILL.md
requires: ["skill-1-the-taxonomy-a1e31d17be"]
links: ["skill-3-workflow-automation-c9b091d735"]
---

## §2. Education and Block-Based Tools

**[DURABLE] A different thing entirely from the rest of this document.** The goal is not
shipping software; it's building mental models — sequencing, conditionals, loops, events,
state — **without the syntax barrier that stops beginners before they reach the concepts.**

**Scratch** (MIT Media Lab) is the anchor: the largest, free, with an enormous shared
project library, and the visual grammar most other tools imitate. **MakeCode** (Microsoft)
drives the **BBC micro:bit** and can toggle between blocks and JavaScript/Python —
⚠️ **that toggle is pedagogically the important feature**, because it makes the transition
to text visible rather than a cliff. **Blockly** (Google) is the underlying library.
**Snap!** extends Scratch with first-class functions and recursion.

### 2.1 ⚠️ The LEGO situation — a live cautionary tale

**[VERSIONED, and this one has moved twice.]**

- **LEGO Mindstorms was discontinued in December 2022** (announced October 2022), ending a
  line that ran from 1998 and, as MIT-Media-Lab-derived technology, **was the first home
  robotics kit available to a wide audience.**
- **SPIKE Prime** became the successor and the FIRST LEGO League platform.
- ⚠️ **In January 2026 LEGO Education announced the SPIKE portfolio is also being
  retired.** **End of sales 30 June 2026** for SPIKE Prime and SPIKE Essential, replaced
  by the new **LEGO Education Computer Science & AI** line (shipping from April 2026,
  K–8, from ~$339.95, designed for **groups of four rather than individual screens**).
- **Software support continues to 30 June 2031** — bug fixes and OS compatibility only,
  **no new features after June 2026**, and the curriculum stays online until 2031.
- **FIRST LEGO League**: SPIKE remains eligible **through the 2027–28 season**; the new CS
  & AI line becomes usable from **2026–27**.

> **⚠️ GOTCHA — the durable lesson, which generalizes well beyond LEGO.** A frustrated but
> accurate community summary put SPIKE as joining **"9v trains, Mindstorms, Spybotics,
> Power Functions, Boost, Control+, Powered Up… on the ever-increasing pile of short-lived
> and now obsolete LEGO technology products that do not offer an upgrade path."**
>
> **This is the low-code bargain in miniature**: a beautifully designed closed ecosystem,
> adopted widely, retired on the vendor's schedule, **with no migration path for the
> curriculum, hardware, or skills built on it.** The counterweight is instructive too —
> **Pybricks**, a third-party MicroPython firmware, keeps NXT, EV3, Robot Inventor, SPIKE
> Prime and SPIKE Essential alive on a common modern stack. **The open layer outlived the
> vendor's product decisions**, which is the argument for §13 → `lowcode-lock-in-and-engineering-practice` in a nutshell.

**[DURABLE] The pedagogical debate worth knowing**: block languages remove syntax errors
and let beginners reach concepts fast, **but there's a real "transition cliff" to text**,
and some educators argue blocks create habits that don't transfer. **The consensus that
has emerged is dual-mode tools** — MakeCode's block/text toggle, SPIKE's blocks-then-Python
path — rather than blocks alone.

**Alternatives worth knowing** if you're choosing now: **VEX IQ / VEX GO** (strong
competition ecosystem), **micro:bit** (⚠️ **cheapest credible entry, and genuinely
open**), **Arduino and Raspberry Pi kits** (no vendor retirement risk — see a DIY-kit
reference), **Sphero**, **mBot**, **Ozobot**.

---
