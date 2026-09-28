---
id: skill-9-networking-0486640ecc
purpose: 9 networking
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-ai-networking-and-tools/SKILL.md
requires: ["skill-8-gameplay-ai-3d38f8b1fe"]
links: ["skill-10-tools-and-pipeline-1d1fd9c6ac"]
---

## §9. Networking

**[DURABLE] Multiplayer is not a feature you add. It is an architectural decision made on
day one**, and retrofitting it onto a single-player codebase is one of the most reliable
ways to destroy a schedule.

### 9.1 The models

| Model | How | Trade-off |
|---|---|---|
| **Lockstep / deterministic** | Send only inputs; every peer simulates identically | Tiny bandwidth, scales to thousands of units (RTS). **Requires perfect determinism (§2.2 → `game-engines-loop-and-architecture`)**; one desync ruins the match; latency = worst player |
| **Client-server, authoritative** | Server simulates; clients send input and render state | **The standard for action games.** Cheat-resistant. Costs server infrastructure |
| **Peer-to-peer** | Direct connections | No server cost; NAT traversal pain, and trivially cheatable |
| **Rollback** | Predict remote inputs, roll back and re-simulate on mismatch | **The fighting-game standard (GGPO).** Superb feel; demands determinism and cheap re-simulation |

### 9.2 Client-server, done properly

The canonical stack — from the Quake/Source lineage and still correct:
1. **Client-side prediction** — apply your own input immediately, don't wait for the
   server round trip.
2. **Server reconciliation** — server sends authoritative state with the last-processed
   input sequence number; client rewinds and replays unacknowledged inputs.
3. **Entity interpolation** — render other players slightly in the past (~100 ms) to
   smooth their motion.
4. **Lag compensation** — the server rewinds other players to where the shooter *saw* them
   when validating a hit.

> **⚠️ GOTCHA — lag compensation is a design decision, not a technical one.** It makes
> shooting feel right for the shooter and produces the "I got shot behind cover"
> experience for the target. **You are choosing whose experience to privilege**, and every
> shooter makes that call explicitly. There is no setting that satisfies both.

**Also**: **snapshot delta compression** and **interest management / relevancy** (don't
send what the client can't see) are what make bandwidth tractable; **UDP with your own
reliability layer** for game traffic (TCP head-of-line blocking is fatal), with TCP or
HTTPS for lobby, matchmaking, and commerce.

**⚠️ Never trust the client.** Validate movement, rate-limit actions, keep the inventory
and economy server-side. Anti-cheat is an arms race with real anti-cheat middleware
(EAC, BattlEye), and kernel-level anti-cheat is itself contested for privacy and stability
reasons.

### 9.3 Rollback specifics

Rollback needs: full deterministic simulation, cheap **save/restore of game state**
(usually a compact struct you can memcpy), simulation fast enough to run **7–10 frames of
re-simulation inside one frame's budget**, and input delay tuning. It's the reason modern
fighting games feel dramatically better online than the delay-based generation did — and
it's essentially impossible to bolt onto a game whose state lives scattered across engine
objects.

---
