---
id: skill-11-machining-55ef8929f3
purpose: 11 machining
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-process-families-machining-additive-and-moulding/SKILL.md
requires: ["skill-10-casting-and-forming-47bbbcb21f"]
links: ["skill-12-joining-f46c479225"]
---

## §11. Machining

**⚠️ Turning (lathe — rotating workpiece), milling (rotating tool), drilling, boring,
grinding, and ⚠️ EDM (electrical discharge — cuts hardened material and internal sharp
corners that a rotating cutter physically cannot).**
```
⚠️ THE DESIGN CONSEQUENCES OF A ROUND CUTTER
   ⚠️ Internal corners CANNOT be sharp — they carry the tool radius.
      ⚠️ Design them with a radius or you're asking for EDM
   ⚠️ Deep narrow pockets need long thin tools that CHATTER and
      deflect — depth-to-diameter ratio is a real limit
   ⚠️ Every SETUP (re-fixturing) costs money and adds tolerance error
   ⚠️ Undercuts and internal features may be unreachable
```
**⚠️ CNC and the toolpath**: ⚠️ **G-code, CAM software, 3-axis vs 5-axis (⚠️ 5-axis reduces
setups and reaches more geometry, at much higher cost), and workholding — which is
frequently the hard part, not the cutting.**
**⚠️ Speeds, feeds and tool wear** — ⚠️ **and the reason material machinability varies so
much: stainless work-hardens, aluminium gums, titanium holds heat in the tool.**

---
