---
id: skill-part-1-the-debugging-mindset-and-process-712bb7067b
purpose: part 1 the debugging mindset and process
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-core-principles-37d12de589"]
links: ["skill-part-2-correlation-trace-ids-the-distributed-debugging-primitive-3d8a572a13"]
---

## Part 1 — The Debugging Mindset and Process

### The Scientific Method Applied to Debugging

Debugging is hypothesis-driven science: **observe → hypothesize → predict → test → analyze → repeat.** The cardinal sin is "debugging by changing things and seeing what happens" — mutating code based on guesses rather than evidence. Form a falsifiable hypothesis, predict what you'd observe if it were true, then test it.

### David Agans' Nine Rules of Debugging

From *Debugging: The 9 Indispensable Rules* (2002, ISBN 978-0-8144-7457-0) — technology-agnostic, canonical mindset framework:

1. **Understand the system** — Read the manual; know the fundamentals, roadmap, and tools. "If you don't understand some part of the system, that always seems to be where the problem is."
2. **Make it fail** — Reproduce reliably. Do it again, start at the beginning, *stimulate* the failure (don't simulate it), find the uncontrolled condition behind intermittents, and record everything to find the "signature." Never throw away a debugging tool.
3. **Quit thinking and look** — Get data first. "It is a capital mistake to theorize before one has data" (Sherlock Holmes, quoted by Agans). Build instrumentation in, add instrumentation on, but watch out for Heisenberg effects. Guess only to focus the search.
4. **Divide and conquer** — Binary-search the problem space; narrow the range with successive approximation.
5. **Change one thing at a time** — Isolate variables; use a known-good case for comparison. (Most-violated rule along with #6.)
6. **Keep an audit trail** — Write down what you did, in what order, and what happened. (Most-violated rule along with #5.)
7. **Check the plug** — Question assumptions; the simplest cause (unplugged cable, wrong config) is often it.
8. **Get a fresh view** — Ask for help, get an outside perspective (the mechanism behind pair debugging and rubber-ducking).
9. **If you didn't fix it, it ain't fixed** — Verify the fix actually eliminated the cause; intermittent "fixes" that aren't confirmed will recur.

### Psychology of Debugging

Cognitive biases actively sabotage debugging:
- **Confirmation bias** — seeking evidence for your favored hypothesis
- **Anchoring** — fixating on the first explanation
- **Availability heuristic** — blaming the most recently-seen bug class
- **Expert blind spots** — senior engineers skip steps a junior would check (the curse of expertise)

Agans' Rule 8 ("get a fresh view") is the institutional countermeasure.

### Rubber Duck Debugging

Explaining code line-by-line to an inanimate object works through the **self-explanation effect** (Chi, de Leeuw, Chiu & LaVancher, *Cognitive Science* 18(3):439–477, 1994) and the production effect. Articulation forces tacit assumptions explicit, exposing the gap between what you *think* the code does and what it says.

**Caveat:** Widely-circulated "fixes 56% more bugs" claims trace only to low-quality secondary sources with no underlying study. The legitimate evidence base is the self-explanation and metacognition literature, not a controlled debugging trial.

### Timeboxing and Escalation Discipline

Gloria Mark (UC Irvine, 2004) found it takes an average of **23 minutes 15 seconds** to fully return to a task after an interruption. Timebox solo debugging (30–60 minutes) before escalating to pair debugging, and protect debugging sessions from interruption.

### The Reproducibility Imperative

**"If it can't be reproduced it can't be fixed."** Strategies:
- Pin down exact failure conditions (inputs, environment, timing, concurrency, load, data state)
- Build a **minimum reproducible example (MRE)** — often the single most powerful step
- "Works in staging, fails in production" points to environment differences (config, data scale, network)
- Watch for date/time bugs (timezone, DST, leap year, clock skew) and platform-specific bugs (ARM vs x86, runtime/browser versions)
- **Heisenbugs** are concurrency bugs that change behavior when observed

### Divide and Conquer Techniques

- Binary search on code paths
- **`git bisect`** to find the commit that introduced a regression
- Program slicing to find statements affecting a variable
- Mocking dependencies to isolate the failing component
- The "wolf fence" partition-and-test algorithm

### Delta Debugging and Bisection

**Delta debugging** (Andreas Zeller, Saarland University, 1999; formalized in Zeller & Hildebrandt, *IEEE TSE* 28(2):183–200, 2002, DOI 10.1109/32.988498) automates minimization using a binary-search-with-twist algorithm (`ddmin`) to reduce a failing input to a *1-minimal* test case where no single element can be removed.

**Canonical case study:** Mozilla crashed after 95 user actions; the prototype automatically reduced it to **3 relevant actions** and simplified **896 lines of HTML to the single line** that caused the failure, in 139 automated test runs (~35 minutes on a 500 MHz PC).

Modern reducers (Perses, C-Reduce, DustMite) build on delta debugging; it pairs naturally with fuzzing. Worst case is O(n²).

---
