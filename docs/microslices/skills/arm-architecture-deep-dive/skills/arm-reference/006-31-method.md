---
id: skill-31-method-4124361a26
purpose: 31 method
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-reference/SKILL.md
requires: ["skill-30-quick-reference-dc70ff65d0"]
links: []
---

## §31. Method

**§1–§25 → `arm-what-arm-is-licensing-families-and-isa-generations`, `arm-aarch64-exception-levels-memory-model-and-mmu`, `arm-vectors-atomics-numerics-and-security-architecture`, `arm-system-architecture-boot-and-virtualization`, `arm-cortex-m-toolchain-porting-and-performance` rests on published architecture** — **the ARM ARM specifies the exception model,
the memory model, translation regimes, the vector extensions and the security features, and
none of it needed verification.** ⚠️ **Where I have described a feature as optional or
version-gated, that is from the architecture's own feature-discovery model (§4 → `arm-what-arm-is-licensing-families-and-isa-generations`), which is
the single most practically important thing to internalize about ARM.**

**Two searches were run in August 2026**, on **Arm's business model** and **its datacentre
position** — ⚠️ **the first because §2 → `arm-what-arm-is-licensing-families-and-isa-generations`'s licensing model, which shaped the architecture
itself, has just changed at its foundation, and the second because ARM server share is
quoted constantly and the numbers in circulation are not measuring the same thing.**

**Confidence.** **High** in §8 → `arm-aarch64-exception-levels-memory-model-and-mmu` and §5 → `arm-aarch64-exception-levels-memory-model-and-mmu`, which are the sections I'd most want read.
⚠️ **The weak memory model is the difference that actually breaks things: x86-TSO hides
missing synchronization, ARM exposes it, and the resulting bugs are intermittent and
load-dependent — which is why §23 → `arm-cortex-m-toolchain-porting-and-performance` puts it first and says test on real hardware under load.**
⚠️ **§5 → `arm-aarch64-exception-levels-memory-model-and-mmu`'s account of what AArch64 deliberately REMOVED is the most instructive part of the
ISA: dropping universal predication and the PC-as-general-register were both giving up
elegant features because they obstruct out-of-order implementation, and that trade tells
you what a modern ISA is actually optimizing for.**
**⚠️ §21 → `arm-cortex-m-toolchain-porting-and-performance`'s hardware register stacking is the small delightful detail — it is why a Cortex-M
interrupt handler can be an ordinary C function.**

**High** on §26.1's core facts, which come from Arm's own newsroom: ⚠️ **the March 2026
announcement of Arm-designed silicon, the AGI CPU's core count and process node, and Meta as
lead partner.** ⚠️ **The performance claims are Arm's own and I have attributed them rather
than stating them.** **⚠️ The point I would most want carried is the structural one: core
licensing carried no supply-chain responsibility, and shipping silicon does — this changes
what kind of company Arm is, and it puts them in partial competition with licensees.**

**Moderate** on §26.2's share figures, and the gotcha IS the finding. ⚠️ **IDC reporting
puts Arm above 45% of server REVENUE while another analysis puts it at 15–23% of server CPU
SHIPMENTS, and both are defensible because AI servers inflate revenue share — the same
reporting has accelerated servers at around 70% of all server revenue.**
⚠️ **A third figure keeps it honest: an analyst noting Arm's roughly $2bn in AGI CPU sales
is under 5% of the overall market.** **⚠️ The billion-cores milestone and hyperscaler
adoption are solid; the percentage claims are exactly where motivated numbers live, and
several of my sources are market-research firms selling forecasts.**
