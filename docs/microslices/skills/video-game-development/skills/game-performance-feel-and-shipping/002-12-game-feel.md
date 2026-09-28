---
id: skill-12-game-feel-988ec6f0e7
purpose: 12 game feel
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-performance-feel-and-shipping/SKILL.md
requires: ["skill-11-performance-bc6ed17f80"]
links: ["skill-13-build-test-and-ship-f2064e5dfd"]
---

## §12. Game Feel

**[DURABLE] "Game feel" is not mysterious — it's a set of specific, implementable
techniques**, and it is very often the difference between a mechanically-identical game
that's fun and one that isn't. Steve Swink's *Game Feel* and Jan Willem Nijman's
"The Art of Screenshake" (§18 → `game-development-reference`) are the canonical treatments.

**Input**: minimize latency (§12.1); **input buffering** (accept a jump pressed a few
frames early); **coyote time** (allow a jump a few frames *after* leaving the ledge);
forgiving hitboxes for the player and generous ones for the player's attacks.

**Response**: hit-stop / freeze frames on impact; screen shake (⚠️ **and an option to
disable it** — §16.7 → `game-development-reference`); knockback; particles; flash; chromatic aberration on hits; and
**animation that anticipates and follows through**.

**Curves**: nothing linear. Acceleration and deceleration curves on movement, easing on
UI, squash-and-stretch. **Tuning these is where a mechanic becomes a feel.**

**Audio** as feedback (§7 → `game-rendering-physics-animation-and-audio`) — the single cheapest source of impact.

### 12.1 Latency

```
input device → OS → engine input poll → simulation → render → present → display
```
Total motion-to-photon of **~50–100 ms is common and mostly invisible**; below ~30 ms feels
crisp; above ~150 ms feels broken. Contributors you control: input polling frequency,
how many frames the render pipeline is buffered ahead, VSync mode, and the display's own
latency. **Competitive games optimize this obsessively; it matters more than framerate
past a point.**

---
