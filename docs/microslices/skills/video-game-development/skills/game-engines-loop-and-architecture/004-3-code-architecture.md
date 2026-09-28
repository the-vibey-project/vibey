---
id: skill-3-code-architecture-cb4275d87e
purpose: 3 code architecture
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-engines-loop-and-architecture/SKILL.md
requires: ["skill-2-the-game-loop-52f0d8cfc2"]
links: []
---

## §3. Code Architecture

### 3.1 The progression

```
God object            → everything in one Player class. Fine for a jam
Inheritance hierarchy → GameObject → Character → Enemy → FlyingEnemy...
                        ⚠️ collapses at the "flying enemy that swims" problem
Component composition → an entity HAS a Transform, a Renderer, a Health...
                        Unity's GameObject/MonoBehaviour model
ECS (data-oriented)   → entities are IDs, components are plain data in packed arrays,
                        systems are functions over component queries
```

**[DURABLE] Composition over inheritance is the one architectural lesson the industry has
fully internalized.** Deep inheritance hierarchies for game entities fail predictably and
always for the same reason: real games need arbitrary combinations of behaviours that the
tree can't express.

### 3.2 ECS

**Why it exists**: cache locality (§11.3 → `game-performance-feel-and-shipping`), trivially parallel systems, and runtime
composition.
```
Entity 42  = just an integer ID
Components: Position[42], Velocity[42], Health[42]      ← packed contiguous arrays
System:     for each entity with (Position, Velocity): pos += vel * dt
```

**[CONTESTED] How much ECS you need.** *For*: measurable performance on entity-heavy
simulations, clean parallelism, and no inheritance tangles. *Against*: real overhead in
indirection and mental model, worse for one-off entities and complex singular systems,
and cross-component logic gets awkward. **The honest synthesis: use ECS where you have
many similar things (particles, units, bullets, crowds); use plain objects for the few
special things (the player, the camera, the UI).** Most shipped games are hybrids, and
purity here is a much smaller win than its advocates suggest.

Unity's DOTS is the mainstream version, now production-ready after a long and
often-criticized maturation; Bevy is ECS-native; EnTT and flecs are the C++ standards.

### 3.3 Patterns that earn their keep

**Game Programming Patterns** (Robert Nystrom, free online — §18 → `game-development-reference`) is the canonical
reference. The ones you'll actually use: **Update Method**, **Component**,
**Object Pool** (⚠️ **essential** — allocating during gameplay causes hitches, §11.4 → `game-performance-feel-and-shipping`),
**State machine** and **hierarchical state machine** (the backbone of character control),
**Observer/event bus** (decouples systems; ⚠️ becomes untraceable spaghetti if
overused), **Service Locator**, **Command** (input remapping, undo, replay, netcode),
**Spatial Partition** (§5.2 → `game-rendering-physics-animation-and-audio`), **Dirty Flag**, and **Data Locality**.

### 3.4 Separating game logic from engine

**[DURABLE] Worth doing to a moderate degree, not religiously.** Keeping your rules,
economy, and state machines in engine-agnostic code makes them unit-testable, portable,
and usable in a headless server. Wrapping every engine call in an abstraction layer is
over-engineering that will cost you more than it saves. **The test: could you run your
combat resolution in a console app with no renderer?** If yes, you've drawn the line in
about the right place.
