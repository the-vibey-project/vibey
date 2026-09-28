---
id: skill-7-colour-and-tone-mapping-1a2f4c24e8
purpose: 7 colour and tone mapping
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-gpu-real-time-techniques-and-colour/SKILL.md
requires: ["skill-6-real-time-techniques-597f5adbcd"]
links: []
---

## §7. Colour and Tone Mapping

**⚠️ Linear vs sRGB is the single most common correctness bug in graphics.** sRGB encoding
is roughly a **2.2 gamma** curve. **All lighting math must happen in linear space.**
```
Texture (sRGB) → decode to linear → light and blend in LINEAR → tone map
  → encode to sRGB → display
```
⚠️ **Use hardware sRGB texture formats and framebuffers so the conversion happens for
free and in the right place. Blending in sRGB space produces visibly wrong midtones** —
the classic symptom is dark fringes around bright objects and washed-out alpha edges.

**HDR and tone mapping**: rendering happens in unbounded linear HDR; the display is
limited. **Reinhard** (simple), **ACES** (⚠️ **the film-industry standard curve, and the
default look for a reason**), **AgX** (⚠️ **newer, and better-behaved at extreme
saturation where ACES skews hues**), **Uncharted 2 / Hable**.
**Colour spaces**: sRGB/Rec.709, **Rec.2020**, DCI-P3, ACEScg (⚠️ **the right working
space for wide-gamut rendering**). **PQ (ST.2084)** and HLG for HDR display transfer.
