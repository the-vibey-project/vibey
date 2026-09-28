---
id: skill-6-performance-and-memory-5c7ff64553
purpose: 6 performance and memory
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-playback-drm-and-performance/SKILL.md
requires: ["skill-5-drm-1fdcb204a4"]
links: ["skill-7-lifecycle-deep-linking-and-discovery-fe1da2b1ef"]
---

## §6. Performance and Memory

### 6.1 The hardware reality

**[DURABLE] Budget as if you're targeting a low-end phone from a decade ago.** Roku
devices run ARM Cortex-A53/A55/A35-class cores (some older models MIPS); TV SoCs across
all vendors are cost-optimized, thermally constrained, and shipped with the minimum RAM
that passes QA. A $30 streaming stick and a $3,000 OLED may run the same app on very
different silicon — **and the cheap device is the one most of your users have.**

**The budgets that actually matter:**
| Resource | Guidance |
|---|---|
| **App memory** | Often a few hundred MB total. Exceeding it means the OS kills you |
| **Startup to first interactive frame** | Target < 3 s cold |
| **Time to first video frame** | Target < 2 s (§4.3) |
| **Frame time** | 16.6 ms — and you will blow it far more easily than on mobile |
| **Image decode** | The dominant memory consumer in a poster-grid UI |

### 6.2 The techniques

1. **Virtualize every long list.** Never instantiate 500 tiles. Recycle views/nodes and
   render a window plus a small buffer. **This is the single highest-impact optimization
   in TV development**, because the rail-grid UI is inherently a huge-list problem.
2. **Size images server-side to the exact display size.** Downloading a 1920px poster to
   render at 300px wastes bandwidth *and* decode memory *and* CPU. Use a thumbnailing CDN
   and request precise dimensions.
3. **Aggressively evict off-screen image bitmaps.** Memory pressure on TV is real.
4. **Preload the *next* screen's data, not everything.**
5. **Minimize DOM work on web platforms** — old Chromium, weak CPU. Batch mutations,
   avoid layout thrashing, prefer `transform`/`opacity` animations, and keep the node
   count low.
6. **Never block on network during navigation.** Show the shell instantly, fill it in.
7. **Watch your JS bundle size** — parse and compile cost is significant on these CPUs.
8. **Profile on the worst device you support, not the best.**

**[PLATFORM] Roku requires memory monitoring for certification.** Apps must use the
**`roAppMemoryMonitor`** APIs to observe and respond to memory events in order to pass
certification testing — that is, the platform mandates that you handle memory pressure
rather than merely hoping. The **BrightScript Profiler** and **Roku Resource Monitor**
are the tools; Roku also ships **`rokuos-perfetto-utils`** for tracing.

---
