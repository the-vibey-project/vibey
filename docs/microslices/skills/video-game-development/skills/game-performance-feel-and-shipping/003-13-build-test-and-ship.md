---
id: skill-13-build-test-and-ship-f2064e5dfd
purpose: 13 build test and ship
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-performance-feel-and-shipping/SKILL.md
requires: ["skill-12-game-feel-988ec6f0e7"]
links: ["skill-14-production-and-scope-6b5e585b92"]
---

## §13. Build, Test, and Ship

### 13.1 Testing
Unit tests for pure logic (this is why §3.4 → `game-engines-loop-and-architecture` matters); **automated smoke tests** that boot
every level and walk around; **replay-based regression tests** (record inputs, replay,
compare state — requires determinism, §2.2 → `game-engines-loop-and-architecture`); performance regression tests in CI with
alerting on frame-time budgets; and **soak tests** (run for 24 hours; find the leak and
the overflow).

### 13.2 Playtesting
**[DURABLE] This is the highest-value activity in game development and the one teams
defer.** Rules that hold universally: **watch, don't explain** (if you have to explain it,
it's broken); playtest with people who have never seen it; **watch where they get stuck,
not what they say**; test early with ugly placeholder art; and separate "this is confusing"
feedback (always act on it) from "I would prefer" feedback (usually don't).

### 13.3 Certification
**[DURABLE] Console certification (Sony TRC, Microsoft XR, Nintendo Lotcheck) is a real
gate that fails real games, and it takes weeks.** What it checks: correct handling of
controller disconnect, suspend/resume, user sign-in and sign-out, storage full, network
loss; correct terminology (**each platform mandates its own button and system
nomenclature**); save-data and corruption handling; achievement/trophy correctness;
loading-time and loudness limits; age ratings; and no crashes in the tested paths.

**⚠️ Budget weeks for cert and expect at least one rejection.** Read the requirements
**at the start of the project** — several are architectural (suspend/resume and save
integrity in particular) and cannot be retrofitted late.

Also plan for: age ratings (ESRB, PEGI, USK, CERO — and loot boxes are a rating and
legality issue in several jurisdictions), localization (**including text expansion —
German runs ~30% longer than English**, and RTL layout for Arabic and Hebrew), and
platform store requirements.

---
