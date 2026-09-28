---
id: skill-20-sources-and-method-b161936671
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-reference/SKILL.md
requires: ["skill-19-quick-reference-4a63153f92"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §2 → `smart-tv-platforms-and-10-foot-ui` (10-foot UI),
§3 → `smart-tv-platforms-and-10-foot-ui` (focus and input), §4.3 → `smart-tv-playback-drm-and-performance` (playback metrics), §5.1 → `smart-tv-playback-drm-and-performance` (DRM structure), §6 → `smart-tv-playback-drm-and-performance` (performance),
§8.2 → `smart-tv-monetization-certification-and-operations`, §12 → `smart-tv-monetization-certification-and-operations`, §15 — is synthesized from vendor design guidelines, long-standing platform
documentation, and consistent practitioner reporting. Every **time-sensitive** claim
(platform shares, OS versions, engine matrices, certification requirements, ad specs,
regulation) was verified against a primary or near-primary source in **August 2026** and
is flagged in §17 with a decay-risk rating. Where the trade-off genuinely depends on
platform mix or budget, §16 presents both cases.

**Search log** (August 2026): smart TV OS market share and platform landscape · Amazon
Vega OS and the Fire OS transition · Roku SceneGraph/BrightScript and certification
requirements · Samsung Tizen and LG webOS SDK and Chromium version constraints · CTV
advertising specs, SSAI, ACR, and measurement.

**Primary and near-primary sources consulted (selected):**
- **Samsung Developer** — **Web Engine Specifications** (the model-year/Chromium table),
  General Specifications (HLS/DASH support, GCC toolchain change), TV Extension archive
- **Roku Developer** — certification testing docs, SceneGraph course, the Roku developer
  blog's Certification category (Spring 2026 update), the `rokudev` GitHub org
- **Amazon Developer** — "Announcing Vega OS" / Get started with Vega Developer Tools;
  **Software Mansion**'s account of building React Native for Vega; **AFTVnews**,
  **Ars Technica**-sourced reporting, **PCWorld**, and **Dolby OptiView** on the transition
- **Parks Associates** (April 2026 Streaming Video Tracker press release, via PRNewswire
  and TV Tech) — US platform shares; **Mordor Intelligence** on activated screens, the
  Fox–Roku agreement, webOS 26, and the Cyber Trust Mark / Kentucky HB 692 regulatory notes
- **IAB Tech Lab** — CTV Programmatic Guide (Universal Ad ID, OM SDK); **Equativ** —
  2026 CTV ad formats and specs, including loudness targets
- **Nielsen** figures via **M+C Saatchi Performance**; **ScreenCloud** and **Play Signage**
  on real-world Chromium version limits; **Float Left**, **Fora Soft**, **Lightcast**,
  and **Accedo** on platform development practice

**Confidence statement.** **High confidence** in §2–§8 → `smart-tv-platforms-and-10-foot-ui`, `smart-tv-monetization-certification-and-operations`, §10–§12 → `smart-tv-monetization-certification-and-operations`, §15, and §19 — these rest
on vendor documentation and consistently-reported practitioner experience. **High
confidence** in the Samsung engine matrix (§1.3 → `smart-tv-platforms-and-10-foot-ui`, §17), which comes directly from Samsung's
own specification page, and in the Roku certification requirements, which come from Roku's
own blog. **Moderate confidence** in §1.1 → `smart-tv-platforms-and-10-foot-ui`'s market-share figures: the sources genuinely
disagree because they measure different things (usage vs. activated screens vs. global
shipments), the numbers come from commercial research firms with differing methodologies,
and I have deliberately presented three framings rather than one number. **Moderate
confidence** in §9 → `smart-tv-monetization-certification-and-operations`'s advertising specifications — these come from ad-tech vendors and the
IAB, are directionally consistent across sources, but vary by publisher in practice, and
the guidance throughout is to confirm specs with the specific publisher or platform rather
than treating any single figure as universal. The Fox–Roku acquisition (§1.2 → `smart-tv-platforms-and-10-foot-ui`, §17) was
**announced**, and announced deals do not always close.
