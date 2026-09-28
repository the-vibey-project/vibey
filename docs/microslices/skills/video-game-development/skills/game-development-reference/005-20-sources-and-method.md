---
id: skill-20-sources-and-method-4ba051070b
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-development-reference/SKILL.md
requires: ["skill-19-quick-reference-f4b6eaff7e"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §2 → `game-engines-loop-and-architecture` (game loop),
§3 → `game-engines-loop-and-architecture` (architecture), §5–§9 → `game-rendering-physics-animation-and-audio`, `game-ai-networking-and-tools` fundamentals, §10 → `game-ai-networking-and-tools` (tooling), §11 → `game-performance-feel-and-shipping` (performance principles),
§12 → `game-performance-feel-and-shipping` (game feel), §13.2 → `game-performance-feel-and-shipping`–13.3, §14 → `game-performance-feel-and-shipping` (production) — is synthesized from the standard
references in §18, GDC practitioner talks, and consistently-reported industry practice.
Every **time-sensitive** claim (engine versions and pricing, market share, industry
conditions, AI adoption and disclosure rules, graphics API status) was verified against a
primary or near-primary source in **August 2026** and is flagged in §17 with a decay-risk
rating. Where practitioners genuinely disagree, §16 presents both cases.

**Search log** (August 2026): Unreal/Unity/Godot versions, licensing, and 2026 market
share · Steam AI disclosure policy and GDC State of the Game Industry 2026 · Vulkan 1.4,
DirectX 12, work graphs and mesh shaders.

**Primary and near-primary sources consulted (selected):**
- **GDC / GDC Festival of Gaming** — *2026 State of the Game Industry* report and its
  official summary (layoffs, AI adoption and sentiment, engine mindshare, Steam Deck),
  via gdconf.com, BusinessWire, and secondary coverage
- **Video Game Insights**, *The Big Game Engines Report* — Steam revenue and release share
- **Godot Engine** growth statistics and release notes (4.6, 4.7); SteamDB-derived counts
- **Khronos** Vulkan specification and **Vulkan Roadmap 2026** requirements;
  **AMD GPUOpen** on work graphs and `VK_AMDX_shader_enqueue` mesh nodes
- **Sebastian Aaltonen**, "No Graphics API" — the explicit-API critique in §4.2 → `game-rendering-physics-animation-and-audio`
- Legal and licensing analysis of the Unity TOS timeline (the 2019 SpatialOS change, the
  April 2023 removal of the protective clause, the September 2023 runtime fee, the 2024
  cancellation), plus 2026 pricing comparisons from multiple independent write-ups
- Reporting on **Steam's January 2026 AI-disclosure clarification** (GamesIndustry.biz and
  GameMeca, as cited by secondary coverage) and on disclosure volumes

**Confidence statement.** **High confidence** in §2–§14 → `game-engines-loop-and-architecture`, `game-performance-feel-and-shipping`'s durable technical and production
content — this rests on the standard references, decades of consistent practitioner
reporting, and material that has been stable across console generations. **High
confidence** in the GDC 2026 survey figures (§15.1 → `game-performance-feel-and-shipping`–15.2, §17), which come from a named,
methodologically-described annual survey of 2,300+ professionals and were corroborated
across multiple independent reports of the same release. **Moderate confidence** in the
engine market-share numbers: they come from commercial research (Video Game Insights) and
platform-derived counts, they measure different things (Steam revenue vs. Steam releases
vs. self-reported mindshare vs. mobile grossing), and the mobile figures in particular
circulate widely without a consistently-attributable primary source — I have presented the
framing rather than a single number. **Moderate confidence** in the engine version and
pricing details in §17: several 2026 sources disagree on which Unity and Unreal versions
are current at any given moment (one cited UE 5.6 as current, others 5.7) and on exact
Unity price points, which is a normal consequence of rapid release cadences and regional
pricing — **verify current pricing on the vendor's own page before making a financial
decision.** The Unreal Engine 6 timeline is an announcement, not a shipped product.
