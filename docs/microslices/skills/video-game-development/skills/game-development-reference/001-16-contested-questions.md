---
id: skill-16-contested-questions-a0e8d0119e
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-development-reference/SKILL.md
requires: []
links: ["skill-17-currency-snapshot-verified-august-2026-d746dd890f"]
---

## §16. Contested Questions

**16.1 ECS vs. object-oriented.** §3.2 → `game-engines-loop-and-architecture`. The strongest version of each case, and the hybrid
synthesis most shipped games actually use.

**16.2 Unity vs. Unreal vs. Godot.** §1 → `game-engines-loop-and-architecture`. Genuinely depends on genre, platform, team
experience, and licence-risk tolerance. The 2026 rough consensus: **Unreal for
high-fidelity 3D, Unity for mobile and cross-platform breadth, Godot for 2D and
licence-sensitive teams** — but every one of those has strong counterexamples.

**16.3 Are the explicit graphics APIs still right?** §4.2 → `game-rendering-physics-animation-and-audio` — Aaltonen's argument that DX12
and Vulkan are ten-year-old designs targeting thirteen-year-old hardware, and that a new
abstraction layer has quietly grown back underneath.

**16.4 Root motion vs. in-place animation.** §6 → `game-rendering-physics-animation-and-audio`.

**16.5 Custom engine vs. commercial.** *For custom*: total control, no royalties, no
licence risk, and a genuine competitive advantage if your game needs something engines
don't do. *Against*: years of work on solved problems, no asset ecosystem, harder hiring,
and you now maintain a renderer forever. ~14% of developers report using an in-house
engine, and most of those are at studios with the scale to justify it.

**16.6 Generative AI in game development.** §15.2 → `game-performance-feel-and-shipping`. The industry is *split against itself* —
36% use it, 52% think it's harming the industry. The disagreement is genuine and runs along
discipline lines, and the legal position on generated-asset ownership is unsettled.

**16.7 How much accessibility, and who pays for it.** There is no serious argument against
accessibility; the disagreement is about cost and priority on small teams. **[DURABLE] The
high-value, low-cost items are well-established**: remappable controls, subtitle size and
background options, colourblind-safe palettes (never colour alone as a signal), **a screen
shake toggle**, difficulty options, hold-vs-toggle for held inputs, and reduced-motion
settings. The **Game Accessibility Guidelines** and the **Xbox Accessibility Guidelines**
are the practical references, and both are organized by implementation cost. Late
retrofitting is what's actually expensive.

---
