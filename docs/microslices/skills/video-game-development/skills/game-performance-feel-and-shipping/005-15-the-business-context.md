---
id: skill-15-the-business-context-12239a706c
purpose: 15 the business context
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-performance-feel-and-shipping/SKILL.md
requires: ["skill-14-production-and-scope-6b5e585b92"]
links: []
---

## §15. The Business Context

### 15.1 The 2026 industry reality

**[VERSIONED — and this is the context anyone entering the field needs.]** From GDC's
**2026 State of the Game Industry** (14th annual, 2,300+ professionals):
- **28% of respondents were laid off in the past two years, rising to 33% in the US**;
  **half** said their employer conducted layoffs in the last 12 months. **Two-thirds of
  AAA respondents** and **one-third of indie respondents** reported layoffs at their
  companies. **Game designers were the most-affected profession at 20% of layoffs**, and
  **48% of those laid off had not yet found a new job.**
- **74% of surveyed students are concerned about their job prospects**, citing lack of
  entry-level roles, competition from experienced laid-off workers, and AI displacement.
- **Unreal passed Unity in primary-engine mindshare** (42% vs. 30%), and the **Steam Deck
  is now the fourth-most-developed-for platform at 28%**.
- Strong unionization support among US respondents.

### 15.2 Generative AI — adoption and sentiment

**[VERSIONED, and the gap between the two numbers is the story.]** GDC 2026 found **36%
of professionals use AI tools in their work** — highest in business roles (58%), lower in
game-studio production (30%) — while **52% believe generative AI is having a negative
impact on the industry, up sharply from 30% the year before**, against just **7%** who see
it as positive. Opposition is fiercest in the most-exposed disciplines: **64% of visual
and technical artists, 63% of designers and narrative professionals, and 59% of
programmers** hold unfavorable views. Most common uses are research and brainstorming
(81%), email and meeting planning (47%), coding (47%), and prototyping (35%).

**[VERSIONED] Disclosure is now a platform requirement.** Steam requires AI disclosure,
and Apple and Google Play require AI labels. Steam's language was **clarified in January
2026 to exempt internal workflow tools** — disclosure applies to AI content in the shipped
game, not to tools used during development. Disclosures have grown enormously (thousands
of Steam titles now carry them), concentrated among **small teams and solo developers**,
while larger studios with established art and audio pipelines mostly file nothing because
their shipped content wasn't AI-generated.

**⚠️ The practical risks are real and separate from the sentiment**: platform disclosure
obligations, **copyright ownership of AI-generated assets is legally unsettled**, and there
is precedent for player backlash forcing rework — **Embark Studios replaced AI-generated
voice acting in *The Finals* with human performances after player response**, despite
having been transparent about it.

### 15.3 Monetization

**Premium** (buy once), **free-to-play + IAP** (dominant on mobile), **battle pass**,
**subscription**, **ad-supported**, **DLC and expansions**, **cosmetics-only**.
**[DURABLE] Your monetization model is a design constraint that reaches into every
system** — F2P economy design, retention loops, and session pacing are gameplay
architecture, not a business-team concern bolted on at the end.

**⚠️ Loot boxes are regulated or banned in several jurisdictions** (Belgium and the
Netherlands most notably), are a factor in age ratings, and attract ongoing legislative
attention. Treat the legal question as live.

### 15.4 Live operations
If you ship a live game you have signed up for: content cadence, telemetry and analytics,
A/B testing, server operations and on-call, community management, anti-cheat, patch
pipelines and per-platform patch certification, and **backward compatibility of save data
across versions**. **[DURABLE] Live ops is a permanent staffing commitment**, and studios
routinely underestimate it by an order of magnitude.

### 15.5 Anti-patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| Building an engine when you needed a game | Years spent on solved problems | Use an engine (§1.1 → `game-engines-loop-and-architecture`) |
| Choosing an engine on features alone | Licensing, ecosystem, and hireability matter as much | §1.1 → `game-engines-loop-and-architecture`–1.3 |
| Not reading (or archiving) the engine licence | Terms have changed mid-project before | §1.2 → `game-engines-loop-and-architecture` |
| Variable timestep physics | Framerate-dependent behaviour, tunneling, non-determinism | Fixed timestep + accumulator (§2.1 → `game-engines-loop-and-architecture`) |
| No max-frame-time clamp | Spiral of death → hang | Clamp accumulated steps |
| Deep inheritance for game entities | Collapses at the first cross-cutting behaviour | Composition (§3.1 → `game-engines-loop-and-architecture`) |
| Full ECS purity on a small game | Overhead and ceremony for no gain | Hybrid — ECS for the many, objects for the few (§3.2 → `game-engines-loop-and-architecture`) |
| Dynamic rigid bodies for the player character | Floaty, sticky, untunable | Kinematic character controller (§5.1 → `game-rendering-physics-animation-and-audio`) |
| No CCD on fast objects | Bullets pass through walls | CCD or raycast movement (§5.2 → `game-rendering-physics-animation-and-audio`) |
| Allocating during gameplay | GC spikes and hitches = dropped frames | Object pools, arena allocators (§11.4) |
| Pointer-chasing hot data | Cache misses dominate | Data-oriented layout (§11.3) |
| Compiling shaders on first use | The defining PC stutter problem of this generation | Precompile and cache PSOs (§4.3 → `game-rendering-physics-animation-and-audio`) |
| "Just use mesh shaders everywhere" | Tile-based mobile GPUs overshade badly | Keep the vertex path (§4.2 → `game-rendering-physics-animation-and-audio`) |
| Optimizing average framerate | Hitches are what players feel | Optimize 1% and 0.1% lows (§11.1) |
| Profiling only on the dev machine | Your target is the low-spec box | Profile on minimum spec |
| Retrofitting multiplayer | Architectural, not additive | Decide on day one (§9 → `game-ai-networking-and-tools`) |
| Trusting the client | Trivially cheated | Server-authoritative validation (§9.2 → `game-ai-networking-and-tools`) |
| One footstep sample | Instantly reads as amateur | Variation and randomization (§7 → `game-rendering-physics-animation-and-audio`) |
| AI that's too good | A design failure, not a feature | Legibility and deliberate imperfection (§8.3 → `game-ai-networking-and-tools`) |
| Pathing every agent every frame | Frame spikes | Budget and amortize requests (§8.2 → `game-ai-networking-and-tools`) |
| Neglecting tools and iteration time | Silently costs you the experimentation that finds the fun | Invest early (§10 → `game-ai-networking-and-tools`) |
| Git for large binary assets | No locking, poor large-file handling | Perforce, or Git LFS with discipline |
| Reading cert requirements at the end | Several are architectural | Read them at the start (§13.3) |
| Explaining your game during playtests | You won't be there when it ships | Watch silently (§13.2) |
| Building everything before testing the fun | You'll polish something that isn't fun | Prototype the risky thing first (§14) |
| Scope you can't finish | The #1 killer of games | Estimate, then cut half (§14) |
| Marketing at launch | Nobody hears about it | Steam page and wishlists early (§14) |
| Crunch as a plan | Worse work, attrition, documented harm | Schedule that doesn't require it (§14) |
| Undisclosed AI content on a platform that requires disclosure | Store policy violation and player backlash | Disclose; know the exemptions (§15.2) |
| Accessibility as a post-launch patch | Much cheaper designed in | §16.7 → `game-development-reference` |
