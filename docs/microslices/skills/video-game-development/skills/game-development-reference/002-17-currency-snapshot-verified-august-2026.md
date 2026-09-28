---
id: skill-17-currency-snapshot-verified-august-2026-d746dd890f
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-development-reference/SKILL.md
requires: ["skill-16-contested-questions-a0e8d0119e"]
links: ["skill-18-the-canon-9dc5577ce1"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Unreal Engine** | **5.7** current; free to **$1M lifetime gross**, then **5%**. 5.7 added tooling aimed at small teams. **Unreal Engine 6 announced at State of Unreal 2026**, early access window reported as **2027** | Medium |
| **Unity** | **6.x** line (6.3 LTS with day-one Switch 2 support; 6.4 shipped March 2026). Seat-based: **Personal free under $200K/yr**, Pro ~$2,040–2,310/yr, Enterprise above $25M. ⚠️ **Runtime fee cancelled September 2024**; prices have since risen again. **Unity 7 beta expected December 2026** | Medium |
| **Godot** | **4.7** (June 2026 — HDR, area lights, drawable textures). 4.6 (26 Jan 2026) **made Jolt the default physics engine** and added Android device mirroring, Google Play Billing/Games Services, and Apple StoreKit 2. **MIT, no royalties, no revenue threshold, nonprofit foundation** | Low |
| **Engine market share** | **Unreal out-earned Unity on Steam for the first time since 2018** (31% vs 26% of 2024 revenue, Video Game Insights); **Unity still ships the most games** (51% of 2024 Steam releases); **Unreal leads mindshare 42% vs 30%** (GDC 2026); **Godot Steam releases 618 → 2,864 in two years (~4.6×)**; Unity ~70% of top-grossing mobile | Medium |
| **Industry conditions** | ⚠️ **28% of GDC 2026 respondents laid off in two years (33% in the US)**; **two-thirds of AAA respondents' companies had layoffs**; **48% of laid-off respondents still unemployed**; **74% of students concerned about prospects**. Ongoing memory-supply constraints affecting hardware | **High** |
| **Generative AI** | **36% use AI tools**; **52% believe it's harming the industry (up from 30%)** vs **7% positive**; opposition highest among artists (64%), designers (63%), programmers (59%). **Steam requires AI disclosure; Apple and Google Play require AI labels.** ⚠️ **Steam clarified in January 2026 that internal workflow tools are exempt** — disclosure covers shipped content. Thousands of Steam titles now disclose, concentrated among small teams | **High** |
| **Vulkan** | Current spec **1.4**. **Vulkan Roadmap 2026 requires Vulkan 1.4**, targeting mid-to-high-end hardware shipping in 2026 or shortly after, adding baseline requirements including `hostImageCopy` and robustness features | Medium |
| **Direct3D 12** | DX12 Ultimate feature set: DXR, VRS, mesh shaders, sampler feedback. **DirectStorage** for fast asset loading. **Work graphs** shipping | Medium |
| **Work graphs** | In D3D12; in Vulkan via **`VK_AMDX_shader_enqueue`** (experimental) with **mesh nodes** and HLSL syntax support via DXC→SPIR-V. ⚠️ **Not yet standardized across hardware vendors** | **High** |
| **Steam Deck** | **Fourth-most-developed-for platform (28% of GDC 2026 respondents)** — newly added to the survey and immediately significant | Medium |

**Goes stale fastest:** industry employment conditions; AI adoption, sentiment, and
disclosure rules; engine version numbers and pricing; work-graph standardization.
**Essentially never stale:** §2 → `game-engines-loop-and-architecture` (game loop), §3.1 → `game-engines-loop-and-architecture` (composition), §5.1 → `game-rendering-physics-animation-and-audio` (kinematic
controllers), §8.3 → `game-ai-networking-and-tools` (AI legibility), §9.2 → `game-ai-networking-and-tools` (netcode fundamentals), §11 → `game-performance-feel-and-shipping` (performance
principles), §12 → `game-performance-feel-and-shipping` (game feel), §14 → `game-performance-feel-and-shipping` (scope).

---
