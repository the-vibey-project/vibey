---
id: skill-14-the-platform-landscape-verified-august-2026-540cff073f
purpose: 14 the platform landscape verified august 2026
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-reference/SKILL.md
requires: ["skill-13-numbers-bb47899ed0"]
links: ["skill-15-resources-30822dfa67"]
---

## §14. The Platform Landscape — verified August 2026

> **⚠️ GOTCHA — this section decays fastest in the document, and the sourcing is weaker
> than the rest.** Much of what follows comes from **XR trade press, vendor blogs, and
> development agencies marketing their services.** ⚠️ **The structural picture is
> corroborated across sources; specific prices, percentages and roadmap dates are not
> measurements. Verify before making a platform commitment.** **§1–§11 → `xr-perceptual-constraints-displays-and-tracking`, `xr-rendering-input-and-spatial-understanding`, `xr-platforms-audio-and-comfort`, `xr-ux-design-and-performance-budgeting` do not depend on
> any of it.**

### 14.1 The three-platform picture
**⚠️ The consistent framing across sources is that platform choice follows use case, not
quality:**
- **Meta Quest** — ⚠️ **the installed base and mature catalogue; the default for scale and
  lowest per-seat cost.** One trade study found **Meta or Quest referenced in 38% of XR
  stories over a four-month 2026 window, more than the next two companies combined.**
  ⚠️ **Horizon OS still favours Meta's own hardware and store, though it does support
  OpenXR.**
- **Apple Vision Pro / visionOS** — ⚠️ **vertically integrated, premium fidelity; the pick
  for visualization, design review and executive demos.** ⚠️ **Coverage in 2026 has been
  substantially retreat-flavoured** — a reduced headset roadmap and cancelled products
  are reported, alongside a 2025 refresh with an upgraded processor and improved
  headstrap.
- **Android XR** (Google + Samsung + Qualcomm) — ⚠️ **the fastest-rising, and reported as
  the #2 platform by coverage share.** Runs standard Android apps, **supports Unity 6,
  OpenXR 1.1 and WebXR**, with **Samsung Galaxy XR** shipping and **XREAL** glasses in the
  ecosystem. **The explicit strategy is the Android playbook applied to XR.**

**Also**: **Valve's Steam Frame** announced, **PICO** (Project Swan flagship indicated for
late 2026), **Varjo** for high-end enterprise/simulation, **HoloLens 2 in maintenance
mode** with enterprise hardware like **HMS SiNGRAY G2** positioned for that gap.
⚠️ **And the sector is volatile — one source notes four VR studios closing within a single
week in 2026.**

**⚠️ Smart glasses are the growth story, not headsets**: reported at **42% of XR coverage**,
with Meta's Ray-Ban line including a display model. **Displays are OLED-on-silicon
near-term with MicroLED in development.**

### 14.2 ⚠️ The genuinely actionable finding — OpenXR and WebXR
**This is the part I'd act on regardless of how the hardware race resolves.**
- **⚠️ OpenXR is the hedge.** Applications built against it run on any conformant headset
  unmodified; **Unity and Unreal both recommend it; Android XR supports OpenXR 1.1, which
  means the same rendering pipeline reaches Quest.** ⚠️ **A multi-platform program is
  increasingly the realistic answer, which is exactly the argument for an OpenXR-based,
  engine-portable strategy now.**
- **WebXR adoption reportedly grew 40% in 2026**, with **Interop 2026 proposing WebXR as a
  focus area** — meaning browser vendors coordinating to close compatibility gaps.
  ⚠️ **One codebase across Quest, Vision Pro, Galaxy XR and phone browsers is a real
  proposition now**, with the usual web trade-offs in performance and device access.

---
