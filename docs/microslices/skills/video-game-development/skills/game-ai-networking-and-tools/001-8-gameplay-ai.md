---
id: skill-8-gameplay-ai-3d38f8b1fe
purpose: 8 gameplay ai
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-ai-networking-and-tools/SKILL.md
requires: []
links: ["skill-9-networking-0486640ecc"]
---

## §8. Gameplay AI

**[DURABLE] Game AI is not machine learning; it is the craft of producing believable,
readable, *beatable* behaviour.** The goal is a good opponent from the player's
perspective, not an optimal agent. **An AI that is too good is a design failure.**

### 8.1 The decision-making toolbox

| Technique | Use |
|---|---|
| **Finite state machine** | Simple agents. Readable, debuggable, and it explodes combinatorially past ~10 states |
| **Hierarchical FSM** | Nested states — a real improvement for character control |
| **Behaviour tree** | **The industry default.** Composable, designer-authorable, good tooling in every engine |
| **Utility AI** | Score each option, pick the best. Excellent for sims and many-option agents (*The Sims*) |
| **GOAP** (goal-oriented action planning) | Plans a sequence of actions to reach a goal. *F.E.A.R.*'s famous squad AI |
| **HTN planning** | Hierarchical task networks. *Horizon Zero Dawn*, *Transformers* |
| **Steering behaviours** | Seek, flee, arrive, separate, flock (Reynolds' boids) — the movement layer beneath everything |

### 8.2 Pathfinding

**A\*** on a navmesh (or grid) is still the answer. **Navmesh generation** (Recast is the
open-source standard, and is what most engines use or imitate). Then the practical layer:
**hierarchical pathfinding** for large maps, **string pulling / funnel algorithm** to
smooth the path off the mesh polygon centers, **local avoidance** (RVO/ORCA) so agents
don't collide, **path caching and request budgeting** (⚠️ don't path 500 agents in one
frame — amortize across frames), and **flow fields** when many agents share a destination
(the standard RTS answer).

### 8.3 Making AI *feel* right

**[DURABLE] The techniques that make AI good are mostly about legibility, not
intelligence:** telegraphed attacks with wind-up frames; **deliberately imperfect
accuracy** (and the near-universal "first shot always misses" rule); **reaction delays**
so the player can respond; **barks and animation that externalize internal state** so the
player can read what the AI is doing; **attack tokens** so only one or two enemies engage
at a time regardless of how many are present; and **cheating in the player's favour**
(hidden last-hit-point buffers, ammo drops when low). *F.E.A.R.*'s AI is remembered as
brilliant largely because the agents **announce their plans out loud**.

---
