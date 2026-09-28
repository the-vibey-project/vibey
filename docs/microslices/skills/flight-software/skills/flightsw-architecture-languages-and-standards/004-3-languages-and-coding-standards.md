---
id: skill-3-languages-and-coding-standards-cfe8781196
purpose: 3 languages and coding standards
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-architecture-languages-and-standards/SKILL.md
requires: ["skill-2-architecture-edea7adb23"]
links: []
---

## §3. Languages and Coding Standards

### 3.1 The language landscape

**[DURABLE] C dominates, and the reason is heritage plus tooling, not affection.**
C shipped on **Voyager, the Shuttle GPCs (alongside HAL/S), essentially every JPL deep
space mission of the last three decades, the ISS command and data handling system, and the
overwhelming majority of cubesats flying in 2026.** ⚠️ **cFS is written in C, and that one
fact explains most of C's persistence** — when a new team designs a C&DH stack, the default
isn't "which language," it's "which framework," and the answer pulls C along with it.

| Language | Position |
|---|---|
| **C** | ⚠️ **The substrate. MISRA-constrained, qualified compilers, universal heritage** |
| **C++** | F Prime; ⚠️ **restricted subsets — no exceptions, no RTTI, no dynamic allocation after init** |
| **Ada / SPARK** | ⚠️ **Ariane, and much of ESA. Strong typing, contracts; SPARK gives provable absence of runtime errors** |
| **Rust** | §3.2 |
| **Python** | ⚠️ **Ground segment, test, and analysis — not flight-critical paths** |
| **MATLAB/Simulink** | ⚠️ **GNC algorithm development with autocoding to C** (§12 → `flightsw-gnc-verification-ground-and-autonomy`) |

### 3.2 ⚠️ Rust's actual status

**[CONTESTED, and worth stating carefully because both the hype and the dismissal are
wrong.]**

**The case is real**: C makes it trivial to introduce memory-safety issues producing
undefined behaviour or security vulnerabilities, and **Rust substantially eliminates that
class.** For a domain where a single memory bug is unrecoverable, that matters more than
almost anywhere else.

**⚠️ The obstacles are also real**: **industry adoption in safety-critical environments is
still lacking**, driven by Rust's relatively short lifespan — which translates concretely
into **immature qualified toolchains, thin certification precedent, and no heritage.**
The published research direction is **partial rewrites of C-based systems rather than
wholesale replacement**, which is the pragmatic path.

**Where it stands in 2026**: **programmes adopting Rust are training their teams on the
job**, and one 2026 assessment calls it **the highest-leverage new language to learn for
space and adjacent safety-critical work.** ⚠️ **Take that as a career signal, not as
evidence that Rust is the default. It isn't, and won't be for years.**

### 3.3 Coding standards

**[DURABLE] These are not style guides. They exist because each rule maps to a class of
in-flight failure.**

**⚠️ NASA/JPL's "Power of 10" (Holzmann)** — the most quotable set:
1. **Restrict to simple control flow** — no goto, setjmp/longjmp, recursion.
   ⚠️ **Recursion makes stack bounds unprovable.**
2. **All loops must have a fixed upper bound**, statically provable.
   ⚠️ **This makes runaway loops impossible by construction.**
3. **No dynamic memory allocation after initialization.**
   ⚠️ **Kills fragmentation, exhaustion, and use-after-free in one rule.**
4. **No function longer than ~60 lines** — one printed page.
5. **≥2 assertions per function**, checking anomalous conditions.
6. **Declare data objects at the smallest possible scope.**
7. **Check every non-void return value; validate every parameter.**
8. **Limit the preprocessor** to includes and simple conditional compilation.
9. **Restrict pointer use** to one level of dereferencing; no function pointers.
10. **⚠️ Compile with all warnings enabled, zero warnings, and analyse daily with
    multiple static analysers.**

**MISRA C** (2012, amended) — ~150 rules for C in safety-critical systems, with
**mandatory / required / advisory** categories and a **formal deviation process**.
⚠️ **Deviations are permitted but must be documented and justified — that discipline is
the actual value, more than any individual rule.**

**JPL Institutional Coding Standard for C** — Power of 10 plus JPL specifics, organized by
**risk level.**

**Process standards**: **NPR 7150.2** (NASA software engineering requirements, with the
Class A–E classification), **DO-178C** (airborne, ⚠️ **DAL A–E; with DO-333 for formal
methods and DO-331 for model-based development**), **ECSS-Q-ST-80C** and **ECSS-E-ST-40C**
(⚠️ **the European equivalents, criticality A–D — and if you work with ESA these are the
ones that bind**).

**⚠️ MC/DC coverage** (modified condition/decision coverage) is required at DO-178C DAL A —
**every condition in every decision must be shown to independently affect the outcome.**
It is expensive, and it is why avionics testing costs what it does.
