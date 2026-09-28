---
id: skill-1-engines-2a88518910
purpose: 1 engines
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-engines-loop-and-architecture/SKILL.md
requires: ["skill-0-routing-07c121212d"]
links: ["skill-2-the-game-loop-52f0d8cfc2"]
---

## §1. Engines

### 1.1 The decision

**[DURABLE] Use an existing engine.** Writing your own is justified when you have an
unusual technical requirement no engine serves, a large experienced team, or the engine
*is* the product. "I'll learn more" is a fine reason for a hobby project and a poor reason
for a commercial one.

**[VERSIONED — mid-2026 landscape.]**

| Engine | Language | Cost model | Best at |
|---|---|---|---|
| **Unreal Engine 5.x** | C++ / Blueprints | Free to **$1M lifetime gross**, then **5%** royalty | High-fidelity 3D, AAA, photoreal. **Nanite** (virtualized geometry) and **Lumen** (real-time GI) eliminate traditional LOD and light-baking work |
| **Unity 6.x** | C# | Seat-based subscription; **Personal free under $200K/yr revenue**, Pro above | Mobile (~**70% of top-grossing mobile titles**), cross-platform breadth, 2D, XR |
| **Godot 4.x** | GDScript / C# / C++ | **MIT — free forever, no royalty, no revenue threshold** | 2D (best-in-class workflow), small teams, licence-risk-averse studios |
| **GameMaker** | GML | Tiered | 2D, beginners, fast prototyping |
| **Bevy / raylib / SDL / MonoGame / LÖVE** | Rust / C / C# / Lua | Open source | Custom engines, jams, programmers who want control |
| **In-house** | — | Your salaries | ~14% of surveyed developers. Justified at scale or for a unique requirement |

### 1.2 Licensing is an engineering risk, not just a finance question

**[DURABLE, learned the hard way] Your engine licence can change under you mid-project,
and that is a real technical risk requiring a real mitigation.** The canonical case:

Unity's 2019 Terms-of-Service change (which blocked SpatialOS) prompted enough backlash
that Unity added a protective commitment — if terms changed adversely, developers could
elect to continue under the prior terms. **That clause was quietly removed on 3 April
2023**, five months before the runtime fee was announced. In September 2023 Unity
announced a **per-install runtime fee of up to $0.20**; the backlash was severe, the CEO
departed, and **new CEO Matt Bromberg cancelled it entirely in September 2024**, reverting
to seat-based subscriptions.

The consequences are still visible in 2026: measurable migration to Godot and Unreal, and
a persistent trust deficit that shows up in *new-project* engine selection more than in
existing projects.

**What to actually do about it:** read the current licence rather than the summary you
remember; **archive the version of the terms you agreed to**; keep gameplay logic
separated from engine-specific APIs where cheap (§3.4); and treat "could we port this if
we had to?" as a question with a real answer. Godot's structural pitch is precisely this —
**a nonprofit foundation and an MIT licence, so there is no pricing model that can change**.

### 1.3 Market reality

**[VERSIONED]** The numbers that matter for hiring, asset availability, and community
support as of 2026:
- **Unreal out-earned Unity on Steam for the first time since 2018** — 31% of 2024 Steam
  revenue vs. Unity's 26% (Video Game Insights) — while **Unity still ships the most games**
  (51% of 2024 Steam releases).
- **Developer mindshare has flipped**: **42% named Unreal their primary engine vs. 30% for
  Unity** (GDC State of the Game Industry 2026).
- **Godot is the fastest-growing engine by every open metric**: Steam releases grew from
  618 (2023–24) to **2,864 (2025–26), roughly 4.6×**; ~114,700 GitHub stars as of mid-2026.
- **Unity remains dominant on mobile** — roughly half of all mobile games, ~70% of the
  top-grossing.

**[DURABLE] Read those as "where the ecosystem is," not "which is better."** Asset store
depth, tutorial coverage, hireable experience, and middleware support follow market share,
and those are often worth more than a feature comparison.

---
