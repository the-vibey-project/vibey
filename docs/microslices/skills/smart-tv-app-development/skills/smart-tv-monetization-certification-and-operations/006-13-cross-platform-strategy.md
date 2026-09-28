---
id: skill-13-cross-platform-strategy-a802491a86
purpose: 13 cross platform strategy
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-monetization-certification-and-operations/SKILL.md
requires: ["skill-12-analytics-and-qoe-e7e6e98f0a"]
links: ["skill-14-accessibility-privacy-and-regulation-220d7c8731"]
---

## §13. Cross-Platform Strategy

### 13.1 The decision

**[CONTESTED — and the honest answer depends on your platform mix and budget.]**

| Approach | What it means | When it's right |
|---|---|---|
| **Native per platform** | BrightScript + Kotlin + Swift + web ×N | Maximum quality and platform integration; highest cost. What the large streamers do |
| **Web app everywhere it's possible** | One HTML/JS codebase for Tizen, webOS, VIDAA, and the long tail; native for Roku/tvOS/Android | **The most common pragmatic architecture.** Covers a lot with one codebase |
| **React Native** | Now genuinely relevant: **RN is a first-class citizen on Vega**, with the native RN core and common dependencies (Reanimated, Gesture Handler, AsyncStorage) precompiled into the system. RN also targets Android TV and tvOS | If Vega + Android TV + tvOS is your mix |
| **Shared core, native shells** | Business logic, API client, and player abstraction shared; UI per platform | The best cost/quality balance for most teams |
| **Turnkey OTT platform** | A vendor generates and maintains apps across platforms from your catalogue | When your differentiation is content, not app UX |

**[DURABLE] Whatever you choose, the thing to share is not the UI — it's everything
underneath it.** The API client, entitlement logic, analytics schema, player abstraction,
and content model should be common. The UI layer *should* differ per platform, because
the focus model, layout idiom, and platform conventions genuinely differ.

**⚠️ Roku is the fragmentation tax nobody can avoid.** BrightScript and SceneGraph share
nothing with anything else — no browser engine, no HTML, no CSS, no JavaScript. If Roku is
in your mix (and in North America it is), you are staffing a separate discipline. Plan for
it explicitly rather than discovering it.

---
